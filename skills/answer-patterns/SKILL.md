---
name: answer-patterns
description: Common question types and answer formatting patterns for Treasury Bulletin QA tasks, including worked examples for specific question patterns.
---
# Common Answer Patterns

Refer to the main prompt for unit conversion tables, verification checklists, and self-consistency check procedures. This skill covers specific question patterns and worked extraction steps.

## Answer Format Quick Reference

| Type | Format | Example |
|------|--------|---------|
| Single number | Bare number (with units if specified) | `8.124` |
| Date | Full month name, day (no leading zero), year | `March 3, 1977` |
| Percentage | Number with `%` sign | `4.5%` |
| Text/Name | Plain text matching source document | `United Kingdom` |
| Bracketed list | Comma-separated in square brackets | `[8.124, 12.852]` |
| Multi-part | Values in brackets | `[1832816, 2049753, 216937]` |

## Question Patterns

### Pattern 1: ESF Balance Sheet Values

**Steps:**
1. Find the ESF-1 table for the date (search broadly across bulletins)
2. Identify "Total capital" row (NOT "Capital account")
3. Identify "Total liabilities and capital" row
4. Calculate absolute difference
5. Convert to requested units (values are in thousands)

### Pattern 2: Multi-Year Time Series

**Steps:**
1. Use a single bash loop to extract across all files in the date range
2. Build time series data
3. Use MCP tools or Python for calculations
4. Format final answer

**Tips:**
- September bulletins have full fiscal year data
- Use bash loops for multi-file extraction

### Pattern 3: Date-Specific Values

**Steps:**
1. Identify which bulletins contain these dates (search broadly)
2. September data appears in late-year bulletins
3. June data appears in mid-year bulletins
4. Extract values for each specified date
5. Perform calculations

### Pattern 4: Counting/Classification

**Approach:**
1. Find the page/exhibit in the bulletin text
2. Search for underlying tabular data in the same bulletin
3. If data found in tables, extract and count programmatically:
   ```python
   maxima = sum(1 for i in range(1, len(vals) - 1) if vals[i] > vals[i-1] and vals[i] > vals[i+1])
   ```
4. For multi-series charts, count per series and sum

### Pattern 5: Statistical Calculation (Volatility, Theil Index, etc.)

**Steps:**
1. Extract rates across multiple bulletins using bash loop
2. Build the time series in Python
3. Compute using MCP tools or the python-calculations skill
4. Self-consistency check: re-extract and re-compute

**Key:** Always verify the data frequency (monthly, quarterly, annual) matches the annualization factor (√12, √4, √1).

## Rounding Rules

| Instruction | Example |
|-------------|---------|
| "Nearest whole number" | 8.124 → 8 |
| "Nearest thousandth" | 8.124453 → 8.124 |
| "Nearest hundredth" | 8.124453 → 8.12 |
| "Round to X decimal places" | Standard rounding |
