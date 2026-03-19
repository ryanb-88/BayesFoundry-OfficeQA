# Common Answer Patterns

This guide shows common question types and how to approach and format answers.

## Answer Format Reference

### Single Number
**Question:** "What is the total capital?"
**Format:** Just the number (with units if specified)
```
8.124
```

### Bracketed List
**Question:** "Report values as comma-separated in square brackets"
**Format:**
```
[value1, value2]
```

### Multiple Sub-Questions
**Question:** "Report: 1) value A, 2) value B, 3) difference"
**Format:**
```
[answer1, answer2, answer3]
```

## Common Question Patterns

### Pattern 1: Balance Sheet Lookups

**What it asks:** Find specific values from an ESF or budget balance sheet.

**Steps:**
1. Identify the exact table type (ESF-1, ESF-2, budget receipts, etc.)
2. Identify the exact reporting date from the question
3. Use `get_row_by_label` to find the specific row
4. Verify the column matches the date requested
5. Check units in the column header (thousands? millions?)
6. Convert to the units requested in the question

**Key warning:** Read the row label EXACTLY. "Total capital" and "Capital account" are different line items. Always verify you are reading the correct row.

---

### Pattern 2: Multi-Year Time Series Analysis

**What it asks:** Compute statistics (mean, HP filter, regression) across multiple years.

**Steps:**
1. Use `list_bulletin_files` to find files for the date range
2. For each year, extract the relevant value using `get_row_by_label` or `extract_numeric_column`
3. Build a data series (e.g., Python list or dict keyed by year)
4. Perform the calculation (see `python_calculations.md` for code templates)
5. Format the final answer

**Tips:**
- September bulletins typically contain full fiscal year summaries
- Use consistent units across all values before computing
- For fiscal year data, remember FY boundaries changed in 1977

---

### Pattern 3: Date-Specific Value Extraction

**What it asks:** Find values as of specific dates (e.g., "last day of June and September").

**Steps:**
1. Map the date to the correct bulletin issue
   - June 30 data → look in mid/late-year bulletins
   - September 30 data → look in late-year bulletins (Sep or later issues)
2. Use `list_bulletin_files(year=YYYY)` to see available months
3. Extract the value, paying attention to which date column you're reading

---

### Pattern 4: Differences and Comparisons

**What it asks:** Compute absolute difference, percentage change, or ratio between values.

**Steps:**
1. Extract both values using the patterns above
2. Verify both values are in the same units
3. Compute: `absolute_diff = abs(value_A - value_B)`
4. Or use `compute_percent_change(value1, value2)` MCP tool
5. Apply rounding as specified in the question

---

### Pattern 5: Visual/Chart Questions

**What it asks:** Count features (local maxima, crossings) or read values from charts.

**Approach:**
1. Search for any underlying data tables that correspond to the chart
2. Look for "Exhibit" or figure descriptions in the text
3. Check if the text describes specific data points or trends
4. If no numerical data is available, note that visual analysis from text alone has limitations

---

## Unit Conversion Reference

| From | To | Formula |
|------|-----|---------|
| Thousands | Millions | ÷ 1,000 |
| Thousands | Billions | ÷ 1,000,000 |
| Millions | Billions | ÷ 1,000 |

## Rounding Rules

| Instruction | Example |
|-------------|---------|
| "Nearest whole number" | 8.124 → 8 |
| "Nearest thousandth" | 8.124453 → 8.124 |
| "Nearest hundredth" | 8.124453 → 8.12 |
| "Round to X decimal places" | Standard rounding |

## Pre-Answer Checklist

Before writing your answer, verify:
- [ ] Used MCP tools to find data (not just raw file reading)
- [ ] Verified the correct row AND column in the table
- [ ] Checked table headers for units (thousands? millions? billions?)
- [ ] Converted to the units requested in the question
- [ ] Applied correct rounding as specified
- [ ] Formatted exactly as requested (brackets? commas? decimal places?)
- [ ] Answered ALL sub-questions
- [ ] Wrote to `/app/answer.txt`
