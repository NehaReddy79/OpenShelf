import gzip
import json
import sys
from collections import Counter

path = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100_000

key_counts = Counter()
desc_types = Counter()
author_counts = Counter()
bad_author_items = 0
parse_failures = 0
total_bytes = 0
processed = 0

with gzip.open(path, "rt", encoding="utf-8") as f:

    for i, line in enumerate(f):
        if i >= limit:
            break

        total_bytes += len(line.encode("utf-8"))
        cols = line.rstrip("\n").split("\t")

        try:
            record = json.loads(cols[-1])
            
        except (json.JSONDecodeError, IndexError):
            parse_failures += 1
            continue

        processed += 1
        key_counts.update(record.keys())

        if "description" in record:
            desc_types[type(record["description"]).__name__] += 1

        if "authors" in record:
            authors = record["authors"]
            n = len(authors)
            author_counts[n if n < 3 else "3+"] += 1
            for item in authors:
                try:
                    item["author"]["key"]
                except (KeyError, TypeError):
                    bad_author_items += 1

        if (i + 1) % 20_000 == 0:
            print(f"...{i + 1} lines read", file=sys.stderr)

print(f"\nLines processed: {processed} | parse failures: {parse_failures}")
print(f"Average bytes per line: {total_bytes / max(processed + parse_failures, 1):.0f}")

print("\nTop 20 keys:")
for key, count in key_counts.most_common(20):
    print(f"  {key:<25} {count:>8}  {count / processed * 100:5.1f}%")

print("\nDescription types:", dict(desc_types))
print("Authors per work:", dict(author_counts))
print("Author items missing the nested author->key path:", bad_author_items)