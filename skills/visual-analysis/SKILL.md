---
name: visual-analysis
description: Strategy for analyzing charts, line plots, and exhibits in Treasury Bulletin documents where underlying data points are not directly available in text form.
---
# Visual Chart & Exhibit Analysis

Refer to the main prompt for the chart/visual triage strategy, time limits, and page-reference lookup. This skill covers additional detail on what the text corpus preserves for each chart type.

## What the Text Corpus Preserves

| Chart Type | Preserved in Text | Lost |
|-----------|-------------------|------|
| Line plots | Title, axis labels, annotations, narrative | Data points, peaks, trends |
| Scatter plots | Title, axis labels, entity labels | Point positions |
| Bar charts | Title, categories | Bar heights if not labeled |
| Pie charts | Title, sometimes percentages in text | Visual proportions |

## Extracting Underlying Data

Charts often visualize data from tables in the same bulletin section. After finding the exhibit reference, search within ±50 lines for tabular data:

```bash
# Find the chart line number, then read surrounding context
grep -n "Exhibit 1" /app/corpus/FILENAME
# If chart is at line 410, check for tables nearby:
read /app/corpus/FILENAME offset=360 limit=100
```

## Using Annotations and Narrative

When no tabular data exists, look for:
- Specific numbers mentioned in text near the chart (e.g., "16.7% Average")
- Peak/trough annotations (e.g., "peak in 1973")
- Narrative paragraphs before/after the exhibit that describe trends
