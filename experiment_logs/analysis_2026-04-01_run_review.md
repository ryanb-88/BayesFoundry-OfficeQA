# Run Review: run-20260331-152832-141106

**Date:** 2026-04-01
**Run:** `run-20260331-152832-141106`
**Score:** 85% (17/20) — up from 60% (3/5) on previous run
**Model:** minimax-m2.5
**Avg latency:** 635s | **Avg cost:** $0.12/task | **Total cost:** $2.30

---

## Summary

The sample-driven improvements (apt numpy, fail-fast computation, table nav, chart triage) produced a massive jump. uid0111 (HP filter) now passes — the apt-get numpy strategy worked. 14 previously-untested tasks all passed on first attempt. Only 3 failures remain.

## Failures

### uid0030 — Chart/Visual (Expected: 18, Agent answered: 11)
**Status:** Known unsolvable from text corpus. Agent improved from 9 → 11 (closer but still wrong). The triage guidance helped — agent spent only 411s (down from 840s) and didn't oscillate as much. But without actual chart data points, this remains a guess.

**Fixability:** Low. Would require either (a) pre-extracting chart data from PDFs via vision model and embedding in the corpus, or (b) accepting the loss. This is 1 question out of 246 (0.4%).

**Recommendation:** Accept the loss. Not worth the engineering effort for 0.4% of the benchmark.

### uid0220 — Pre-1940s Expenditures (Expected: 27, Agent answered: 31.3)
**Status:** Agent extracted the correct values (Feb 1938: 528M, Jan 1939: 693M) but used the wrong percent difference formula.

**Root cause:** The question asks for "absolute percent difference" which is ambiguous. The agent computed `|a-b|/a × 100 = 31.25% → 31.3%`. The expected answer (27) matches the **symmetric percent difference** formula: `|a-b| / ((a+b)/2) × 100 = 165/610.5 × 100 = 27.0%`.

**Cross-reference with corpus:** Verified in `treasury_bulletin_1939_02.txt` lines 243-254. The agent's data extraction was correct. The error is purely in the formula choice.

**Fixability:** Medium. This is a question-interpretation issue. The phrase "absolute percent difference" is genuinely ambiguous in finance/economics. Options:
1. Add guidance to the prompt about percent difference formulas — when a question says "percent difference" (not "percent change"), use the symmetric formula: `|a-b| / ((a+b)/2) × 100`
2. Add a worked example showing the symmetric formula
3. Add to the self-consistency check: "If computing percent difference, try both `|a-b|/a` and `|a-b|/avg(a,b)` — if the question says 'percent difference' (not 'percent change'), prefer the symmetric formula"

**Recommendation:** Add prompt guidance distinguishing "percent change" (uses base value as denominator) from "percent difference" (uses average as denominator).

### uid0246 — Euclidean Norm of Treasury Bill Changes (Expected: 44605.38, Agent answered: 10782.79)
**Status:** Agent extracted wrong values from a complex multi-category Treasury bill table. The question requires finding:
1. Regular weekly + annual Treasury bills outstanding as of Jan 31, 1970 and Jan 31, 1975
2. Tax anticipation Treasury bills outstanding on those same dates
3. Absolute change for each category
4. Euclidean norm of the two changes

**Root cause:** The agent struggled with the complex table structure in the FD-1 and PDO tables. The Treasury bill data is split across multiple table types (FD-1 summary, PDO-2 offerings, ownership tables) with different granularity. The agent appears to have extracted values from the wrong table or wrong row, getting ~10K instead of ~44K for the norm.

**Cross-reference with corpus:** The source files are `treasury_bulletin_1970_03.txt` and `treasury_bulletin_1975_03.txt`. The FD-1 table at line 1365 of the 1970 file shows total debt by category but doesn't break out Treasury bills by regular vs tax anticipation. That breakdown is in the PDO-2 table (line 1931+) which has a complex multi-level header structure with the `Unnamed:` artifacts.

**Fixability:** Medium-Hard. This is a data extraction accuracy issue on complex tables. The agent needs to:
- Correctly identify which table has the regular weekly vs tax anticipation breakdown
- Navigate the mangled headers to extract the right columns
- Handle the fact that the data may be in different table formats across the two bulletins (1970 vs 1975)

**Recommendation:** 
1. Add a worked example for multi-category extraction from complex tables (e.g., "find X and Y separately in the same table, then compute")
2. Strengthen the table navigation guidance with an example of counting pipe-delimited columns
3. Consider adding a "Treasury bill categories" entry to the Topic-to-Section Mapping

---

## Improvements to Implement

### 1. Percent Difference Formula Guidance (fixes uid0220)
Add to prompt:

```
## Percent Change vs Percent Difference

- **"Percent change"** from A to B: `(B - A) / A × 100` (base is the starting value)
- **"Percent difference"** between A and B: `|A - B| / ((A + B) / 2) × 100` (base is the average)
- **"Absolute percent change"**: `|B - A| / A × 100`

When the question says "percent difference" (not "change"), use the symmetric/average formula.
```

### 2. Multi-Category Table Extraction Example (helps uid0246 class)
Add a worked example showing extraction of multiple categories from the same table, with column counting.

### 3. Topic Mapping Update
Add Treasury bill subcategories to the Topic-to-Section Mapping:
```
| Treasury bill breakdown | `Regular weekly`, `Tax anticipation`, `PDO-2`, `Offerings of Treasury Bills` | PDO-2 |
```

---

## Performance Comparison

| Metric | Previous (run-20260331-111337) | Current (run-20260331-152832) | Delta |
|--------|-------------------------------|-------------------------------|-------|
| Score | 60% (3/5) | 85% (17/20) | +25% |
| uid0111 (HP filter) | FAIL | PASS | ✅ Fixed |
| uid0030 (chart) | FAIL | FAIL | Known unsolvable |
| uid0220 (expenditures) | Not tested | FAIL | Formula issue |
| uid0246 (Euclidean norm) | Not tested | FAIL | Extraction issue |
| Avg latency | 678s | 635s | -43s |
| Avg cost | $0.12 | $0.12 | Same |

## Key Wins

- **uid0111 now passes** — the apt-get numpy strategy worked perfectly
- **14 new tasks passed** on first attempt (uid0004, uid0023, uid0033, uid0041, uid0048, uid0057, uid0136, uid0167, uid0194, uid0199, uid0217, uid0230, uid0241)
- **uid0057 passes** — the multi-file bash loop strategy works (this was a known failure before)
- **uid0136 passes** — geometric mean calculation works
- **uid0230 passes** — annualized volatility calculation works
- **Latency improved** slightly despite more tasks

## Next Steps

1. Implement percent difference formula guidance (low effort, fixes uid0220)
2. Add multi-category extraction example (medium effort, may help uid0246)
3. Consider model upgrade test — with 85% baseline, a stronger model might push to 90%+
4. Submit to full 246-question benchmark to see real-world score
