# Reflection — OfficeQA Hackathon Progress
**Date:** March 21, 2026

---

## The Task

**OfficeQA** is a benchmark of **246 financial Q&A questions** grounded in U.S. Treasury Bulletin documents spanning 1939–2025. Questions range from simple table lookups to complex multi-step reasoning (percent change, geometric mean, linear regression, Euclidean norms). Scoring uses **1% fuzzy numeric tolerance**.

The corpus is **697 pre-parsed markdown files** (~100-150K tokens each) containing tables, narratives, and appendices from monthly Treasury Bulletins. The agent runs inside a Docker container with corpus at `/app/corpus/`.

**Budget:** $100 OpenRouter API credit.

---

## What the Databricks Blog Said Would Fail (and Why)

The [OfficeQA benchmark paper](https://www.databricks.com/blog/introducing-officeqa-benchmark-end-to-end-grounded-reasoning) identified these as the primary failure modes:

| Failure Mode | Their Baseline | Notes |
|---|---|---|
| **PDF parsing** | ~50-60% start | Raw PDFs with complex layouts, multi-column tables, headers |
| **Providing a parsing tool** | ~70% ceiling | Their best result after adding a structured parser |
| **Visual/chart questions** | ~0% | Line plots, bar charts — no image representation in text |
| **Multi-step reasoning** | Low | Requires chaining table lookup → arithmetic → format |
| **Data revision** | Low | Earlier bulletins contain stale data; later bulletins revise figures |
| **External knowledge gaps** | Low | Questions requiring facts not in the corpus (gold bloc, WW2 dates) |

**Key insight we acted on:** Since the Sentient Arena provides **pre-parsed markdown** (not raw PDFs), we effectively start at their ~70% ceiling — the hardest problem (parsing) is already solved for us.

---

## What We Did to Tackle Each Failure

### 1. Corpus Navigation & Token Efficiency
**Problem:** Bulletin files are 100-150K tokens each. Reading them naively burns budget and hits context limits.

**Solution:**
- Built `treasury_mcp_server.py` with 6 targeted tools: `extract_tables`, `search_corpus`, `find_latest_value`, `batch_extract`, `list_bulletins`, `read_bulletin`
- Made the server **dual-mode**: acts as MCP server when invoked by opencode, CLI tool when called via bash (`python3 /app/skills/mcp_servers/treasury_mcp_server.py extract_tables 1977 3 "T-bill"`)
- Prompt instructs agent to call bash fallbacks if MCP isn't available

**Status:** CLI fallback works. MCP server protocol is correct (verified locally) but opencode 1.2.27's `run` (one-shot) mode doesn't register external MCP tools — known limitation, workaround in place.

---

### 2. Multi-Step Reasoning Errors
**Problem:** Agent confuses formulas (percent change vs percent difference), gets units wrong, rounds too early.

**Solution — `skills/04_question_patterns.md`:**
Explicit Python code templates for every operation type:
- Percent change: `|B-A|/A × 100` (base denominator)
- Percent difference: `|A-B|/((A+B)/2) × 100` (average denominator — different!)
- Geometric mean, linear regression, Euclidean norm, CAGR
- Output formatting rules (trailing zeros, `%` only when asked)

**Solution — Prompt formula disambiguation block:**
```
⚠️ "percent change" ≠ "percent difference" — always check which the question asks for
```

**Result:** Zero formula errors observed across 19 sample tasks.

---

### 3. Data Revision (Stale Values)
**Problem:** Treasury Bulletins frequently revise prior figures. A search returning the 1970 bulletin might have a value that was corrected in the 1972 bulletin.

**Solution:** `find_latest_value` tool (both MCP and CLI) searches bulletins **newest-first**, returning the most recently published version of a value.

**Status:** Implemented. Not yet proven to have fixed a specific failure — worth monitoring in full run.

---

### 4. External Knowledge Gaps
**Problem:** ~13% of questions require facts not in the corpus (gold bloc membership, WW2 dates, fiscal year calendar changes).

**Solution — `skills/05_external_knowledge.md`:**
- Gold bloc countries in 1935: France, Switzerland, Netherlands, Belgium, **Italy**, Poland, Luxembourg
- Italy left gold standard: **October 1935** (not 1934 — model training data is wrong on this)
- WW2 dates, U.S. presidents, fiscal year transition (pre-1977: FY ends June 30, post-1976: ends Sep 30)
- ESF balance sheet structure, financial glossary

**Proven fix:** uid0199 (gold bloc question) failed on first attempt because the agent said "Italy left in October 1934" — wrong. Updated skill to explicitly override training data with the correct date. uid0199 now passes.

---

### 5. Fiscal Year Confusion
**Problem:** Many questions ask for "FY1953 total" but the agent sums wrong months or uses the wrong FY boundary.

**Solution — `skills/02_fiscal_year_and_dates.md`:**
- Pre-1977: FY ends **June 30** (FY1953 = July 1952 – June 1953)
- Post-1976: FY ends **September 30**
- Transition quarter: July–September 1976 (3-month gap)

---

### 6. Visual/Chart Questions
**Problem:** Some questions ask about line plots ("how many local maxima?") — the corpus has no images.

**Solution:** None possible. The markdown files don't contain chart images. These questions are unfixable.

**Known failure:** uid0030 — "How many local maxima on the line plots on page 5 of September 1990 bulletin?" → agent guesses, will likely always fail.

---

### 7. MCP Server Investigation (Deep Dive)

We spent significant time debugging why the MCP server wasn't registering:

| Attempt | Finding |
|---|---|
| `bash -c "pip install mcp ... ; python3 server.py"` | pip stdout leaked into JSON-RPC stream; silent parse failure |
| Redirect pip output: `>/dev/null 2>&1` | Startup still too slow; MCP handshake timed out |
| Pure stdlib JSON-RPC server (no pip) | Protocol correct, tested locally — opencode still ignores it |
| `uv run --with mcp python3 server.py` | Fast, clean — still not registered |
| Direct `python3 server.py` | Still not registered |

**Root cause confirmed:** opencode 1.2.27 in `run` (one-shot) mode does not wait for MCP server initialization before sending the first message to the model. Tools never appear in the model's tool list. This is a version-specific limitation.

**Workaround:** Dual-mode server callable via bash. Prompt shows both call styles side-by-side.

---

## What We've Accomplished

### Sample Task Score: **18/19 = 94.7%**

| Category | Result |
|---|---|
| Easy tasks (133 total) | 7/7 tested → 100% |
| Hard tasks (113 total) | 11/12 tested → 91.7% |
| Overall sample | 18/19 → 94.7% |

### Cost Analysis (so far)
- Avg cost per task: ~$0.28 (Claude Sonnet 4.5)
- Avg cost per task: ~$0.12 (GLM-5 — still being validated)
- Total budget spent in testing: ~$8-10
- Projected full run (Claude): ~$70 — within $100 budget
- Projected full run (GLM-5): ~$30 — very safe

### Infrastructure Built
- `arena.yaml` — complete harness config with MCP + prompt
- `prompts/officeqa_prompt.j2` — battle-tested Jinja2 template
- `skills/01-05` — 5 reference files covering every known edge case
- `skills/mcp_servers/treasury_mcp_server.py` — dual-mode corpus server
- `analyze_run.py` — trajectory parsing and cost analysis tool
- `LEARNINGS.md` — engineering log
- GitHub: `Shradha` branch at `ryanb-88/BayesFoundry-OfficeQA`

---

## What's Remaining

### Known Failures
| Task | Type | Fixable? | Root Cause |
|------|------|----------|------------|
| uid0030 | Visual/chart | ❌ No | "Count local maxima on line plot" — no images in corpus |
| uid0246 | Table disambiguation | 🔶 Maybe | Agent read maturity schedule instead of outstanding totals table |

### Open Questions
1. **GLM-5 validation** — passed 2/2 tasks. Need 5-10 more hard tasks to confirm it's reliable enough for full submission.
2. **Full run score estimate** — 94.7% on 19 samples. The full 246 may contain more visual questions and edge cases not seen in samples.
3. **uid0246 fix** — the T-bill "outstanding vs maturing" table disambiguation is an unsolved search keyword problem. Might need a hint in the skills about PDO table types.

---

## Next Steps

### Immediate (before full submission)
1. **Validate GLM-5 on 5+ more hard tasks** — confirm accuracy holds before committing to it for the full run
2. **Investigate uid0246** — look at the February 1970 bulletin to understand which table has "outstanding as of Jan 31" vs "maturing on Jan 31" and add a disambiguation hint to skills
3. **Add skills hint for PDO tables** — "outstanding as of [date]" → look for a snapshot table, not a maturity schedule

### For Final Submission
4. **Decide model** — GLM-5 (cheap, ~$30) vs Claude Sonnet 4.5 (accurate, ~$70). If GLM-5 has any hard-task failures, revert to Claude for submission.
5. **Run full 246 tasks** — use `arena submit` or `arena test` on the full benchmark
6. **Monitor budget** — stop if approaching $90 to leave buffer

### Stretch Goals (if time/budget allows)
7. **Enable web search** — add Brave Search MCP for the ~13% of questions needing external knowledge (need `BRAVE_API_KEY`)
8. **Investigate MCP fix** — try opencode in interactive mode or a different version; if MCP tools register, token costs could drop 10-30x for targeted lookups
9. **uid0030-type questions** — explore if there's any way to infer chart data from surrounding text (unlikely but worth one attempt)

---

## Key Lessons

1. **Pre-parsed corpus is the biggest advantage** — we start at ~70% for free. The Databricks team had to build parsing; we just had to navigate.
2. **Prompt > model for structured tasks** — clear formula disambiguation and strategy steps matter more than model size.
3. **MCP in one-shot mode is unreliable** — design bash fallbacks from day one when using opencode `run`.
4. **Skills files work** — the Italy date fix on uid0199 shows that explicit override of training data is effective.
5. **Cache is your best friend** — 81-96% cache hit rate on Claude means the actual incremental cost per token is very low.
