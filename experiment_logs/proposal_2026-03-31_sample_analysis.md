# Sample-Driven Improvement Analysis (Revised)

**Date:** 2026-03-31
**Author:** Kiro
**Status:** Proposal (no code changes)
**Baseline:** 60% on 5-task local sample (3/5 passing), 38.6% on full 246-question benchmark
**Latest Run:** `run-20260331-111337-947d78` (minimax-m2.5)

---

## 0. Hard Constraints (Competition Environment)

Before proposing improvements, these are the immovable constraints discovered from examining the actual container environment and agent trajectories:

1. **Corpus is pre-baked TXT.** The Docker image (`ghcr.io/sentient-agi/harbor/officeqa-corpus:latest`) ships 697 `.txt` files at `/app/corpus/`. These are the transformed Markdown-with-tables files. We cannot swap in JSON, page-level, or re-parsed versions.
2. **No pip.** `pip3: command not found` inside the container. The agent cannot install numpy, scipy, statsmodels, or any other package. All computation must use Python stdlib only.
3. **No JSON corpus.** The parsed JSON files with bounding boxes, element types, and page IDs are NOT available inside the container.
4. **Agent tools:** `bash`, `grep`, `read`, `write`, `python3` (stdlib only). The agent never invokes MCP tools.
5. **What we control:** `arena.yaml` (model choice, prompt template, skills), `prompts/officeqa_prompt.j2`, `skills/` directory, `install.sh` (can install system packages via `apt-get`).

---

## 1. Failure Analysis — Latest Run

### uid0030 (Chart/Visual — "local maxima on line plots") → FAIL
- **Ground truth:** 18
- **Agent answered:** 9 (after oscillating between 8, 9, 10)
- **Root cause:** Chart data points are not in the TXT corpus. The agent found exhibit titles and axis annotations but had to *guess* the count of local maxima from typical economic patterns. Fundamentally unsolvable from text alone.
- **Failure class:** **Missing data** — corpus doesn't contain the information needed.

### uid0111 (HP Filter — structural balance FY2024) → FAIL
- **Ground truth:** unknown (agent's answer was wrong)
- **Agent answered:** `[-1832816, -377191, 1455625]`
- **Root cause:** The agent correctly extracted FY2010-2024 receipts and outlays. It then spent **21 minutes writing 13 different Python files** trying to implement an HP filter from scratch because numpy/scipy aren't available and pip doesn't exist. Its Gaussian elimination produced numerically unstable results (10^213), and the final Gauss-Jordan approach gave wrong trend values (trend receipts for 2010 = 695,246 vs actual 2,161,745 — the trend should be *close* to the data, not 1/3 of it).
- **Failure class:** **Computation complexity without libraries** — the agent can't reliably implement pentadiagonal matrix solvers in pure Python under time pressure.

### uid0097 (ESF balance) → PASS ✓
### uid0127 (ESF mean) → PASS ✓  
### uid0192 (YoY growth) → PASS ✓

---

## 2. Corpus Quality Issues (Observable but Not Fixable)

These affect accuracy but we cannot change the corpus:

### 2.1 Table Header Mangling
Multi-level headers produce `Unnamed: X_level_Y` artifacts and 500+ character header rows. This wastes tokens and makes column identification hard. **Impact:** 40-60% of questions involve multi-level tables.

### 2.2 No Page Boundaries
No `--- PAGE N ---` markers. Page-reference questions (uid0011, uid0030, uid0035, uid0046) are harder to answer. **Impact:** ~4 questions in first 50.

### 2.3 Chart/Figure Data Loss
Charts are reduced to titles and axis labels. Data points are lost. **Impact:** ~5 chart questions (~2% of benchmark).

### 2.4 Large File Sizes
Files range from 1,789 to 12,241 lines. Broad grep on "Total receipts" returns 3,378 matches across all files.

---

## 3. Question Type Distribution (First 88 of 246)

| Category | ~Count | Current Coverage |
|----------|--------|-----------------|
| Single value lookup | ~25 | Good |
| Multi-file extraction | ~15 | Partial (bash loops) |
| Complex calculation | ~20 | **Weak** (no numpy) |
| Date/text answer | ~8 | Good |
| Chart/visual | ~5 | **None** (data not in corpus) |
| Page-reference | ~4 | **None** (no page markers) |
| External knowledge | ~3 | **None** |
| Multi-step reasoning | ~8 | Partial |

Key calculations required (all must be pure Python stdlib):
- Geometric mean, CAGR, coefficient of variation — **doable** with `math` and `statistics`
- Linear regression / OLS — **doable** with manual formula
- HP filter, Box-Cox, exponential smoothing — **hard** without numpy
- Theil index, KL divergence, Zipf/Pareto exponents — **doable** with `math`
- Value at Risk, Winsorized range — **doable** with sorting
- Annualized volatility — **doable** with `math.log` and `statistics.stdev`

---

## 4. Proposed Improvements (Ranked by Expected Impact)

### Improvement 1: Robust Pure-Python Calculation Library (Expected: +8-15%)
**Effort:** Medium
**Risk:** Low

Since pip is unavailable, the agent must implement every calculation from scratch. The current `python-calculations` skill has snippets but they're incomplete and the agent still wastes time debugging implementations.

**Proposal:** Ship a complete, tested `compute.py` file as part of the skills or prompt that the agent can write to `/app/compute.py` at the start of every task. This file would contain battle-tested pure-Python implementations of:

```python
# HP filter using pentadiagonal banded solver (NOT Gaussian elimination)
def hp_filter(y, lamb=100): ...

# OLS linear regression
def ols_regression(x, y): ...

# Geometric mean
def geometric_mean(values): ...

# Coefficient of variation (population)
def coeff_of_variation(values): ...

# CAGR
def cagr(start, end, years): ...

# Theil index
def theil_index(shares): ...

# KL divergence
def kl_divergence(p, q): ...

# Annualized volatility (Brownian motion)
def annualized_volatility(values, periods_per_year=12): ...

# Box-Cox transform
def box_cox(x, lam): ...

# Exponential smoothing
def exponential_smoothing(y, alpha): ...

# Value at Risk (historical)
def var_historical(returns, confidence=0.95): ...

# Zipf exponent (MLE)
def zipf_exponent(values): ...

# Pareto tail / Hill estimator
def hill_estimator(values, k): ...

# Winsorized range
def winsorized_range(values, pct=0.1): ...
```

The critical piece is the **HP filter**. The agent's failure on uid0111 was entirely due to a buggy pentadiagonal solver. A correct implementation using banded Cholesky decomposition (exploiting the positive-definite symmetric structure of I + λD'D) would be numerically stable without numpy.

**Implementation approach:**
1. Write and test `compute.py` locally with known-correct outputs (validate against `statsmodels.tsa.filters.hp_filter.hpfilter`)
2. Add it to the `skills/python-calculations/` directory
3. Update the prompt to instruct the agent: "At the start of any calculation task, write `/app/compute.py` with the contents from the python-calculations skill, then import from it"

**Why this is the highest priority:** At least 20 of 246 questions require non-trivial numerical computation. The agent currently wastes 5-20 minutes per task trying to implement these from scratch, often getting them wrong. A pre-built library eliminates this entire failure class.

### Improvement 2: Model Upgrade (Expected: +10-20%)
**Effort:** Low (config change in `arena.yaml`)
**Risk:** Medium (cost increase, behavior change)

minimax-m2.5 demonstrated clear weaknesses:
- **Numerical instability blindness:** Didn't recognize when Gaussian elimination produced 10^213 values
- **Decision paralysis:** Oscillated between 8, 9, 10 for uid0030 answer, rewrote answer.txt 4 times
- **Excessive iteration:** Wrote 13 Python files for one HP filter instead of recognizing the approach was failing

Candidates to test:
| Model | Strengths | Cost/task |
|-------|-----------|-----------|
| `anthropic/claude-sonnet-4` | Strong reasoning, tool discipline, recognizes when to stop | ~$0.30 |
| `google/gemini-2.5-pro` | 1M context, strong math, efficient | ~$0.15 |
| `deepseek/deepseek-r1` | Strong math/reasoning, very low cost | ~$0.10 |

A stronger model would:
- Implement the HP filter correctly on the first try (or recognize it needs a different approach)
- Not oscillate on answers
- Follow prompt instructions more reliably (bash loops, early answer writing)
- Better handle the mangled table headers

### Improvement 3: Prompt — Fail-Fast Computation Rules (Expected: +3-5%)
**Effort:** Low
**Risk:** Low

Add explicit rules to prevent the uid0111 failure pattern:

```
## Computation Rules — CRITICAL

1. **No pip.** pip is not available. Do NOT try to install packages.
   Use only Python stdlib: math, statistics, fractions, decimal, itertools, functools.

2. **Write compute.py first.** For ANY calculation task, write /app/compute.py
   with the implementations from the python-calculations skill BEFORE starting.

3. **Fail fast.** If your first Python script produces:
   - Values with 50+ digits → your solver is numerically unstable. Try a different algorithm.
   - Trend values that are <50% or >200% of the input data → your filter is wrong.
   - NaN or Inf → stop and try a simpler approach.
   NEVER spend more than 3 attempts on the same algorithm. Switch approaches.

4. **Sanity check every answer:**
   - Dollar amounts: federal budget ~trillions, agencies ~billions, ESF ~millions-billions
   - Percentages: typically -100% to +1000%
   - Counts: positive integers
   - Trends/filters: should be smoother than but similar magnitude to input data
```

### Improvement 4: Prompt — Table Header Navigation Strategy (Expected: +3-5%)
**Effort:** Low
**Risk:** Low

The mangled headers are a fixed constraint, but we can teach the agent to work around them:

```
## Navigating Mangled Table Headers

The corpus tables have multi-level headers flattened with " > " separators.
Headers often contain "Unnamed: X_level_Y" artifacts. To extract values:

1. **Ignore the header row for column identification.** Instead:
   - Read 5-10 lines ABOVE the table to find the table title (e.g., "Table ESF-1.--Balances as of...")
   - The title tells you what dates/categories the columns represent
2. **Count columns by position.** If the title says "Dec 31, 1989 | Change | Mar 31, 1990",
   then column 1 = Dec 31, column 2 = Change, column 3 = Mar 31.
3. **Use grep to find the row, then split by "|" to get column values:**
   ```bash
   grep "Total capital" file.txt | head -1 | awk -F'|' '{print $2, $3, $4}'
   ```
```

### Improvement 5: Install numpy/scipy via apt-get (Expected: +5-10% IF it works)
**Effort:** Low
**Risk:** Medium (may not be available in the base image)

While `pip` isn't available, `apt-get` IS (the install.sh already uses it). We could try:

```bash
apt-get install -y python3-numpy python3-scipy
```

This installs the system-packaged versions of numpy and scipy. If the base Ubuntu image has these packages available, this would unlock `numpy.linalg.solve`, `scipy.signal`, and `statsmodels` (if packaged).

**Must test first** — the base image is `ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624` which likely has `python3-numpy` in the apt repos. If this works, it's the single highest-impact change.

**Implementation:** Add to `install.sh`:
```bash
apt-get install -y python3-numpy python3-scipy python3-pandas 2>/dev/null || true
```

The `|| true` ensures the agent setup doesn't fail if the packages aren't available.

### Improvement 6: Prompt — Page Estimation Heuristic (Expected: +1-2%)
**Effort:** Low
**Risk:** Low

For page-reference questions, add a heuristic:

```
## Page-Reference Questions

The corpus files don't have page markers. To estimate page numbers:
1. The Table of Contents (near the top of each file) maps section names to page numbers
2. Use the ToC to find which section is on the target page
3. Then grep for that section's content
Example: "What's on page 5?" → Check ToC → page 5 is in "Economic Policy" section → grep for that section
```

### Improvement 7: Chart Question Triage (Expected: +0-1%)
**Effort:** Low
**Risk:** Low

Chart questions are ~2% of the benchmark and fundamentally hard from text. Add:

```
## Chart/Visual Questions — Triage

If the question asks about chart data points (local maxima, specific values from a plot):
1. Search for the exhibit/chart title in the bulletin
2. Check if a DATA TABLE exists near the chart (within 50 lines) — charts often visualize nearby tables
3. If a table exists, extract data and compute the answer
4. If NO table exists, look for narrative text that describes the chart's key features
5. Write your best estimate early — don't spend >5 minutes on chart questions
```

---

## 5. Implementation Priority

| Priority | Improvement | Expected Impact | Effort | Constraint |
|----------|------------|-----------------|--------|-----------|
| **P0** | #5: `apt-get install python3-numpy` | +5-10% | Low | Must test if available |
| **P0** | #1: Pure-Python compute.py library | +8-15% | Medium | Fallback if apt fails |
| **P1** | #3: Fail-fast computation rules | +3-5% | Low | Prompt change only |
| **P1** | #4: Table header navigation | +3-5% | Low | Prompt change only |
| **P2** | #2: Model upgrade | +10-20% | Low | Cost increase |
| **P3** | #6: Page estimation heuristic | +1-2% | Low | Prompt change only |
| **P3** | #7: Chart question triage | +0-1% | Low | Prompt change only |

---

## 6. Recommended Execution Order

### Phase 1: Quick wins (prompt + install.sh only)
1. Test `apt-get install -y python3-numpy python3-scipy` in install.sh
2. Add fail-fast computation rules to prompt (#3)
3. Add table header navigation strategy to prompt (#4)
4. Add page estimation and chart triage to prompt (#6, #7)

### Phase 2: Compute library
5. If apt numpy works → update python-calculations skill to use numpy implementations
6. If apt numpy fails → build and test pure-Python `compute.py` with correct HP filter, OLS, etc.
7. Update prompt to instruct agent to write compute.py at task start

### Phase 3: Model evaluation
8. Run the 20-task local benchmark with current model + Phase 1-2 changes
9. Run same benchmark with claude-sonnet-4 and gemini-2.5-pro
10. Pick best model based on accuracy × cost tradeoff

**Estimated combined impact of Phase 1-2:** +14-25% (from 38.6% to ~53-64%)
**Estimated combined impact of all phases:** +25-45% (from 38.6% to ~64-84%)

---

## 7. Key Insight

The single biggest lever is **reliable numerical computation**. 20+ of 246 questions require non-trivial math (HP filter, OLS, geometric mean, Theil index, etc.). The agent currently fails these not because it can't find the data, but because it can't compute the answer correctly without numpy. Solving this — either via apt-get or a pre-built pure-Python library — would flip an entire category of questions from FAIL to PASS.
