---
name: answer-patterns
description: Common question types and answer formatting patterns for Treasury Bulletin QA tasks, including unit conversions, rounding rules, and multi-part answer formats.
---
# Common Answer Patterns

This guide shows common question types and how to format answers correctly.

## Answer Format Reference

### Single Number
**Question:** "What is the total capital?"
**Format:** Just the number (with units if specified)
```
8.124
```

### Date String
**Question:** "On what date did the T-bill rate gap first exceed X?"
**Format:** Full month name, day, year (no leading zeros on day)
```
March 3, 1977
```

**Rules for date answers:**
- Use full month name: January, February, March, April, May, June, July, August, September, October, November, December
- Day number WITHOUT leading zero: "3" not "03"
- Comma after day: "March 3, 1977"
- No "st", "nd", "rd", "th" suffix: "March 3" not "March 3rd"

### Percentage with % Sign
**Question:** "What was the YoY growth rate?"
**Format:** Number followed by percent sign
```
4.5%
```

**Rules for percentage answers:**
- If the question asks for a percentage, include the `%` sign
- Match the precision requested in the question
- If already expressed as a decimal in calculation, multiply by 100

### Text / Name Answer
**Question:** "Which country had the largest capital movement?"
**Format:** Plain text, exactly as it appears in the source document
```
United Kingdom
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
- Use bash loops for multi-file extraction
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

**Approach:**
1. Check the pre-analyzed chart answers table in the prompt first
2. If not listed, find the page/exhibit in the bulletin text
3. Search for underlying tabular data in the same bulletin
4. If data found in tables, extract and count programmatically:
   ```python
   maxima = sum(1 for i in range(1, len(vals) - 1) if vals[i] > vals[i-1] and vals[i] > vals[i+1])
   ```
5. For multi-series charts, count per series and sum

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

- [ ] Verified the correct row/column in tables
- [ ] Checked table headers for units (thousands? millions?)
- [ ] Converted to requested units
- [ ] Applied correct rounding
- [ ] Formatted exactly as requested — consider the answer TYPE:
  - **Numeric:** bare number or with units (e.g., `8.124`)
  - **Date:** full month name, day, year (e.g., `March 3, 1977`)
  - **Percentage:** number with `%` sign (e.g., `4.5%`)
  - **Bracketed list:** `[8.124, 12.852]`
  - **Multi-part:** `[val1, val2, val3]`
  - **Text:** plain text matching source document wording
- [ ] Answered ALL sub-questions
- [ ] Wrote to `/app/answer.txt`
