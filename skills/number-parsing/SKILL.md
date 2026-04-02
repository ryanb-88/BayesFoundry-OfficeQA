# Parsing Numbers from Treasury Bulletin Tables

## Number Formats

| What you see | What it means |
|---|---|
| `1,234.5` | 1234.5 (comma = thousands separator) |
| `(45.3)` | -45.3 (parentheses = negative) |
| `-45.3` | -45.3 |
| `*` or `r` suffix | Revised value — prefer this over unrevised |
| `—` or `...` | Data not available |
| `(1)` at end of row | Footnote marker, not a number |

## Units — Always Check the Table Header

Units are stated near the table heading, not repeated per row:
- "In millions of dollars" → all values ÷ 1 (already in millions)
- "In billions of dollars" → all values ÷ 1 (already in billions)
- "In thousands of dollars" → divide by 1,000 to get millions

**Never assume units.** A value of `1,234` could be $1,234 million or $1,234 thousand.

## Multi-Row Column Headers

Some tables have 2–3 header rows before the `|---|` separator line:
```
| Category | Fiscal Year |          |
|          | 1952        | 1953     |
|---|---|---|
| Defense  | 1234.5      | 2345.6   |
```
Read ALL header rows to understand what each column represents.

## Handling Revised Values

Treasury Bulletins frequently republish revised figures:
- A value in `treasury_bulletin_1955_01.txt` for FY1953 may differ from
  the same value in `treasury_bulletin_1953_09.txt`
- **Always use the most recently published version** (latest bulletin date)
- Use the `find_latest_value` MCP tool to search newest-first

## Computing From Raw Values

When you extract numbers with commas, strip them in Python before calculating:
```python
raw = "1,234,567.89"
value = float(raw.replace(",", ""))  # → 1234567.89
```

For parenthetical negatives:
```python
raw = "(45.3)"
value = -float(raw.strip("()"))  # → -45.3
```
