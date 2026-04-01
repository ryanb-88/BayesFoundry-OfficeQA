---
name: python-calculations
description: Complete pure-Python calculation library for Treasury Bulletin QA tasks. Includes HP filter, OLS regression, geometric mean, Theil index, volatility, CAGR, Euclidean norm, KL divergence, Box-Cox, VaR, Zipf/Hill estimators, and more. All implementations use only Python stdlib (math, statistics) — no numpy required.
---
# Python Calculation Library

## IMPORTANT: Environment Setup

Before ANY calculation, try to install numpy/scipy:
```bash
apt-get install -y python3-numpy python3-scipy 2>/dev/null || true
```

Then check what's available:
```python
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from statsmodels.tsa.filters.hp_filter import hpfilter
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
```

If numpy/statsmodels are available, use them. If not, use the pure-Python implementations below.

---

## Complete compute.py — Write This to /app/compute.py

For any calculation task, write this file first, then import from it:

```python
"""
Pure-Python calculation utilities for Treasury Bulletin QA.
No external dependencies — uses only math and statistics from stdlib.
"""
import math
import statistics


# ============================================================
# HP Filter (Hodrick-Prescott) — Pure Python
# ============================================================
#
# CRITICAL: The pure-Python fallback uses FULL dense Gaussian
# elimination with partial pivoting. Do NOT attempt to optimize
# with banded solvers — they are numerically fragile and the
# boundary conditions are easy to get wrong. For n < 1000 (all
# Treasury QA tasks), the dense O(n^3) solver is fast enough
# and guaranteed correct.
# ============================================================

def hp_filter(y, lamb=100):
    """
    Hodrick-Prescott filter. Returns (cycle, trend).
    lamb: smoothing parameter (100 for annual, 1600 for quarterly, 14400 for monthly)
    """
    # Try statsmodels first (best)
    try:
        from statsmodels.tsa.filters.hp_filter import hpfilter
        import numpy as np
        c, t = hpfilter(np.array(y, dtype=float), lamb=lamb)
        return list(c), list(t)
    except ImportError:
        pass

    # Try numpy (good)
    try:
        import numpy as np
        n = len(y)
        y_arr = np.array(y, dtype=float)
        I = np.eye(n)
        D = np.zeros((n - 2, n))
        for i in range(n - 2):
            D[i, i] = 1
            D[i, i + 1] = -2
            D[i, i + 2] = 1
        Q = I + lamb * D.T @ D
        trend = np.linalg.solve(Q, y_arr)
        cycle = y_arr - trend
        return list(cycle), list(trend)
    except ImportError:
        pass

    # Pure Python fallback: dense Gaussian elimination
    # Solves (I + lamb * D'D) * tau = y where D is the second-difference operator
    n = len(y)
    y_f = [float(v) for v in y]

    # Build Q = I + lamb * D'D as a dense n x n matrix
    Q = [[0.0] * n for _ in range(n)]
    for i in range(n):
        Q[i][i] = 1.0
    for k in range(n - 2):
        # D[k,:] has 1 at k, -2 at k+1, 1 at k+2
        for a, va in zip([k, k + 1, k + 2], [1.0, -2.0, 1.0]):
            for b, vb in zip([k, k + 1, k + 2], [1.0, -2.0, 1.0]):
                Q[a][b] += lamb * va * vb

    # Augmented matrix [Q | y]
    aug = [Q[i][:] + [y_f[i]] for i in range(n)]

    # Gaussian elimination with partial pivoting
    for col in range(n):
        # Find pivot row
        max_val = abs(aug[col][col])
        max_row = col
        for row in range(col + 1, n):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                max_row = row
        if max_row != col:
            aug[col], aug[max_row] = aug[max_row], aug[col]

        pivot = aug[col][col]
        for row in range(col + 1, n):
            if abs(aug[row][col]) < 1e-30:
                continue
            factor = aug[row][col] / pivot
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]

    # Back substitution
    tau = [0.0] * n
    for i in range(n - 1, -1, -1):
        val = aug[i][n]
        for j in range(i + 1, n):
            val -= aug[i][j] * tau[j]
        tau[i] = val / aug[i][i]

    cycle = [y_f[i] - tau[i] for i in range(n)]
    return cycle, tau


# ============================================================
# OLS Linear Regression
# ============================================================

def ols_regression(x, y):
    """
    Ordinary least squares: y = slope * x + intercept.
    Returns (slope, intercept, predicted_values).
    """
    n = len(x)
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    ss_xy = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    ss_xx = sum((x[i] - x_mean) ** 2 for i in range(n))
    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean
    predicted = [slope * xi + intercept for xi in x]
    return slope, intercept, predicted


# ============================================================
# Geometric Mean
# ============================================================

def geometric_mean(values):
    """Geometric mean of positive values."""
    n = len(values)
    log_sum = sum(math.log(v) for v in values)
    return math.exp(log_sum / n)


# ============================================================
# Coefficient of Variation (population std dev)
# ============================================================

def coeff_of_variation_pop(values):
    """CV using population standard deviation."""
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return math.sqrt(var) / abs(mean)


# ============================================================
# CAGR
# ============================================================

def cagr(start_val, end_val, n_years):
    """Compound annual growth rate."""
    return (end_val / start_val) ** (1.0 / n_years) - 1


# ============================================================
# Theil Index
# ============================================================

def theil_index(values):
    """Theil index of dispersion from raw values."""
    total = sum(values)
    n = len(values)
    shares = [v / total for v in values]
    return (1.0 / n) * sum(s * math.log(n * s) for s in shares if s > 0)


# ============================================================
# KL Divergence
# ============================================================

def kl_divergence(p, q):
    """KL divergence D(P || Q) for discrete distributions."""
    return sum(pi * math.log(pi / qi) for pi, qi in zip(p, q) if pi > 0 and qi > 0)


# ============================================================
# Annualized Volatility
# ============================================================

def annualized_volatility(values, periods_per_year=12, use_log_returns=False):
    """Annualized volatility from a price/rate series."""
    if use_log_returns:
        returns = [math.log(values[i] / values[i - 1]) for i in range(1, len(values))]
    else:
        returns = [values[i] - values[i - 1] for i in range(1, len(values))]
    n = len(returns)
    mean_r = sum(returns) / n
    var = sum((r - mean_r) ** 2 for r in returns) / (n - 1)
    return math.sqrt(var) * math.sqrt(periods_per_year)


# ============================================================
# Box-Cox Transform
# ============================================================

def box_cox(x, lam):
    """Box-Cox transformation of a single value."""
    if abs(lam) < 1e-10:
        return math.log(x)
    return (x ** lam - 1) / lam


# ============================================================
# Exponential Smoothing
# ============================================================

def exponential_smoothing(y, alpha):
    """Single exponential smoothing. Returns smoothed series."""
    s = [y[0]]
    for i in range(1, len(y)):
        s.append(alpha * y[i] + (1 - alpha) * s[-1])
    return s


# ============================================================
# Value at Risk (Historical)
# ============================================================

def var_historical(returns, confidence=0.95):
    """Historical VaR at given confidence level using nearest-rank."""
    sorted_r = sorted(returns)
    idx = int(math.floor((1 - confidence) * len(sorted_r)))
    return sorted_r[idx]


# ============================================================
# Euclidean Norm
# ============================================================

def euclidean_norm(values):
    """L2 norm of a vector."""
    return math.sqrt(sum(v ** 2 for v in values))


# ============================================================
# Zipf Exponent (MLE)
# ============================================================

def zipf_exponent(values):
    """Estimate Zipf exponent via OLS on log-log rank-size."""
    sorted_vals = sorted(values, reverse=True)
    n = len(sorted_vals)
    log_ranks = [math.log(i + 1) for i in range(n)]
    log_vals = [math.log(v) for v in sorted_vals if v > 0]
    if len(log_vals) < n:
        log_ranks = log_ranks[:len(log_vals)]
    slope, _, _ = ols_regression(log_ranks, log_vals)
    return -slope


# ============================================================
# Hill Estimator (Pareto Tail)
# ============================================================

def hill_estimator(values, k):
    """Hill estimator for Pareto tail exponent using top k values."""
    sorted_vals = sorted(values, reverse=True)
    x_k = sorted_vals[k]  # k-th order statistic (0-indexed: k is the (k+1)-th largest)
    log_sum = sum(math.log(sorted_vals[i]) - math.log(x_k) for i in range(k))
    return k / log_sum if log_sum != 0 else float('inf')


# ============================================================
# Winsorized Range
# ============================================================

def winsorized_range(values, pct=0.1):
    """Winsorized range: range after trimming pct from each tail."""
    sorted_v = sorted(values)
    n = len(sorted_v)
    k = int(round(pct * n))
    # Winsorize: replace bottom k with k-th value, top k with (n-k-1)-th value
    low = sorted_v[k]
    high = sorted_v[n - k - 1]
    return high - low


# ============================================================
# Population Standard Deviation
# ============================================================

def pop_stdev(values):
    """Population standard deviation."""
    n = len(values)
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)
```

## Usage

At the start of any calculation task:
1. Write the above code to `/app/compute.py`
2. Then in your calculation script: `from compute import hp_filter, ols_regression, ...`

## Quick Reference

| Calculation | Function | Key Parameters |
|------------|----------|---------------|
| HP filter | `hp_filter(y, lamb=100)` | lamb: 100 annual, 1600 quarterly |
| Linear regression | `ols_regression(x, y)` | Returns (slope, intercept, predicted) |
| Geometric mean | `geometric_mean(values)` | Values must be positive |
| CV (population) | `coeff_of_variation_pop(values)` | Uses population std dev |
| CAGR | `cagr(start, end, years)` | Returns decimal (multiply by 100 for %) |
| Theil index | `theil_index(values)` | Raw values, auto-normalizes |
| KL divergence | `kl_divergence(p, q)` | Discrete probability distributions |
| Volatility | `annualized_volatility(vals, periods)` | periods_per_year: 12 monthly, 252 daily |
| Box-Cox | `box_cox(x, lam)` | Single value transform |
| Exp smoothing | `exponential_smoothing(y, alpha)` | Returns smoothed series |
| VaR | `var_historical(returns, 0.95)` | Returns loss at confidence level |
| Euclidean norm | `euclidean_norm(values)` | L2 norm |
| Zipf exponent | `zipf_exponent(values)` | Log-log OLS estimate |
| Hill estimator | `hill_estimator(values, k)` | Pareto tail, k = tail cutoff |
| Winsorized range | `winsorized_range(values, 0.1)` | pct = fraction to trim each side |
| Pop std dev | `pop_stdev(values)` | Population (not sample) |
