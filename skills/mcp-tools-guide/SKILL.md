---
name: mcp-tools-guide
description: Efficient data extraction patterns for Treasury Bulletin documents using grep, read, and bash.
---
# Data Extraction Guide

## Efficient Extraction Patterns

### Find a specific value in a table
```bash
# Step 1: Find the line number
grep -n "Total capital" /app/corpus/treasury_bulletin_1989_06.txt

# Step 2: Read just the relevant section (e.g., 10 lines around match)
# Use the read tool with offset and limit based on the line number found
```

### Extract data from multiple files at once
```bash
for f in /app/corpus/treasury_bulletin_19{89..92}_06.txt; do
  echo "=== $f ==="
  grep -n "Total assets" "$f" | head -3
done
```

### Search across all bulletins for a topic
```bash
grep -l "Exchange Stabilization" /app/corpus/treasury_bulletin_1989*.txt
```

### Extract a specific table section
```bash
# Find the table header line, then read ~50 lines from there
grep -n "Table ESF-1\|Balances as of" /app/corpus/treasury_bulletin_1989_06.txt
# Then use read with offset=<line_number> limit=50
```

## Rules

1. **NEVER read an entire file** — always grep first, then read a targeted range
2. **Use bash loops** for multi-year data instead of sequential reads
3. **Pipe grep through head** to limit output: `grep "pattern" file | head -10`
4. **Use python3** for any calculation more complex than basic arithmetic
