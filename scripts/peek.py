import gzip
import json
import sys

path = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 5

with gzip.open(path, "rt", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= n:
            break
        cols = line.rstrip("\n").split("\t")
        print(f"--- line {i + 1} | {len(line.encode('utf-8'))} bytes | {len(cols)} columns ---")
        for j, c in enumerate(cols[:-1]):
            print(f"col {j}: {c}")
        record = json.loads(cols[-1])
        print("JSON keys:", sorted(record.keys()))
        print(json.dumps(record, indent=2)[:1500])
        print()