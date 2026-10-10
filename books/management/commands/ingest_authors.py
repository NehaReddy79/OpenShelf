from django.core.management import BaseCommand
import json
import gzip
import os 
import time
import logging
from datetime import datetime , timezone
from books.models import Author

logger = logging.getLogger(__name__)

def parse_ts(value):
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def read_checkpoint(path):
    try:
        with open(path) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_checkpoint(path, line_number , retries = 5 , base_delay = 0.1):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(str(line_number))

    for attempt in range(retries):
        try:
            os.replace(tmp, path)
            return True
        except PermissionError:
            if attempt < retries - 1:
                time.sleep(base_delay * (2 ** attempt))

    logger.warning(
        "Could not update checkpoint at line %s after %s attempts. Continuing.",
        line_number, retries,
    )
    try : 
        os.remove(tmp)
    except OSError : 
        pass
    return False
    


class Command(BaseCommand):

    help = "Stream the Open Library authors dump into Postgres (batched, idempotent, resumable)."
    def add_arguments(self , parser) : 
        parser.add_argument("file_path" , type = str)
        parser.add_argument("--limit" , type = int , default=None)
        parser.add_argument("--batch-size" ,type=int , default=5000 )
        parser.add_argument("--fresh", action="store_true",
                            help="Ignore and delete any existing checkpoint")

    def handle(self , *args , **options):
        file_path = options["file_path"]
        limit = options["limit"]
        batch_size = options["batch_size"]
        checkpoint_path = file_path+".checkpoint"

        if options["fresh"] and os.path.exists(checkpoint_path):
            os.remove(checkpoint_path)
        start_line = read_checkpoint(checkpoint_path)
        if start_line : 
            self.stdout.write(f"Resuming line {start_line}")

        count_before = Author.objects.count()
        started = time.time()
        batch = []
        parse_failures = 0
        skipped = 0
        lines_read = start_line

        def flush(line_number):
            Author.objects.bulk_create(batch, batch_size=batch_size, ignore_conflicts=True)
            batch.clear()
            write_checkpoint(checkpoint_path, line_number)

        with gzip.open(file_path , "rt" , encoding="utf-8") as file:
            for i , line in enumerate(file) :

                if i < start_line:
                    continue
                if limit is not None and i >= limit:
                    break
                lines_read = i + 1
                columns = line.rstrip("\n").split("\t")
                try:
                    records = json.loads(columns[-1])
                except (json.JSONDecodeError , IndexError):
                    parse_failures += 1
                    continue

                key = records.get("key")
                name = records.get("name", "")
                
                last_modified = records.get("last_modified")

                if isinstance(last_modified , dict):
                    last_modified = last_modified.get("value")
                if not last_modified and len(columns) > 3:
                    last_modified = columns[3]

                if not key or not last_modified:
                    skipped += 1
                    continue

                try:
                    last_modified = parse_ts(last_modified)
                except ValueError:
                    skipped += 1
                    continue

                batch.append(Author(key = key , name = name , last_modified = last_modified))

                if len(batch) >= batch_size:
                    flush(lines_read)
                    self.stdout.write(f"...{lines_read} lines processed")


            if batch:
                flush(lines_read)
            else : 
                write_checkpoint(checkpoint_path , lines_read)

        elapsed = time.time() - started
        inserted = Author.objects.count() - count_before
        processed = lines_read - start_line

        self.stdout.write(self.style.SUCCESS(
            f"\n Lines processed : {processed}"
            f"\n New rrows inserted : {inserted}"
            f"\n Parse Failures : {parse_failures}"
            f"\n Skipped : {skipped}"
            f"\n Elapsed : {elapsed:.1f}s"
            f"\n Speed : {processed / max(elapsed , 0.001):.0f} lines/sec"
        ))

    





