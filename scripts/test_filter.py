import gzip
import sys
from collections import Counter


sys.path.insert(0, ".") 
from books.ingest_utils import parse_work_line

path = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100_000

stats = Counter()
kept = 0
total_authors = 0
samples = []

with gzip.open(path, "rt", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= limit:
            break
        result = parse_work_line(line, sample_percent=50, stats=stats)
        if result:
            kept += 1
            total_authors += len(result["author_keys"])
            if len(samples) < 3:
                samples.append(result)

print(f"Lines: {limit:,} | kept: {kept:,} ({kept / limit * 100:.1f}%)")
print(f"Avg authors per kept work: {total_authors / max(kept, 1):.2f}")
print("Reasons:", dict(stats))
for s in samples:
    print("\n", s)