---
name: python-calculations
description: Ready-to-use Python snippets for common numerical calculations in Treasury Bulletin QA tasks including geometric mean, Theil index, volatility, CAGR, Euclidean norm, and HP filter.
---
# Python Calculation Utilities

This skill provides ready-to-use Python snippets for complex numerical calculations. Copy-paste these into a `python3 -c "..."` or write a `.py` script.

## Geometric Mean

Use when the question asks for "geometric mean" of a series of rates or values.

```python
import statistics

values = [0.05, 0.03, 0.07, 0.04]  # replace with your values
gm = statistics.geometric_mean(values)
print(f"Geometric mean: {gm}")
```

For percentage values like "5.3%, 4.8%, 6.1%", convert to decimals first:
```python
rates_pct = [5.3, 4.8, 6.1]  # in percent
rates = [r / 100 for r in rates_pct]
gm = statistics.geometric_mean(rates) * 100
print(f"Geometric mean: {gm:.4f}%")
```

For geometric mean of raw values (not rates):
```python
from functools import reduce
import operator

values = [120, 135, 128, 142]
gm = reduce(operator.mul, values, 1) ** (1.0 / len(values))
print(f"Geometric mean: {gm:.4f}")
```

## Geometric Mean of Discount Rates

Special case for T-bill discount rates across multiple periods. Extract rates from bulletins first, then:

```python
import statistics

discount_rates = [5.25, 5.50, 5.75, 6.00]  # replace with extracted rates (in %)
gm = statistics.geometric_mean([r / 100 for r in discount_rates]) * 100
print(f"Geometric mean of discount rates: {gm:.4f}%")
```

## Theil Index of Dispersion

Use for measuring inequality or dispersion of a distribution (e.g., securities holdings across countries).

```python
import math

# shares must sum to 1.0 (proportions of total)
shares = [0.35, 0.25, 0.20, 0.15, 0.05]  # replace with your values
n = len(shares)

theil = (1.0 / n) * sum(
    s * math.log(n * s) for s in shares if s > 0
)
print(f"Theil index: {theil:.6f}")
```

If you have raw values (not shares), normalize first:
```python
import math

values = [350, 250, 200, 150, 50]  # replace with your values
total = sum(values)
shares = [v / total for v in values]
n = len(shares)

theil = (1.0 / n) * sum(
    s * math.log(n * s) for s in shares if s > 0
)
print(f"Theil index: {theil:.6f}")
```

## Annualized Realized Volatility (Brownian Motion Model)

Use when asked for "annualized volatility" or "realized volatility" based on a series of returns or price changes.

```python
import math

# daily (or periodic) returns as decimals, e.g. [0.02, -0.01, 0.03, ...]
returns = [0.02, -0.01, 0.03, -0.015, 0.025, 0.01, -0.005]  # replace with your values
n = len(returns)
mean_r = sum(returns) / n
variance = sum((r - mean_r) ** 2 for r in returns) / (n - 1)  # sample variance
period_vol = math.sqrt(variance)  # periodic volatility

# Annualize: multiply by sqrt of periods per year
# For monthly returns: sqrt(12), for weekly: sqrt(52), for daily: sqrt(252)
periods_per_year = 12  # adjust based on data frequency
annualized_vol = period_vol * math.sqrt(periods_per_year)

print(f"Period volatility: {period_vol:.6f}")
print(f"Annualized volatility: {annualized_vol:.6f}")
print(f"Annualized volatility (pct): {annualized_vol * 100:.4f}%")
```

If the question specifies "geometric Brownian motion" or "log returns":
```python
import math

prices = [100, 102, 99, 103, 105, 101, 104]  # replace with price series
log_returns = [math.log(prices[i] / prices[i-1]) for i in range(1, len(prices))]
n = len(log_returns)
mean_lr = sum(log_returns) / n
variance = sum((r - mean_lr) ** 2 for r in log_returns) / (n - 1)
period_vol = math.sqrt(variance)

periods_per_year = 12  # adjust as needed
annualized_vol = period_vol * math.sqrt(periods_per_year)
print(f"Annualized volatility (log returns): {annualized_vol:.6f}")
```

## CAGR (Compound Annual Growth Rate)

Use when asked for compound annual growth rate over a period.

```python
beginning_value = 1200.5  # replace with start value
ending_value = 1850.3     # replace with end value
n_years = 5               # number of years

cagr = (ending_value / beginning_value) ** (1.0 / n_years) - 1
print(f"CAGR: {cagr:.6f} ({cagr * 100:.4f}%)")
```

For CAGR from a series of annual values:
```python
values = [1200.5, 1310.2, 1425.8, 1530.1, 1680.5, 1850.3]  # chronological
cagr = (values[-1] / values[0]) ** (1.0 / (len(values) - 1)) - 1
print(f"CAGR over {len(values)-1} years: {cagr:.6f} ({cagr * 100:.4f}%)")
```

## Euclidean Norm (L2 Norm)

Use when asked for "Euclidean norm" or "L2 norm" of a vector of changes or differences.

```python
import math

changes = [0.15, -0.22, 0.08, -0.31, 0.12]  # replace with your values
norm = math.sqrt(sum(c ** 2 for c in changes))
print(f"Euclidean norm: {norm:.6f}")
```

For a series of T-bill rate changes:
```python
import math

# Extract rate changes from bulletins, then:
rate_changes = [0.15, -0.22, 0.08, -0.31, 0.12]  # replace with extracted changes
norm = math.sqrt(sum(c ** 2 for c in rate_changes))
print(f"L2 norm of rate changes: {norm:.4f}")
```

## HP Filter (Hodrick-Prescott)

Use for decomposing a time series into trend and cyclical components. Requires statsmodels.

**Install first if needed:**
```bash
pip install statsmodels
```

```python
import numpy as np
from statsmodels.tsa.filters.hp_filter import hpfilter

# Quarterly data: lambda = 1600, Annual: lambda = 100, Monthly: lambda = 14400
data = np.array([120.5, 125.3, 130.1, 128.7, 135.2, 140.8, 138.5, 145.3])  # replace

cycle, trend = hpfilter(data, lamb=1600)  # adjust lamb for data frequency

print("Trend component:")
for i, t in enumerate(trend):
    print(f"  Period {i+1}: {t:.4f}")
print("Cyclical component:")
for i, c in enumerate(cycle):
    print(f"  Period {i+1}: {c:.4f}")
```

Typical usage — extract trend from receipts/outlays and compute cyclical component:
```python
import numpy as np
from statsmodels.tsa.filters.hp_filter import hpfilter

# Example: federal receipts over 8 periods
receipts = np.array([1000, 1050, 1100, 1080, 1150, 1200, 1180, 1250])
cycle, trend = hpfilter(receipts, lamb=1600)

print(f"Trend values: {trend.round(2)}")
print(f"Cyclical values: {cycle.round(4)}")
```

## General Tips

1. **Always verify units before converting** — table values may be in thousands, millions, or raw units
2. **Round results appropriately** — check the question's rounding instructions
3. **Write intermediate values to files for debugging** if calculations are multi-step
4. **Handle edge cases**: empty series, zero values, negative numbers
5. **Use `python3 -c "..."` for quick one-liners**, or write a `.py` file for multi-step calculations
