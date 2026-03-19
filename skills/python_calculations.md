# Python Calculation Utilities

## Overview

This skill provides code templates for common numerical calculations in OfficeQA tasks.

## Hodrick-Prescott (HP) Filter

Used to decompose time series into trend and cyclical components.

```python
import numpy as np

def hp_filter(y, lamb=1600):
    """Hodrick-Prescott filter.

    Args:
        y: Array of time series values
        lamb: Smoothing parameter (1600 for quarterly, 6.25 for annual, 129600 for monthly)

    Returns:
        trend: Trend component
        cycle: Cyclical component (y - trend)
    """
    n = len(y)
    # Construct the penalty matrix
    diag0 = np.ones(n)
    diag1 = np.ones(n - 1) * (-2)
    diag2 = np.ones(n - 2)
    D = np.zeros((n - 2, n))
    for i in range(n - 2):
        D[i, i] = 1
        D[i, i + 1] = -2
        D[i, i + 2] = 1
    I = np.eye(n)
    trend = np.linalg.solve(I + lamb * D.T @ D, y)
    cycle = y - trend
    return trend, cycle

# Example usage with Treasury data:
# values = [8124, 8245, 8389, ...]  # extracted from bulletins
# trend, cycle = hp_filter(np.array(values, dtype=float), lamb=6.25)  # annual data
```

If `statsmodels` is available, prefer the library version:

```python
from statsmodels.tsa.filters.hp_filter import hpfilter
cycle, trend = hpfilter(data, lamb=6.25)  # annual lambda
```

## Year-over-Year (YoY) Growth Rate

```python
def yoy_growth_rate(current, previous):
    """Compute year-over-year growth rate as a percentage.

    Args:
        current: Value for current period
        previous: Value for prior period

    Returns:
        Growth rate as percentage (e.g., 5.2 means 5.2%)
    """
    if previous == 0:
        return float('inf')
    return ((current - previous) / abs(previous)) * 100

# Example: compute YoY for a series
# values = {2010: 1832816, 2011: 2049753, 2012: 2163457, ...}
# for year in sorted(values)[1:]:
#     prev_year = year - 1
#     rate = yoy_growth_rate(values[year], values[prev_year])
#     print(f"FY{year}: {rate:.4f}%")
```

## Mean / Average

```python
def compute_mean(values):
    """Compute arithmetic mean of a list of numbers."""
    if not values:
        return 0.0
    return sum(values) / len(values)
```

## Unit Conversions

```python
def thousands_to_millions(val):
    """Convert thousands of dollars to millions."""
    return val / 1000

def thousands_to_billions(val):
    """Convert thousands of dollars to billions."""
    return val / 1_000_000

def millions_to_billions(val):
    """Convert millions of dollars to billions."""
    return val / 1000

# Example:
# raw_value = 8_124_453  # from table, in thousands
# in_billions = thousands_to_billions(raw_value)  # 8.124453
# rounded = round(in_billions, 3)  # 8.124
```

## Parsing Treasury Numbers

```python
def parse_treasury_number(text):
    """Parse a number from Treasury Bulletin format.

    Handles commas, parentheses for negatives, and common non-numeric markers.

    Args:
        text: String value from table cell (e.g., "8,124,453" or "(1,234)")

    Returns:
        Float value, or None if not parseable
    """
    s = str(text).strip()
    if s in ("-", "n/a", "n.a.", "", "..."):
        return None
    is_negative = s.startswith("(") and s.endswith(")")
    if is_negative:
        s = s[1:-1]
    s = s.replace(",", "")
    try:
        val = float(s)
        return -val if is_negative else val
    except ValueError:
        return None
```

## Tips

- Always verify units in table headers before computing
- Use `round()` only at the final step, not intermediate calculations
- Write intermediate values to files for debugging when calculations are complex
- Treasury Bulletin tables in "thousands" are the most common format
