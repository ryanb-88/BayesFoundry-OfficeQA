# Visual Chart Analysis Guide

## Overview

Some Treasury Bulletin questions require analyzing visual charts, graphs, and line plots. Since the corpus contains text-only representations, special techniques are needed.

## Chart Types in Treasury Bulletins

### Time Series Line Plots
- Interest rates over time
- Budget receipts/outlays trends
- Economic indicators (GDP, saving rates, etc.)
- Debt levels

### Scatter Plots
- Cross-country comparisons (saving rates vs. GDP growth, etc.)
- Note: Scatter plots do NOT have local maxima in the time-series sense

### Bar Charts
- Comparisons across countries, time periods, or categories

## Key Concepts

### Local Maximum (Local Max)
A point where the value is higher than its immediate neighbors — any peak, even a small one.

### Local Minimum (Local Min)
A point where the value is lower than its immediate neighbors — any trough.

## Strategy for Visual Questions

### Step 1: Find the Underlying Data
Many charts are generated from table data in the bulletins. Before assuming the data is "visual only":
1. Use `search_tables_for_value` to search for the exhibit title or subject
2. Look for tables that cover the same time period and topic
3. Check the text for data annotations or narrative descriptions of the chart

### Step 2: Extract Data Points
If you find a corresponding table:
1. Extract the numeric values for the relevant series
2. Use Python to identify peaks/troughs programmatically:

```python
def count_local_maxima(values):
    """Count local maxima in a list of values."""
    count = 0
    for i in range(1, len(values) - 1):
        if values[i] > values[i-1] and values[i] > values[i+1]:
            count += 1
    return count
```

### Step 3: If No Data Table Exists
If the chart data is not available in any table:
- Note this limitation clearly
- Look for text descriptions of trends, peaks, or specific values
- Check for source data references that might point to other tables

## Multiple Series on One Chart
When a chart contains multiple line plots (e.g., "Private Saving" and "Total Saving"):
- Count features on each line separately
- The question may ask for the total across all lines, or per line — read carefully

## Important Notes

⚠️ Always try to find the actual data before guessing. MCP search tools can locate tables corresponding to chart exhibits.

⚠️ Distinguish between chart types: scatter plots, line plots, and bar charts require different analysis approaches.

⚠️ Read the question carefully — "local maxima on the line plots" is different from "peaks on the bar chart."
