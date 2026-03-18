# Common Answer Patterns

This guide shows common question types and how to format answers correctly.

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
[8.124, 12.852]
```

### Multiple Sub-Questions
**Question:** "Report: 1) value A, 2) value B, 3) difference"
**Format:**
```
[1832816, 2049753, 216937]
```

## Common Question Patterns

### Pattern 1: ESF Balance Sheet Values

**Example Question:**
> What is the total nominal capital held as per U.S. Treasury's Exchange Stabilization Fund Balance Sheet as of March 31, 1989 and what is the absolute difference with total liabilities and capital?

**Steps:**
1. Find the ESF-1 table for the date
2. Identify "Total capital" row (NOT "Capital account")
3. Identify "Total liabilities and capital" row
4. Calculate absolute difference
5. Convert to requested units (billions)

**Key Tables:**
```
| Capital:                    |              |
| Capital account             | 200,000      | <- This is NOT total capital
| Net Income (loss)           | 7,924,453    |
| Total capital               | 8,124,453    | <- USE THIS
| Total liabilities and capital | 20,976,061 | <- And this
```

**Answer:** `[8.124, 12.852]` (in billions)

---

### Pattern 2: Multi-Year Time Series

**Example Question:**
> Using data for fiscal years 2010-2024, compute [complex calculation]...

**Steps:**
1. List files for the date range
2. Extract relevant tables from each file
3. Build time series data
4. Perform calculations (may need Python)
5. Format final answer

**Tips:**
- September bulletins have full fiscal year data
- Use MCP `extract_numeric_column` for efficiency
- Write Python code for complex math (e.g., HP filters)

---

### Pattern 3: Date-Specific Values

**Example Question:**
> Based on data as of the last day of June and September for years 1990-1992...

**Steps:**
1. Identify which bulletins contain these dates
2. September data appears in late-year bulletins
3. June data appears in mid-year bulletins
4. Extract values for each specified date
5. Perform calculations

---

### Pattern 4: Counting/Classification

**Example Question:**
> How many local maxima are there on the line plots?

**Difficulty:** These questions require visual analysis of charts that may not be preserved in text format.

**Approach:**
1. Search for any numeric data tables that support the charts
2. Look for "Exhibit" or figure descriptions
3. If no data available, note that visual analysis is not possible from text

---

## Unit Conversion Reference

| From | To | Formula |
|------|-----|---------|
| Thousands | Millions | ÷ 1,000 |
| Thousands | Billions | ÷ 1,000,000 |
| Millions | Billions | ÷ 1,000 |

### Example Conversions
```
8,124,453 thousand = 8,124.453 million = 8.124 billion
200,000 thousand = 200 million = 0.200 billion
```

## Rounding Rules

| Instruction | Example |
|-------------|---------|
| "Nearest whole number" | 8.124 → 8 |
| "Nearest thousandth" | 8.124453 → 8.124 |
| "Nearest hundredth" | 8.124453 → 8.12 |
| "Round to X decimal places" | Standard rounding |

## Error Prevention Checklist

Before writing your answer:

- [ ] Used MCP tools to find data (not just raw file reading)
- [ ] Verified the correct row/column in tables
- [ ] Checked table headers for units (thousands? millions?)
- [ ] Converted to requested units
- [ ] Applied correct rounding
- [ ] Formatted exactly as requested (brackets? commas?)
- [ ] Answered ALL sub-questions
- [ ] Wrote to `/app/answer.txt`
