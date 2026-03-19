# MCP Tools Usage Guide

## Overview

The `officeqa-table-parser` MCP server provides specialized tools for extracting and analyzing tabular data from Treasury Bulletin documents. **Always try MCP tools before falling back to raw file reading.**

## Tool Reference

### 1. `list_bulletin_files`

Find available Treasury Bulletin files, optionally filtered by year and/or month.
If no exact match is found, returns suggestions for available files in that year.

**Parameters:**
- `corpus_path` (str, default: "/app/corpus"): Path to corpus directory
- `year` (int, optional): Filter by year (e.g., 1989)
- `month` (int, optional): Filter by month 1-12

**Example Usage:**
```
# Find all files from 1989
list_bulletin_files(year=1989)

# Find September 1990 bulletin
list_bulletin_files(year=1990, month=9)

# List all available files
list_bulletin_files()
```

**When to use:**
- First step for most queries — verify which files exist
- You need to find files for a specific time period
- You're not sure which months are available for a given year

---

### 2. `get_row_by_label` ⭐ (Most Direct Lookup)

Find a specific row by its label text across all tables in a file. This is the fastest way to look up a known value.

**Parameters:**
- `filename` (str): Name of the bulletin file
- `row_label` (str): Text label to search for (partial match, case-insensitive)
- `corpus_path` (str, default: "/app/corpus"): Path to corpus directory

**Example Usage:**
```
# Find "Total capital" row in a specific bulletin
get_row_by_label(filename="treasury_bulletin_1989_09.txt", row_label="Total capital")

# Find individual income tax receipts
get_row_by_label(filename="treasury_bulletin_2024_09.txt", row_label="Individual income taxes")

# Find a specific line item
get_row_by_label(filename="treasury_bulletin_1990_06.txt", row_label="Gross saving")
```

**When to use:**
- You know the file AND the row label you need — this is the most efficient tool
- Looking up specific line items (Total capital, Total liabilities, specific tax categories)
- Verifying a value you found via other tools

---

### 3. `extract_tables_from_bulletin`

Extract all tables from a specific Treasury Bulletin file with structured data.
Returns table context (section headers) to help identify which table is which.

**Parameters:**
- `filename` (str): Name of the bulletin file (e.g., "treasury_bulletin_1989_12.txt")
- `corpus_path` (str, default: "/app/corpus"): Path to corpus directory

**Example Usage:**
```
# Get all tables from December 1989 bulletin
extract_tables_from_bulletin(filename="treasury_bulletin_1989_12.txt")
```

**When to use:**
- You need to explore what tables are in a file
- You need the full structure of a table (all rows and columns)
- You want to see all data in context

---

### 4. `search_tables_for_value`

Search across tables for rows containing a keyword. ⚠️ **Always specify `year` to avoid scanning all 697 files.**

**Parameters:**
- `search_term` (str): Value or keyword to search for (case-insensitive)
- `corpus_path` (str, default: "/app/corpus"): Path to corpus directory
- `year` (int, optional): **Strongly recommended** — filter by year
- `max_results` (int, default: 50): Maximum number of results

**Example Usage:**
```
# Find ESF data in 1989 (ALWAYS specify year)
search_tables_for_value(search_term="Exchange Stabilization Fund", year=1989)

# Find capital account references in a specific year
search_tables_for_value(search_term="capital account", year=1989)
```

**When to use:**
- You don't know which file contains the data
- You want to find all occurrences of a value across a year's bulletins
- First-pass discovery before using more targeted tools

---

### 5. `extract_numeric_column`

Extract all numeric values from a specific column across all tables in a file.
Returns row labels alongside values for easier identification.

**Parameters:**
- `filename` (str): Name of the bulletin file
- `column_name` (str): Name of the column (partial match, case-insensitive)
- `corpus_path` (str, default: "/app/corpus"): Path to corpus directory

**Returns:**
- List of values with row labels and statistics (sum, mean, min, max)

**Example Usage:**
```
# Extract all values from "Total" columns
extract_numeric_column(filename="treasury_bulletin_1989_09.txt", column_name="Total")
```

**When to use:**
- You need all values from a specific column for calculations
- Building a data series for time series analysis
- Getting summary statistics

---

### 6. `compute_percent_change`

Compute the percent change between two values.

**Parameters:**
- `value1` (float): Initial value (older)
- `value2` (float): Final value (newer)

**Example Usage:**
```
compute_percent_change(value1=8124453, value2=8245678)
```

---

## Recommended Workflows

### Single-Value Lookup (fastest)
1. `list_bulletin_files(year=YYYY, month=MM)` — verify file exists
2. `get_row_by_label(filename="...", row_label="...")` — direct lookup
3. Convert units and format answer

### Discovery (don't know where data is)
1. `search_tables_for_value(search_term="...", year=YYYY)` — find it
2. `get_row_by_label(filename="...", row_label="...")` — get precise value
3. Convert units and format answer

### Multi-Year Analysis
1. `list_bulletin_files(year=YYYY)` — for each year in range
2. `get_row_by_label` or `extract_numeric_column` — extract values per year
3. Use Python for calculations (HP filter, means, regressions)

### Exploration (unfamiliar table structure)
1. `extract_tables_from_bulletin(filename="...")` — see all tables
2. Identify relevant table by context and column headers
3. `get_row_by_label` for specific values

## Performance Tips

- **Always specify `year`** in `search_tables_for_value` — scanning 697 files is slow
- Use `get_row_by_label` over `extract_tables_from_bulletin` when you know what you're looking for
- Use `list_bulletin_files` first to verify files exist before trying to extract from them
- The `context` field in results shows nearby section headers — use this to identify the right table
