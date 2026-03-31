---
name: visual-analysis
description: Strategy for analyzing charts, line plots, and exhibits in Treasury Bulletin documents where underlying data points are not directly available in text form.
---
# Visual Chart & Exhibit Analysis

## The Challenge

The text corpus preserves table data, headers, and annotations — but charts and plots only appear as exhibit titles, axis labels, and annotations. The actual data points are NOT in the text.

⚠️ **Time limit: Do NOT spend more than 5 minutes on chart questions.** Write your best estimate early and move on.

## Strategy

### Step 1: Find the exhibit/chart in the bulletin
```bash
grep -n "Exhibit\|Chart\|CHART" /app/corpus/FILENAME | head -20
```

### Step 2: Search for underlying tabular data (within ±50 lines)
Charts often visualize data from tables in the same bulletin section. Search for the chart's topic in nearby tables:
```bash
# Find the chart line number, then read surrounding context
grep -n "Exhibit 1" /app/corpus/FILENAME
# If chart is at line 410, check for tables nearby:
read /app/corpus/FILENAME offset=360 limit=100
```

### Step 3: If tabular data exists, compute programmatically
```python
def count_local_maxima(values):
    return sum(1 for i in range(1, len(values) - 1)
               if values[i] > values[i-1] and values[i] > values[i+1])
```

### Step 4: If no tabular data exists
Use exhibit descriptions, annotations, and narrative context to reason about the answer.
- Look for specific numbers mentioned in the text near the chart
- Check for annotations like "16.7% Average" or "peak in 1973"
- Use the narrative paragraphs before/after the exhibit for context

### Step 5: Write answer immediately
Do not iterate endlessly. Write your best estimate to `/app/answer.txt` after your first analysis pass.

## Common Chart Types in Treasury Bulletins

| Chart Type | What Text Preserves | What's Lost |
|-----------|-------------------|------------|
| Line plots | Title, axis labels, annotations, narrative | Data points, peaks, trends |
| Scatter plots | Title, axis labels, entity labels | Point positions |
| Bar charts | Title, categories | Bar heights if not labeled |
| Pie charts | Title, sometimes percentages in text | Visual proportions |

## Page-Reference for Charts

If the question references a specific page number:
1. Check the Table of Contents at the top of the bulletin file
2. The ToC maps section names to page numbers
3. Find which charts/exhibits are listed on that page
4. Then search for those exhibit names in the file body
