---
name: visual-analysis
description: Strategy for analyzing charts, line plots, and exhibits in Treasury Bulletin documents where underlying data points are not directly available in text form.
---
# Visual Chart & Exhibit Analysis

## The Challenge

The text corpus preserves table data, headers, and annotations — but charts and plots only appear as exhibit titles, axis labels, and annotations. The actual data points are NOT in the text.

## Strategy

### Step 1: Find the exhibit/chart in the bulletin
```bash
grep -n "Exhibit\|Chart\|CHART" /app/corpus/FILENAME | head -20
```

### Step 2: Search for underlying tabular data
Charts often visualize data from tables in the same bulletin section. Search for the chart's topic in nearby tables.

### Step 3: If tabular data exists, compute programmatically
```python
def count_local_maxima(values):
    return sum(1 for i in range(1, len(values) - 1)
               if values[i] > values[i-1] and values[i] > values[i+1])
```

### Step 4: If no tabular data exists
Use exhibit descriptions, annotations, and narrative context to reason about the answer.

## Common Chart Types in Treasury Bulletins

| Chart Type | What Text Preserves | What's Lost |
|-----------|-------------------|------------|
| Line plots | Title, axis labels, annotations | Data points, peaks, trends |
| Scatter plots | Title, axis labels, entity labels | Point positions |
| Bar charts | Title, categories | Bar heights if not labeled |
