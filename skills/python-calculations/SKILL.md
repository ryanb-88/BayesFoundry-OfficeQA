---
name: python-calculations
description: Guidance for performing complex numerical calculations in Python including time series analysis, HP filters, statistical computations, unit conversions, and result formatting.
---
# Python Calculation Utilities

## Overview
This skill provides guidance for performing complex numerical calculations in Python, such as:
- Time series analysis (e.g., Hodrick-Prescott filters)
- Statistical computations (e.g., mean, standard deviation)
- Unit conversions (e.g., thousands to millions, billions)
- Complex multi-step calculations

## Key Capabilities
- Time series analysis: HP filter, moving averages
- Statistical summaries: mean, std, variance
- Unit conversions: handle various formats (thousands, millions, billions)
- Complex calculations: Combine multiple operations
- Result formatting: Match expected answer format

## Usage Tips
1. Always verify units before converting
2. Use `thousands_to_millions()` or `thousands_to_billions()`
3. Round results appropriately
4. Write intermediate values to files for debugging
5. Handle errors gracefully
6. Use list comprehensions for complex multi-step logic
