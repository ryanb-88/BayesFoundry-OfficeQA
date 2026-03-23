---
name: visual-analysis
description: Strategy for analyzing charts, line plots, and exhibits in Treasury Bulletin documents where underlying data points are not directly available in text form.
---
# Visual Chart & Exhibit Analysis

## The Challenge

The Treasury Bulletin text corpus preserves table data, section headers, and annotations — but charts and plots are only partially represented. You'll find exhibit titles, axis labels, source notes, and sometimes annotations, but NOT the underlying data points that make up line plots, scatter plots, or bar charts.

## Strategy for Chart/Visual Questions

### Step 1: Identify the page and exhibits
Use grep or `read_bulletin_section` to find the page. Look for:
- `Exhibit N` headers
- Chart titles (often ALL CAPS)
- Axis labels and annotations
- Source notes below charts

### Step 2: Determine what type of analysis is needed

**If the question asks about chart metadata** (titles, axis labels, what's depicted):
- This CAN be answered from text. Extract exhibit titles, annotations, and descriptions.

**If the question asks about data values shown in a chart:**
- Check if the same data appears in a nearby table (charts often visualize tabular data from the same bulletin)
- Search for the chart's topic in the same file's tables
- If the data exists in tables, extract it and perform the analysis

**If the question asks about visual features** (local maxima, peaks, crossings, slopes):
- First check if underlying data exists in tables — if so, you can compute maxima/peaks programmatically
- If no tabular data exists for the chart, extract whatever context you can (time range, series names, annotations about peaks/troughs) and reason carefully
- Use annotations like "16.7% Average" or "Depression of 1930s" as anchoring clues

### Step 3: For line plot analysis when data IS available in tables

If you find the underlying data in a table:
```python
# Count local maxima in a series
def count_local_maxima(values):
    maxima = 0
    for i in range(1, len(values) - 1):
        if values[i] > values[i-1] and values[i] > values[i+1]:
            maxima += 1
    return maxima
```

### Step 4: Cross-reference multiple sources

Charts in Treasury Bulletins often correspond to:
- Tables in the same section (most common)
- Data from previous bulletins referenced in the text
- Summary statistics mentioned in narrative sections

Always search the same bulletin for tabular versions of charted data before concluding the data is unavailable.

## Common Chart Types in Treasury Bulletins

| Chart Type | What Text Preserves | What's Lost |
|-----------|-------------------|------------|
| Line plots | Title, axis labels, annotations, source | Data points, peaks, trends |
| Scatter plots | Title, axis labels, country/entity labels | Point positions, correlations |
| Bar charts | Title, categories, sometimes values in labels | Bar heights if not labeled |
| Tables as charts | Full data (these are actually tables) | Nothing — fully preserved |

## Tips

- Exhibits are numbered sequentially within each bulletin article
- Chart annotations often mention key statistics (averages, notable events)
- The text around a chart often discusses the trends shown — use narrative context
- If a question seems impossible from text alone, double-check that no table contains the same data
