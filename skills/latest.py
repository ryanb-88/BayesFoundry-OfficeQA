#!/usr/bin/env python3
"""
Find the MOST RECENTLY PUBLISHED value for a keyword by searching bulletins
NEWEST-FIRST. Treasury bulletins frequently revise prior figures — this ensures
you always get the latest revision.

Call via bash:
  python3 /app/skills/latest.py "<keyword>" [year_from] [year_to]

Example:
  python3 /app/skills/latest.py "gross debt" 1975 1985
  python3 /app/skills/latest.py "national defense" 1950 1960
"""
import sys
import re
from pathlib import Path

CORPUS_DIR = Path("/app/corpus")

def _parse_filename(name):
    m = re.match(r"treasury_bulletin_(\d{4})_(\d{2})\.txt", name)
    return (int(m.group(1)), int(m.group(2))) if m else None

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
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 latest.py <keyword> [year_from] [year_to]")
        sys.exit(1)

    keyword = args[0]
    year_from = int(args[1]) if len(args) > 1 else 1939
    year_to = int(args[2]) if len(args) > 2 else 2025

    pattern = re.compile(keyword, re.IGNORECASE)

    # Search NEWEST-FIRST
    for fpath in sorted(CORPUS_DIR.glob("treasury_bulletin_*.txt"), reverse=True):
        parsed = _parse_filename(fpath.name)
        if not parsed:
            continue
        fy, fm = parsed
        if fy < year_from or fy > year_to:
            continue

        lines = fpath.read_text(encoding="utf-8", errors="replace").split("\n")
        for i, line in enumerate(lines):
            if pattern.search(line):
                s, e = _find_table_bounds(lines, i)
                h = _nearest_header(lines, s)
                print(f"LATEST MATCH in {fpath.name} (line {i + 1}):\n")
                print("\n".join(lines[h:e]))
                return

    print(f"No match for '{keyword}' in bulletins {year_from}–{year_to}")

if __name__ == "__main__":
    main()
