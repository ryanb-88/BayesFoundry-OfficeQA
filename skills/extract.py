#!/usr/bin/env python3
"""
Extract tables from a specific Treasury Bulletin. Call via bash:
  python3 /app/skills/extract.py <year> <month> <keyword>

Returns only the relevant table sections (~5K tokens vs 150K for full file).
"""
import sys
import re
from pathlib import Path

CORPUS_DIR = Path("/app/corpus")

def _find_table_bounds(lines, idx):
    start = idx
    while start > 0:
        prev = lines[start - 1].strip()
        if prev.startswith("|") or (prev == "" and start - 2 >= 0 and lines[start - 2].strip().startswith("|")):
            start -= 1
        else:
            break
    end = idx + 1
    while end < len(lines):
        curr = lines[end].strip()
        if curr.startswith("|"):
            end += 1
        elif curr == "":
            peek = end + 1
            while peek < len(lines) and lines[peek].strip() == "":
                peek += 1
            if peek < len(lines) and lines[peek].strip().startswith("|"):
                end = peek + 1
            else:
                break
        else:
            break
    return max(0, start), min(len(lines), end)

def _nearest_header(lines, from_idx, look_back=40):
    for i in range(from_idx - 1, max(0, from_idx - look_back), -1):
        if lines[i].startswith("#"):
            return i
    return max(0, from_idx - 5)

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 extract.py <year> <month> <keyword>")
        sys.exit(1)

    year = int(sys.argv[1])
    month = int(sys.argv[2])
    keyword = sys.argv[3]

    path = CORPUS_DIR / f"treasury_bulletin_{year:04d}_{month:02d}.txt"
    if not path.exists():
        print(f"NOT FOUND: treasury_bulletin_{year:04d}_{month:02d}.txt")
        sys.exit(1)

    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    pattern = re.compile(keyword, re.IGNORECASE)
    found = []
    seen = set()

    for i, line in enumerate(lines):
        if pattern.search(line):
            s, e = _find_table_bounds(lines, i)
            if (s, e) in seen:
                continue
            seen.add((s, e))
            h = _nearest_header(lines, s)
            found.append("\n".join(lines[h:e]))

    if not found:
        print(f"No tables containing '{keyword}' in treasury_bulletin_{year:04d}_{month:02d}.txt")
    else:
        sep = "\n\n" + "=" * 60 + "\n\n"
        print(sep.join(found[:5]))

if __name__ == "__main__":
    main()
