# Question Patterns and How to Solve Them

Each pattern below maps to a specific solving strategy.

---

## Pattern 1: Single Value Lookup
**Example:** "What were total expenditures for national defense in calendar year 1940?"

**Strategy:**
1. Search the bulletin from early 1941 for a table with monthly 1940 defense values
2. Sum all 12 months (Jan–Dec 1940) — don't use fiscal year "Total" column
3. Check units (millions? billions?)

**MCP tools:** `search_corpus(keyword="national defense", year_from=1940, year_to=1942)`

---

## Pattern 2A: Absolute Percent CHANGE (uses ONE base value)
**Trigger words:** "percent change", "percent increase", "percent decrease", "percent growth"
**Example:** "What was the absolute percent change of X from year A to year B?"

**Formula:** `|value_B - value_A| / |value_A| × 100`

```python
val_a = 1234.5   # EARLIER / BASE value
val_b = 21093.0  # LATER value
pct = abs(val_b - val_a) / abs(val_a) * 100
print(f"{pct:.2f}%")
```

**Watch out:** "absolute" means always positive even if decreased.

---

## Pattern 2B: Absolute Percent DIFFERENCE (uses AVERAGE as denominator)
**Trigger words:** "percent difference", "absolute percent difference"
**Example:** "What is the absolute percent difference between X in period A and Y in period B?"

**Formula:** `|A - B| / ((A + B) / 2) × 100`

```python
val_a = 528.0
val_b = 693.0
pct_diff = abs(val_a - val_b) / ((val_a + val_b) / 2) * 100
print(f"{pct_diff:.1f}")  # e.g. 27.0 → write "27"
```

**CRITICAL:** "Percent difference" ≠ "Percent change".
- Percent change: divide by the starting/older value
- Percent difference: divide by the average of the two values

---

## Pattern 3: Sum Across a Date Range
**Example:** "List total gross debt end of fiscal month January from 1969 to 1980"

**Strategy:**
1. Use `batch_extract` to pull January bulletins for 1969–1980 all at once
2. Extract one value per year
3. Return as comma-separated list

**MCP tools:** `batch_extract(keyword="gross debt", year_from=1969, year_to=1980, month=1)`

---

## Pattern 4: Geometric Mean
**Example:** "What is the geometric mean of weekly discount rates for September 1953–1955?"

**Formula:** `(v1 × v2 × ... × vn)^(1/n)`

```python
import math
values = [1.23, 1.45, 1.38, ...]  # extract from bulletins
geo_mean = math.prod(values) ** (1 / len(values))
print(f"{geo_mean:.3f}")
```

---

## Pattern 5: Linear Regression
**Example:** "Predict 1999 value using 1990–1998 data. Treat 1990 as year 0."

```python
xs = list(range(9))   # 0 through 8 (years 1990–1998)
ys = [...]            # extracted values for each year

n = len(xs)
sum_x = sum(xs)
sum_y = sum(ys)
sum_xy = sum(x*y for x, y in zip(xs, ys))
sum_x2 = sum(x**2 for x in xs)

slope = (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x**2)
intercept = (sum_y - slope*sum_x) / n
predicted = slope * 9 + intercept   # year 9 = 1999

print(f"slope={slope:.2f}, intercept={round(intercept)}, predicted={round(predicted)}")
```

---

## Pattern 6: Specific Date Lookup (e.g., bill auction dates)
**Example:** "On which March 1977 date was the gap between 13-week and 26-week T-bill rates smallest?"

**Strategy:**
1. Read `treasury_bulletin_1977_03.txt` or `_04.txt`
2. Find the weekly T-bill rate table
3. Compute 26-week minus 13-week for each Thursday row
4. Find the row with minimum gap
5. Return date in U.S. long format: `March 17, 1977`

---

## Pattern 7: Multi-Document Aggregation With External Context
**Example:** "Sum net capital movements for gold bloc countries in 1935, excluding Belgium, Poland, Luxembourg"

**Strategy:**
1. Web search: "gold bloc countries 1935" to identify members
2. Search corpus for capital movement tables covering 1935
3. Extract values for each gold bloc country (excluding the named ones)
4. Sum and report in specified units/precision

---

## Pattern 8: Visual/Chart Question
**Example:** "On page 5 of the September 1990 bulletin, how many local maxima are on the line plots?"

These questions reference charts — the text corpus won't have the image.
- These are rare (~3% of questions)
- The text file may have a text description or data table near the chart reference
- Search for surrounding context; if no data is available, state your best estimate from any nearby text

---

## Pattern 9: Compound Annual Growth Rate (CAGR)
**Example:** "What is the CAGR of X from year A to year B?"

**Formula:** `(end_value / start_value)^(1/n_years) - 1`

```python
start_val = 1000.0
end_val = 2000.0
n_years = 10  # from 2003 to 2013
cagr = (end_val / start_val) ** (1 / n_years) - 1
print(f"{cagr * 100:.2f}")  # e.g. 7.18
```

---

## Pattern 10: Theil Index of Dispersion
**Example:** "What is the Theil index of dispersion of X from 1961 to 1970?"

**Formula:** `T = (1/n) * sum(x_i/mean * ln(x_i/mean))`

```python
import math
values = [...]  # extracted series
n = len(values)
mean = sum(values) / n
theil = (1/n) * sum((v/mean) * math.log(v/mean) for v in values)
print(f"{theil:.3f}")
```

---

## Pattern 11: Hodrick-Prescott (HP) Filter
**Example:** "Apply HP filter with λ=100 to receipts and outlays series, report structural balance."

```python
import numpy as np

def hp_filter(y, lam=100):
    """Returns trend component via HP filter."""
    n = len(y)
    y = np.array(y, dtype=float)
    # Build second-difference matrix
    D = np.zeros((n-2, n))
    for i in range(n-2):
        D[i, i] = 1
        D[i, i+1] = -2
        D[i, i+2] = 1
    # Solve: (I + lam * D'D) * trend = y
    A = np.eye(n) + lam * D.T @ D
    trend = np.linalg.solve(A, y)
    return trend

receipts = [...]  # FY2010–FY2024 values
outlays = [...]
trend_r = hp_filter(receipts, lam=100)
trend_o = hp_filter(outlays, lam=100)

structural_balance = trend_r[-1] - trend_o[-1]  # FY2024
actual_balance = receipts[-1] - outlays[-1]      # FY2024
gap = abs(actual_balance - structural_balance)
print(f"[{round(actual_balance)}, {round(structural_balance)}, {round(gap)}]")
```

---

## Pattern 12: Annualized Realized Volatility (Brownian Motion)
**Example:** "Compute annualized realized volatility of discount rate using log returns."

```python
import math
rates = [r1, r2, ...]  # weekly discount rates
log_returns = [math.log(rates[i+1]/rates[i]) for i in range(len(rates)-1)]
realized_var = sum(r**2 for r in log_returns)  # sum of squared returns
# Annualize: multiply by 52 (weekly → annual), then sqrt for volatility
annualized_vol = math.sqrt(realized_var * 52)
print(f"{annualized_vol * 100:.2f}%")  # output as percent
```

---

## Pattern 13: Euclidean Norm of Changes
**Example:** "Report the Euclidean norm of two absolute changes."

```python
import math
change1 = abs(val_a2 - val_a1)
change2 = abs(val_b2 - val_b1)
norm = math.sqrt(change1**2 + change2**2)
print(f"{norm:.2f}")
```

---

## Pattern 14: Standard Deviation (Population and Sample)
**Trigger words:** "standard deviation", "population standard deviation", "sample standard deviation", "std dev", "price volatility"

```python
import math
values = [...]  # extracted series

n = len(values)
mean = sum(values) / n

# Population std dev (σ) — divide by n
# Use when: "population standard deviation" or data IS the full population
pop_var = sum((v - mean)**2 for v in values) / n
pop_std = math.sqrt(pop_var)

# Sample std dev (s) — divide by (n-1)
# Use when: "sample standard deviation" or data is a sample
samp_var = sum((v - mean)**2 for v in values) / (n - 1)
samp_std = math.sqrt(samp_var)

print(f"{pop_std:.6f}")   # or samp_std
```

**When to use which:**
- "population standard deviation" → divide by **n**
- "sample standard deviation" → divide by **n-1**
- No qualifier → usually sample (n-1), but check context

---

## Pattern 15: Coefficient of Variation (CV)
**Trigger words:** "coefficient of variation", "CV", "relative variability"

**Formula:** `CV = std_dev / mean × 100` (usually as a percent)

```python
import math
values = [...]
n = len(values)
mean = sum(values) / n
std = math.sqrt(sum((v - mean)**2 for v in values) / (n - 1))  # sample std
cv = (std / mean) * 100
print(f"{cv:.2f}%")   # or without % if not requested
```

---

## Pattern 16: Median
**Trigger words:** "median", "middle value"

```python
values = sorted([...])
n = len(values)
if n % 2 == 1:
    median = values[n // 2]
else:
    median = (values[n // 2 - 1] + values[n // 2]) / 2
print(f"{median:.2f}")
```

**Tukey exclusive median hinge method** (for quartiles):
- Q1 = median of lower half (excluding median if n is odd)
- Q3 = median of upper half (excluding median if n is odd)

```python
values = sorted([...])
n = len(values)
half = n // 2
lower = values[:half]
upper = values[n - half:]   # excludes middle if odd
q1 = (lower[len(lower)//2 - 1] + lower[len(lower)//2]) / 2 if len(lower) % 2 == 0 else lower[len(lower)//2]
q3 = (upper[len(upper)//2 - 1] + upper[len(upper)//2]) / 2 if len(upper) % 2 == 0 else upper[len(upper)//2]
iqr = q3 - q1
h_spread = iqr   # H-spread = IQR
print(f"Q1={q1}, Q3={q3}, IQR/H-spread={h_spread:.2f}")
```

---

## Pattern 17: Pearson Correlation and R-squared
**Trigger words:** "correlation", "pearson correlation", "r-square", "r2", "coefficient of correlation"

```python
import math
xs = [...]   # independent variable
ys = [...]   # dependent variable
n = len(xs)

mean_x = sum(xs) / n
mean_y = sum(ys) / n

cov = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n)) / n
std_x = math.sqrt(sum((x - mean_x)**2 for x in xs) / n)
std_y = math.sqrt(sum((y - mean_y)**2 for y in ys) / n)

r = cov / (std_x * std_y)          # Pearson r
r_squared = r ** 2                  # R²

print(f"r={r:.4f}, R²={r_squared:.4f}")
```

**For linear regression (OLS) slope + intercept:**
```python
slope = sum((xs[i]-mean_x)*(ys[i]-mean_y) for i in range(n)) / sum((x-mean_x)**2 for x in xs)
intercept = mean_y - slope * mean_x
predicted_at_x = slope * x_new + intercept
print(f"slope={slope:.4f}, intercept={intercept:.4f}, predicted={predicted_at_x:.4f}")
```

**R² from regression:**
```python
ss_res = sum((ys[i] - (slope*xs[i] + intercept))**2 for i in range(n))
ss_tot = sum((y - mean_y)**2 for y in ys)
r_sq = 1 - ss_res / ss_tot
print(f"R²={r_sq:.4f}")
```

---

## Pattern 18: Argmax / Argmin ("which year had the highest X")
**Trigger words:** "highest", "lowest", "maximum", "minimum", "which year", "which month", "find the year"

```python
values = {'1960': 123.4, '1961': 156.7, '1962': 98.2, ...}  # dict of label→value

max_label = max(values, key=lambda k: values[k])
min_label = min(values, key=lambda k: values[k])

print(f"Max: {max_label} = {values[max_label]}")
print(f"Min: {min_label} = {values[min_label]}")
```

Or with parallel lists:
```python
labels = ['1960', '1961', '1962']
vals   = [123.4,  156.7,  98.2]
print(labels[vals.index(max(vals))])   # year with highest value
print(labels[vals.index(min(vals))])   # year with lowest value
```

---

## Pattern 19: Moving Average (Simple n-period)
**Trigger words:** "moving average", "n-month moving average", "rolling average", "centered moving average"

```python
values = [...]    # time series
n = 3             # window size (e.g., 3-month moving average)

# Trailing moving average (ends at current point):
trailing_ma = [sum(values[i-n+1:i+1])/n for i in range(n-1, len(values))]

# Centered moving average (odd window only):
half = n // 2
centered_ma = [sum(values[i-half:i+half+1])/n for i in range(half, len(values)-half)]

print(trailing_ma)
print(centered_ma)
```

**Range of moving averages** = max(MA) - min(MA)

---

## Pattern 20: Z-Score
**Trigger words:** "z-score", "standard score", "unusual", "how many standard deviations"

```python
import math
values = [...]
target = ...   # the value to score

mean = sum(values) / len(values)
std = math.sqrt(sum((v - mean)**2 for v in values) / len(values))   # population std
z = (target - mean) / std
print(f"{z:.2f}")
```

---

## Pattern 21: Counting ("how many X satisfy condition Y")
**Trigger words:** "how many", "count", "number of", "how many times", "excluding row/column headers"

```python
values = [...]   # extracted series

# Count values exceeding a threshold:
count = sum(1 for v in values if v > threshold)

# Count distinct categories:
categories = [...]
count_unique = len(set(categories))

# Count cells in a table region (e.g., rows × cols, minus headers):
rows = 10
cols = 8
total_cells = rows * cols   # adjust for headers as needed

print(count)
```

---

## Pattern 22: Percentile (Hazen plotting position, VaR, nth percentile)
**Trigger words:** "percentile", "value-at-risk", "VaR", "expected shortfall", "hazen", "85th percentile"

```python
values = sorted([...])
n = len(values)

# Standard percentile (interpolated):
def percentile(data, p):
    """p is 0-100"""
    data = sorted(data)
    idx = (p / 100) * (len(data) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(data) - 1)
    return data[lo] + (idx - lo) * (data[hi] - data[lo])

# Hazen plotting position (used in hydrology/treasury questions):
# P_i = (i - 0.5) / n  where i is rank (1-based)
def hazen_percentile(data, p):
    data = sorted(data)
    n = len(data)
    # Find i where (i-0.5)/n = p/100 → i = p*n/100 + 0.5
    idx = (p / 100) * n + 0.5 - 1   # convert to 0-based
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    frac = idx - lo
    return data[lo] + frac * (data[hi] - data[lo])

# VaR at 95% (5th percentile of losses, or 95th of gains):
var_95 = percentile(values, 5)   # if values are returns/changes

# Expected Shortfall at 95% = mean of values below VaR:
cutoff = percentile(values, 5)
es_95 = sum(v for v in values if v <= cutoff) / sum(1 for v in values if v <= cutoff)

print(f"85th Hazen percentile: {hazen_percentile(values, 85):.2f}")
print(f"VaR 95%: {var_95:.2f}")
print(f"ES 95%: {es_95:.2f}")
```

---

## Pattern 23: Skewness and Kurtosis
**Trigger words:** "skewness", "Fisher-Pearson", "kurtosis", "excess kurtosis"

```python
import math
values = [...]
n = len(values)
mean = sum(values) / n
std = math.sqrt(sum((v - mean)**2 for v in values) / (n - 1))   # sample std

# Fisher-Pearson adjusted skewness (unbiased):
skew_raw = (n / ((n-1)*(n-2))) * sum(((v - mean)/std)**3 for v in values)

# Sample excess kurtosis (Fisher):
kurt = ((n*(n+1)) / ((n-1)*(n-2)*(n-3))) * sum(((v-mean)/std)**4 for v in values) \
       - (3*(n-1)**2) / ((n-2)*(n-3))

print(f"Skewness: {skew_raw:.3f}")
print(f"Excess Kurtosis: {kurt:.3f}")
```

---

## Pattern 24: Log Growth Rate / Continuously Compounded Rate
**Trigger words:** "logarithmic growth", "continuously compounded", "log change", "natural log of ratio"

```python
import math
start_val = ...
end_val = ...
n_periods = ...   # number of years/months

# Continuously compounded annual growth rate:
log_growth = math.log(end_val / start_val) / n_periods
print(f"{log_growth:.4f}")   # e.g. 0.045 means 4.5%

# Log return (single period):
log_return = math.log(end_val / start_val)
print(f"{log_return:.4f}")
```

---

## Pattern 25: Trimmed Mean and Winsorized Range
**Trigger words:** "trimmed mean", "winsorized", "truncated mean"

```python
values = sorted([...])
n = len(values)

# p% trimmed mean — drop bottom p% and top p% before averaging:
p = 0.10   # 10% trim (20% total)
cut = int(n * p)
trimmed = values[cut:n-cut]
trimmed_mean = sum(trimmed) / len(trimmed)

# Winsorized range — replace extremes, report range of middle values:
# 10% Winsorized: replace bottom 10% with [10th pct value], top 10% with [90th pct value]
lo_val = values[cut]
hi_val = values[n - 1 - cut]
winsorized_range = hi_val - lo_val

print(f"Trimmed mean: {trimmed_mean:.4f}")
print(f"Winsorized range: {winsorized_range:.4f}")
```

---

## Pattern 26: Gini Coefficient
**Trigger words:** "gini coefficient", "gini index", "inequality"

```python
values = sorted([v for v in [...] if v > 0])  # must be positive
n = len(values)
total = sum(values)

# Standard formula:
gini = (2 * sum((i+1)*v for i, v in enumerate(values)) - (n+1)*total) / (n * total)
print(f"{gini:.4f}")
```

---



| Question asks for... | Write to answer.txt as... |
|---|---|
| Percent rounded to hundredths | `12.34%` |
| Percent with no sign specified | just the number: `12.34` |
| Billions to thousandths | `1.234` |
| Millions as integer | `1234` |
| Comma-separated list | `100.5, 200.3, 150.7` |
| Bracket list with commas | `[12.34, 5678, 9012]` |
| U.S. long date | `March 17, 1977` |
| Nominal dollars (no unit specified) | just the number |
| Trailing zero after rounding | drop it: `27.0` → `27` |

**Format rule:** Only include `%` if the question explicitly says "report as a percent value" or gives an example like `(12.34%, not 0.1234)`. When in doubt, write just the number.
