# Statistical Operations — Python and mcpcalc Patterns

---

## Using mcpcalc for Statistical Operations — TRY THIS FIRST

Before writing any Python for Patterns 14–26, try mcpcalc. It has 300+ calculators covering most stats operations:

```
# Step 1: find the right calculator
list_calculators(category="statistics")

# Step 2: check inputs
get_calculator_schema(slug="standard-deviation")   # or whatever slug was returned

# Step 3: compute
calculate(slug="standard-deviation", inputs={"values": [1.2, 3.4, 5.6, ...]})
```

**Common mcpcalc slugs to try:**
| Operation | Try slug |
|-----------|----------|
| Std dev (pop or sample) | `standard-deviation`, `descriptive-statistics` |
| Correlation / R² | `pearson-correlation`, `linear-regression` |
| OLS regression | `linear-regression`, `simple-linear-regression` |
| Moving average | `moving-average` |
| Geometric mean | `geometric-mean` |
| Percentile | `percentile`, `quantile` |
| Median | `median`, `descriptive-statistics` |
| Z-score | `z-score` |
| Gini coefficient | `gini-coefficient` |
| Skewness/Kurtosis | `skewness`, `kurtosis`, `descriptive-statistics` |

**For complex multi-step math**, use CAS session:
```
create_session(calculator="cas")
push_session_action(expression="std([1.2, 3.4, 5.6])")
```

**Fall back to Python** (patterns below) only if mcpcalc returns an error or doesn't have the calculator.

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
