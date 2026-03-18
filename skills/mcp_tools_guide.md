# MCP Tools Usage Guide

## Overview

The `officeqa-table-parser` MCP server provides specialized tools for extracting and analyzing tabular data from Treasury Bulletin documents. **Always try MCP tools before falling back to raw file reading.**

## Tool Reference

### 1. `list_bulletin_files`

Find available Treasury Bulletin files, optionally filtered by year and/or month.

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
- You need to find files for a specific time period
- You're not sure which files exist
- You need to find multiple files for a time series analysis

---

### 2. `extract_tables_from_bulletin`

Extract all tables from a specific Treasury Bulletin file with structured data.

**Parameters:**
- `filename` (str): Name of the bulletin file (e.g., "treasury_bulletin_1989_12.txt")
- `corpus_path` (str, default: "/app/corpus"): Path to corpus directory

**Returns:**
- List of tables with column headers, row data, and metadata

**Example Usage:**
```
# Get all tables from December 1989 bulletin
extract_tables_from_bulletin(filename="treasury_bulletin_1989_12.txt")

# Extract tables and find ESF data
tables = extract_tables_from_bulletin(filename="treasury_bulletin_1989_09.txt")
# Then search through tables for "Exchange Stabilization Fund"
```

**When to use:**
- You know the specific file you need
- You want structured table data with column names
- You need to analyze multiple tables from one bulletin

---

### 3. `search_tables_for_value`

Search across ALL tables in ALL files (or filtered by year) for rows containing a keyword.

**Parameters:**
- `search_term` (str): Value or keyword to search for (case-insensitive)
- `corpus_path` (str, default: "/app/corpus"): Path to corpus directory
- `year` (int, optional): Filter by year
- `max_results` (int, default: 50): Maximum number of results

**Example Usage:**
```
# Find all mentions of Exchange Stabilization Fund in 1989
search_tables_for_value(search_term="Exchange Stabilization Fund", year=1989)

# Find capital account references
search_tables_for_value(search_term="capital account", year=1989)

# Search for specific dollar amounts
search_tables_for_value(search_term="8,124,453")
```

**When to use:**
- You need to find where a specific term appears
- You're not sure which file contains the data
- You want to find all occurrences of a value across multiple files

---

### 4. `extract_numeric_column`

Extract all numeric values from a specific column across all tables in a file.

**Parameters:**
- `filename` (str): Name of the bulletin file
- `column_name` (str): Name of the column (partial match)
- `corpus_path` (str, default: "/app/corpus"): Path to corpus directory

**Returns:**
- List of values with statistics (sum, mean, min, max)

**Example Usage:**
```
# Extract all "Total" columns
extract_numeric_column(filename="treasury_bulletin_1989_09.txt", column_name="Total")

# Extract values from a specific column
extract_numeric_column(filename="treasury_bulletin_1990_09.txt", column_name="Mar. 31, 1989")
```

**When to use:**
- You need all values from a specific column
- You want statistics on a column's values
- You're doing time series analysis

---

### 5. `compute_percent_change`

Compute the percent change between two values.

**Parameters:**
- `value1` (float): Initial value (older)
- `value2` (float): Final value (newer)

**Example Usage:**
```
compute_percent_change(value1=8124453, value2=8245678)
```

---

## Recommended Workflow

### For Single-Value Questions
1. Use `search_tables_for_value` to find relevant tables
2. Use `extract_tables_from_bulletin` to get structured data
3. Parse the specific value and convert units

### For Multi-Year Analysis
1. Use `list_bulletin_files` to identify needed files
2. Use `extract_tables_from_bulletin` for each file
3. Combine data and perform calculations

### For Complex Queries
1. Start with `search_tables_for_value` to locate data
2. Extract full tables with `extract_tables_from_bulletin`
3. Use Python code execution for complex calculations (e.g., Hodrick-Prescott filter)

## Tips

- MCP tools are faster than reading entire files
- Table extraction preserves column structure
- Use partial column name matches (e.g., "Total" matches "Total assets")
- Always check the `corpus_path` default if files aren't found
