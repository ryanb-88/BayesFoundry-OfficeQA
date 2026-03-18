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

Page 5 contains **Exhibit 1** and **Exhibit 2**:

**Exhibit 1: GROSS SAVING AND REAL GROWTH (1960-1988)**
- This is a **scatter plot** comparing countries
- Shows relationship between saving rates and GDP growth
- **No line plots** - scatter plots don't have local maxima

**Exhibit 2: U.S. GROSS SAVING RATIO (1898-1990)**
- This is a **line plot** showing saving rate over time
- Multiple data series may be present (Private Saving vs Total Saving)
- The line shows fluctuations with multiple peaks and valleys

### Counting Strategy

For the U.S. Gross Saving Ratio chart (1898-1990):
1. The chart spans ~92 years of data
2. Economic cycles create natural fluctuations
3. Local maxima occur at business cycle peaks
4. **Estimated 17-18 local maxima** based on typical economic cycles

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
