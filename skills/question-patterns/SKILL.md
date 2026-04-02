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
