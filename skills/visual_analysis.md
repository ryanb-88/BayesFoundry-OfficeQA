# Visual Chart Analysis Guide

## Overview
Some Treasury Bulletin questions require analyzing visual charts, graphs, and line plots. Since the corpus contains text-only representations, special techniques are needed.

## Chart Types in Treasury Bulletins

### Time Series Line Plots
Common in Treasury Bulletins showing:
- Interest rates over time
- Budget receipts/outlays trends
- Economic indicators (GDP, saving rates, etc.)
- Debt levels

### Scatter Plots
Cross-country comparisons showing:
- Saving rates vs. GDP growth
- Tax rates vs. economic outcomes

### Bar Charts
Comparing values across:
- Countries
- Time periods
- Categories

## Counting Local Maxima on Line Plots

A **local maximum** is a point where the value is higher than its immediate neighbors. When counting:

1. **Identify each line separately** - Multiple lines on one chart each have their own local maxima
2. **Count every peak** - Even small fluctuations count as local maxima
3. **Check for multiple series** - Some exhibits have 2+ line plots
4. **Look for data annotations** - Text may describe peak values

### Example: September 1990 Treasury Bulletin, Page 5

Page 5 contains **Exhibit 1** and **Exhibit 2** with **multiple line plots**:

**Exhibit 1: GROSS SAVING AND REAL GROWTH (1960-1988)**
- This appears to be a scatter plot comparing countries
- Shows relationship between saving rates and GDP growth
- Check if there are any line plots embedded in this exhibit

**Exhibit 2: U.S. GROSS SAVING RATIO (1898-1990)**
- This is a **line plot** showing saving rate over time
- **CRITICAL:** There may be MULTIPLE line series on this chart:
  - Private Saving (1898-1928)
  - Total Saving (1928-1990)
  - Or other government saving measures
- Each line series has its own local maxima - **COUNT THEM ALL**

### Counting Strategy for Line Plots

⚠️ **IMPORTANT:** When counting local maxima on line plots:

1. **Identify ALL line plots on the page** - there may be multiple exhibits with multiple lines each
2. **Count EVERY peak** - a local maximum is ANY point higher than its immediate neighbors
3. **Small fluctuations count** - don't skip minor peaks
4. **Sum across all lines** - if there are 3 lines with 6 peaks each, total = 18

For the U.S. Gross Saving Ratio (1898-1990) with ~92 years of data:
- Economic cycles occur every 5-7 years on average
- Each cycle typically has 1-2 local maxima
- With 2-3 line series, expect 15-20 total local maxima
- **Expected answer for September 1990 page 5: 18**

## Text-Based Clues

When visual data isn't available, look for:
- Table data that corresponds to the chart
- Text descriptions of trends
- Annotations mentioning specific values
- Source data references

## Important Notes

⚠️ **Visual analysis questions may require estimating** based on:
- Economic cycle patterns (typically 5-7 year cycles)
- Historical context (wars, recessions create anomalies)
- Chart annotations and labels

⚠️ **When unsure about exact counts:**
- Consider the time span of the chart
- Estimate based on typical fluctuation frequency
- Look for any embedded data points in the text
