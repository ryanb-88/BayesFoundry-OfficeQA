---
name: python-calculations
description: Pure-Python calculation library for Treasury Bulletin QA tasks. All implementations use only Python stdlib (math, statistics) — no numpy required.
---
# Python Calculation Library

Refer to the main prompt for environment setup (apt-get), HP filter guidance, and fallback strategy. This skill provides the complete compute.py implementation.

## Setup

Before any calculation, try to install numpy/scipy:
```bash
apt-get install -y python3-numpy python3-scipy 2>/dev/null || true
```

If available, prefer numpy/scipy. If not, use the pure-Python implementations below.

## Complete compute.py — Write to /app/compute.py

For any calculation task, write this file first, then import from it:

```python
"""
Pure-Python calculation utilities for Treasury Bulletin QA.
No external dependencies — uses only math and statistics from stdlib.
"""
import math
import statistics


def hp_filter(y, lamb=100):
    """
    Hodrick-Prescott filter. Returns (cycle, trend).
    lamb: 100 annual, 1600 quarterly, 14400 monthly.
    """
    try:
        from statsmodels.tsa.filters.hp_filter import hpfilter
        import numpy as np
        c, t = hpfilter(np.array(y, dtype=float), lamb=lamb)
        return list(c), list(t)
    except ImportError:
        pass
    try:
        import numpy as np
        n = len(y)
        y_arr = np.array(y, dtype=float)
        e = np.eye(n)
        D = np.zeros((n - 2, n))
        for i in range(n - 2):
            D[i, i] = 1; D[i, i + 1] = -2; D[i, i + 2] = 1
        Q = e + lamb * D.T @ D
        trend = np.linalg.solve(Q, y_arr)
        return list(y_arr - trend), list(trend)
    except ImportError:
        pass
    # Pure Python fallback: pentadiagonal solver
    n = len(y)
    y_f = [float(v) for v in y]
    d0 = [0.0] * n
    d1 = [0.0] * n
    d2 = [0.0] * n
    for i in range(n):
        if i == 0 or i == n - 1:
            d0[i] = 1 + lamb * 1
        elif i == 1 or i == n - 2:
            d0[i] = 1 + lamb * 5
        else:
            d0[i] = 1 + lamb * 6
    for i in range(n - 1):
        d1[i] = -2.0 * lamb if (i == 0 or i == n - 2) else -4.0 * lamb
    for i in range(n - 2):
        d2[i] = lamb
    a, b, c, e1, e2, rhs = d2[:], d1[:], d0[:], d1[:], d2[:], y_f[:]
    for i in range(n):
        if i >= 1 and abs(c[i - 1]) >= 1e-30:
            m = b[i - 1] / c[i - 1]
            c[i] -= m * e1[i - 1]
            if i < n - 1 and i - 1 < n - 2:
                e1[i] -= m * e2[i - 1]
            rhs[i] -= m * rhs[i - 1]
            b[i - 1] = 0
        if i >= 2 and abs(c[i - 2]) >= 1e-30:
            m = a[i - 2] / c[i - 2]
            if i - 1 < n - 1 and i - 2 < n - 1:
                b[i - 1] -= m * e1[i - 2]
            if i - 2 < n - 2:
                c[i] -= m * e2[i - 2]
            rhs[i] -= m * rhs[i - 2]
            a[i - 2] = 0
    tau = [0.0] * n
    for i in range(n - 1, -1, -1):
        val = rhs[i]
        if i < n - 1: val -= e1[i] * tau[i + 1]
        if i < n - 2: val -= e2[i] * tau[i + 2]
        tau[i] = val / c[i]
    return [y_f[i] - tau[i] for i in range(n)], tau


def ols_regression(x, y):
    """OLS: y = slope * x + intercept. Returns (slope, intercept, predicted)."""
    n = len(x)
    x_mean, y_mean = sum(x) / n, sum(y) / n
    ss_xy = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    ss_xx = sum((x[i] - x_mean) ** 2 for i in range(n))
    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean
    return slope, intercept, [slope * xi + intercept for xi in x]


def geometric_mean(values):
    n = len(values)
    return math.exp(sum(math.log(v) for v in values) / n)


def coeff_of_variation_pop(values):
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return math.sqrt(var) / abs(mean)


def cagr(start_val, end_val, n_years):
    return (end_val / start_val) ** (1.0 / n_years) - 1


def theil_index(values):
    total, n = sum(values), len(values)
    shares = [v / total for v in values]
    return (1.0 / n) * sum(s * math.log(n * s) for s in shares if s > 0)


def kl_divergence(p, q):
    return sum(pi * math.log(pi / qi) for pi, qi in zip(p, q) if pi > 0 and qi > 0)


def annualized_volatility(values, periods_per_year=12, use_log_returns=False):
    if use_log_returns:
        returns = [math.log(values[i] / values[i - 1]) for i in range(1, len(values))]
    else:
        returns = [values[i] - values[i - 1] for i in range(1, len(values))]
    n = len(returns)
    mean_r = sum(returns) / n
    var = sum((r - mean_r) ** 2 for r in returns) / (n - 1)
    return math.sqrt(var) * math.sqrt(periods_per_year)


def box_cox(x, lam):
    return math.log(x) if abs(lam) < 1e-10 else (x ** lam - 1) / lam


def exponential_smoothing(y, alpha):
    s = [y[0]]
    for i in range(1, len(y)):
        s.append(alpha * y[i] + (1 - alpha) * s[-1])
    return s


def var_historical(returns, confidence=0.95):
    sorted_r = sorted(returns)
    return sorted_r[int(math.floor((1 - confidence) * len(sorted_r)))]


def euclidean_norm(values):
    return math.sqrt(sum(v ** 2 for v in values))


def zipf_exponent(values):
    sorted_vals = sorted(values, reverse=True)
    n = len(sorted_vals)
    log_ranks = [math.log(i + 1) for i in range(n)]
    log_vals = [math.log(v) for v in sorted_vals if v > 0]
    if len(log_vals) < n:
        log_ranks = log_ranks[:len(log_vals)]
    slope, _, _ = ols_regression(log_ranks, log_vals)
    return -slope


def hill_estimator(values, k):
    sorted_vals = sorted(values, reverse=True)
    x_k = sorted_vals[k]
    log_sum = sum(math.log(sorted_vals[i]) - math.log(x_k) for i in range(k))
    return k / log_sum if log_sum != 0 else float('inf')


def winsorized_range(values, pct=0.1):
    sorted_v = sorted(values)
    n = len(sorted_v)
    k = int(round(pct * n))
    return sorted_v[n - k - 1] - sorted_v[k]


def pop_stdev(values):
    n = len(values)
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)
```

## Quick Reference

| Function | Use For | Key Parameters |
|----------|---------|---------------|
| `hp_filter(y, lamb)` | Hodrick-Prescott filter | lamb: 100 annual, 1600 quarterly |
| `ols_regression(x, y)` | Linear regression | Returns (slope, intercept, predicted) |
| `geometric_mean(values)` | Geometric mean | Values must be positive |
| `coeff_of_variation_pop(values)` | CV (population std dev) | |
| `cagr(start, end, years)` | Compound annual growth rate | Returns decimal |
| `theil_index(values)` | Theil index of dispersion | Auto-normalizes |
| `kl_divergence(p, q)` | KL divergence | Discrete distributions |
| `annualized_volatility(vals, periods)` | Annualized volatility | 12 monthly, 252 daily |
| `box_cox(x, lam)` | Box-Cox transform | |
| `exponential_smoothing(y, alpha)` | Single exp smoothing | |
| `var_historical(returns, conf)` | Historical VaR | |
| `euclidean_norm(values)` | L2 norm | |
| `zipf_exponent(values)` | Zipf exponent (OLS) | |
| `hill_estimator(values, k)` | Pareto tail exponent | k = tail cutoff |
| `winsorized_range(values, pct)` | Winsorized range | pct = fraction to trim |
| `pop_stdev(values)` | Population std dev | |
