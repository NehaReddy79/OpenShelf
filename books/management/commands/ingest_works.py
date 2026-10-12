from books.ingest_utils import write_checkpoint , read_checkpoint , parse_ts , parse_work_line
import json
import os
import gzip
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from books.models import Author , Work , WorkAuthor
from collections import Counter

from django.db import transaction

from books.models import Author, Work, WorkAuthor


def process_batch(batch):

    author_keys = {k for w in batch for k in w["author_keys"]}
    work_keys = [w["key"] for w in batch]

    with transaction.atomic():
       
        author_ids = dict(
            Author.objects.filter(key__in=author_keys).values_list("key", "id")
        )

        
        Work.objects.bulk_create(
            [
                Work(
                    key=w["key"],
                    title=w["title"],
                    description=w["description"],
                    subjects=w["subjects"],
                    first_publish_date=w["first_publish_date"],
                    last_modified=w["last_modified"],
                )
                for w in batch
            ],
            ignore_conflicts=True,
        )

       
        work_ids = dict(
            Work.objects.filter(key__in=work_keys).values_list("key", "id")
        )

        
        links = []
        missing = 0
        for w in batch:
            work_id = work_ids[w["key"]]
            position = 0
            for author_key in w["author_keys"]:
                author_id = author_ids.get(author_key)
                if author_id is None:
                    missing += 1
                    continue
                links.append(
                    WorkAuthor(work_id=work_id, author_id=author_id, position=position)
                )
                position += 1

        WorkAuthor.objects.bulk_create(links, ignore_conflicts=True, batch_size=5000)

    return missing
    
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str)
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--batch-size", type=int, default=5000)
        parser.add_argument("--sample-percent" , type = int , default = 50)
        parser.add_argument("--fresh", action="store_true",
                            help="Ignore and delete any existing checkpoint")

    def handle(self , *args , **options):
        file_path = options["file_path"]
        limit = options["limit"]
        batch_size = options["batch_size"]
        sample_percent = options["sample_percent"]
        checkpoint_path = file_path+".checkpoint"

        

        if options["fresh"] and os.path.exists(checkpoint_path):
            os.remove(checkpoint_path)
        start_line = read_checkpoint(checkpoint_path)
        if start_line : 
            self.stdout.write(f"Resuming line {start_line}")

        works_before = Work.objects.count()
        links_before = WorkAuthor.objects.count()
        started = time.time()
        batch = []
        processed_lines = 0
        lines_read = start_line
        missing_total = 0
        stats = Counter()

        with gzip.open(file_path , "rt" , encoding="utf-8") as f:
            for i , line in enumerate(f , start=1):

                if i <= start_line:
                    continue

                if limit is not None and processed_lines >= limit :
                    break

                
                lines_read = i
                work = parse_work_line(line , sample_percent , stats)

                if work is not None:
                    batch.append(work)

                if len(batch) >= batch_size:
                    missing_total += process_batch(batch)
                    batch.clear()
                    write_checkpoint(checkpoint_path , lines_read)
                    self.stdout.write(f"...{lines_read:,} lines read")
            if batch:
                missing_total += process_batch(batch)
                batch.clear()
            write_checkpoint(checkpoint_path , lines_read)

        elapsed = time.time() - started
        processed = lines_read - start_line
        self.stdout.write(self.style.SUCCESS(
            f"\nLines read: {processed:,}"
            f"\nWorks kept: {stats['kept']:,}"
            f"\nNew works inserted: {Work.objects.count() - works_before:,}"
            f"\nNew links inserted: {WorkAuthor.objects.count() - links_before:,}"
            f"\nMissing author references: {missing_total:,}"
            f"\nDrop reasons: {dict(stats)}"
            f"\nElapsed: {elapsed:.1f}s"
            f"\nSpeed: {processed / max(elapsed, 0.001):.0f} lines/sec"
        ))