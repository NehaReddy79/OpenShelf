import gzip
import json
import sys
import time
from collections import Counter

path = sys.argv[1]
step = int(sys.argv[2]) if len(sys.argv) > 2 else 50

def has_author(record):
    authors = record.get("authors")
    if not isinstance(authors , list):
        return False
    for item in authors : 
        try:
            if item["author"]["key"]:
                return True
        except (KeyError , TypeError):
            continue
    return False

total_lines = 0
sampled = 0
rules = Counter()
parse_failures = 0
started = time.time()

with gzip.open(path, "rt", encoding="utf-8") as f:

    for i, line in enumerate(f):
        total_lines += 1

        if i % step != 0:
            continue

        cols = line.rstrip("\n").split("\t")

        try:
            record = json.loads(cols[-1])
            
        except (json.JSONDecodeError, IndexError):
            parse_failures += 1
            continue

        sampled += 1
        author = has_author(record)
        subjects = bool(record.get("subjects"))
        cover = bool(record.get("covers"))

        if author : 
            rules["A: has author"] += 1
            if subjects:
                rules["B: author + subjects"] += 1
            if cover:
                rules["C: author + cover"] += 1
            if cover or subjects:
                rules["D: author +(subjects OR cover)"] += 1
            if cover and subjects:
                rules["E: author +(subjects + cover)"] += 1
            

        if total_lines % 1_000_000 == 0:
            print(f"...{i + 1} lines scanned", file=sys.stderr)

print(f"\nTotal lines: {total_lines:,}")
print(f"Sampled (every {step}th): {sampled:,} | parse failures: {parse_failures}")
print(f"Elapsed: {time.time() - started:.0f}s\n")

print(f"{'Rule':<36}{'Yield':>8}{'Est. rows':>14}")
for rule in sorted(rules):
    pct = rules[rule] / sampled
    print(f"{rule:<36}{pct * 100:>7.1f}%{int(pct * total_lines):>14,}")