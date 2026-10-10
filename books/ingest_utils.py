import logging
import os
import time
import json
import zlib
from datetime import datetime , timezone

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

def is_sampled(key , sample_percent):
    return zlib.crc32(key.encode("utf-8")) % 100 < sample_percent

def normalize_description(value):
    if isinstance(value , dict):
        value = value.get("value")
    return value.strip() if isinstance(value , str) else ""

def extract_author_keys(authors):
    if not isinstance(authors , list):
        return []
    keys = []
    for item in authors : 
        try:
            k = item["author"]["key"]
        except (KeyError , TypeError):
            continue

        if k and k not in keys:
            keys.append(k)

    return keys

def parse_work_line(line , sample_percent = 50 , stats = None):
    def count(reason):
        if stats is not None:
            stats[reason] += 1
    columns = line.rstrip("\n").split("\t")

    if len(columns) < 5:
        count("malformed_line")
        return None

    key = columns[1]

    if not is_sampled(key , sample_percent):
        count("not_sampled")
        return None
    try:
        record = json.loads(columns[-1])
    except json.JSONDecodeError:
        count("parse_failure")
        return None

    author_keys = extract_author_keys(record.get("authors"))
    subjects = record.get("subjects")
    if not author_keys:
        count("no_author")
        return None
    
    if not subjects or not isinstance(subjects, list):
        count("no_subjects")
        return None
    
    if not record.get("covers"):
        count("no_cover")
        return 

    last_modified = record.get("last_modified")
    if isinstance(last_modified , dict):
        last_modified = last_modified.get("value")
    if not last_modified:
        last_modified = columns[3]
    try:
        last_modified = parse_ts(last_modified)
    except (ValueError , TypeError):
        count("bad_timestamp")
        return None

    count("kept")

    return {
        "key": key,
        "title": record.get("title") or "",
        "description": normalize_description(record.get("description")),
        "subjects": [s for s in subjects if isinstance(s, str)],
        "first_publish_date": str(record.get("first_publish_date") or ""),
        "last_modified": last_modified,
        "author_keys": author_keys,
    }

    