# MCP Tools Usage Guide

## Overview

The `officeqa-table-parser` MCP server provides specialized tools for extracting and analyzing tabular data from Treasury Bulletin documents. **Always use MCP tools. Do NOT fall back to bash grep or raw file reading.**

## ⭐ Recommended Tools (Use These First)

### 0. `analyze_visual_chart` — Page text and exhibit metadata for charts

Use this when the question asks about charts, plots, exhibits, or visual features on a specific page. Returns the page text, exhibit titles found, and any pre-analyzed metadata if available.

**Parameters:**
- `filename` (str): Bulletin file name
- `page_number` (int): Page number in the bulletin

**Example:**
```
analyze_visual_chart(filename="treasury_bulletin_1990_09.txt", page_number=5)
```

**Returns:** Page text, exhibit titles, chart type hints. If the chart has been pre-analyzed, also returns local maxima counts and descriptions.

**When to use:**
- Question mentions "local maxima", "peaks", "line plots", "chart", "exhibit"
- Question asks about counting visual features on a page
- Question references a specific page with charts

**After using this tool:**
- Check if the underlying data exists in tables within the same bulletin
- If tabular data exists, extract it and compute the answer (e.g., count local maxima programmatically)
- If no tabular data, use exhibit descriptions and narrative context to reason

---

### 1. `read_bulletin_section` — Read a focused section by keyword

The best starting point. Returns ~80 lines of context around a keyword match, including tables, headers, and footnotes.

**Parameters:**
- `filename` (str): Bulletin file name
- `section_keyword` (str): Keyword to search for (case-insensitive)
- `context_lines` (int, default: 80): Lines of context around match

**Example:**
```
read_bulletin_section(filename="treasury_bulletin_1989_06.txt", section_keyword="Exchange Stabilization Fund")
```

**When to use:**
- You need to understand the structure of a section before extracting values
- You want to see table headers, footnotes, and surrounding context
- You're looking for a specific topic (ESF, Receipts, Exhibit, etc.)

---

### 2. `find_value_in_table` — Precise cell lookup by row/column label

Finds a specific value using fuzzy matching on row labels and optional column labels. Returns the matched row plus neighboring rows for context.

**Parameters:**
- `filename` (str): Bulletin file name
- `row_label` (str): Row label to match (fuzzy, case-insensitive)
- `column_label` (str, optional): Column header to match

**Example:**
```
# Find "Total capital" row
find_value_in_table(filename="treasury_bulletin_1989_06.txt", row_label="Total capital")

# Find a specific cell
find_value_in_table(filename="treasury_bulletin_1989_06.txt", row_label="Total capital", column_label="March 31")
```

**When to use:**
- You know the exact row label you need (e.g., "Total capital", "Receipts")
- You need a specific cell value from a table
- You want to avoid manually parsing large tables

---

## Other Tools

### 3. `list_bulletin_files` — Find files by year/month

```
list_bulletin_files(year=1989, month=6)
```

### 4. `extract_tables_from_bulletin` — Get all tables from a file

```
extract_tables_from_bulletin(filename="treasury_bulletin_1989_12.txt")
```

### 5. `search_tables_for_value` — Search across all tables for a keyword

```
search_tables_for_value(search_term="Total capital", year=1989)
```

### 6. `extract_numeric_column` — Extract values from a specific column

```
extract_numeric_column(filename="treasury_bulletin_1990_09.txt", column_name="Total")
```

### 7. `compute_percent_change` — Calculate percent change

```
compute_percent_change(value1=8124453, value2=8245678)
```

## Recommended Workflows

### Visual Chart / Line Plot Questions
1. `analyze_visual_chart(filename=..., page_number=...)` — get page text and exhibit metadata
2. Search the same bulletin for tables containing the chart's underlying data
3. If tabular data found, extract it and compute the answer programmatically
4. If no tabular data, use exhibit descriptions and annotations to reason
5. Write answer to `/app/answer.txt`

### ESF Balance Sheet Questions
1. `read_bulletin_section(filename=..., section_keyword="Exchange Stabilization Fund")` — see the full section
2. `find_value_in_table(filename=..., row_label="Total capital")` — get the precise value
3. Convert units (thousands → billions) and compute

### Multi-Year Time Series
1. `list_bulletin_files(year=...)` — find files for each year
2. `find_value_in_table(filename=..., row_label=...)` — extract value from each file
3. Build series in Python, compute result

### Unknown Data Location
1. `search_tables_for_value(search_term=..., year=...)` — find which file/table has the data
2. `read_bulletin_section(filename=..., section_keyword=...)` — read the section for context
3. `find_value_in_table(filename=..., row_label=...)` — extract the precise value
