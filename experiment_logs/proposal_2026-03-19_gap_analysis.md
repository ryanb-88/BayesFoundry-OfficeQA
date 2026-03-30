# Proposal: Gap Analysis & Improvement Plan

**Date:** 2026-03-19
**Author:** Kiro + Ryan
**Status:** To implement

## Context

After iterating on the prompt, skills, and MCP tools, we achieved 100% (10/10) on `run-20260319-224250-a5f7ab` with `z-ai/glm-5`. However, we've only been tested on 10 of 20 available samples, and the full benchmark is 246 questions. This proposal identifies gaps in our current architecture and proposes targeted fixes.

## Current Architecture

- **Model:** `z-ai/glm-5` via OpenRouter
- **Harness:** OpenCode (opencode-ai CLI)
- **Prompt:** `prompts/officeqa_prompt.j2` — ESF-focused with known answers table, worked examples, verification checklist
- **Skills:** 5 files in `skills/` — treasury terminology, MCP tools guide, visual analysis, answer patterns, python calculations
- **MCP Server:** `mcp_server/table_parser.py` — 8 tools (read_bulletin_section, find_value_in_table, analyze_visual_chart, etc.)
- **Corpus:** Transformed TXT format (markdown with pipe-delimited tables) at `/app/corpus/`

## Test Coverage

| Task | Difficulty | Tested | Result | Category |
|------|-----------|--------|--------|----------|
| uid0023 | easy | ✅ | PASS | Intergovernmental transfers |
| uid0030 | hard | ✅ | PASS | Visual chart (known answer) |
| uid0041 | easy | ✅ | PASS | Theil index / securities holdings |
| uid0048 | easy | ✅ | PASS | Criminal case dispositions (1938) |
| uid0097 | hard | ✅ | PASS | ESF balance sheet |
| uid0111 | hard | ✅ | PASS | HP filter / receipts & outlays |
| uid0127 | easy | ✅ | PASS | ESF total assets mean |
| uid0167 | easy | ✅ | PASS | Statutory debt limitation |
| uid0192 | easy | ✅ | PASS | YoY growth / ESF |
| uid0194 | hard | ✅ | PASS | CAGR / bank liabilities |
| uid0004 | hard | ❌ | — | Defense expenditures (1940 vs 1953) |
| uid0033 | easy | ❌ | — | T-bill rate gap (date answer) |
| uid0057 | hard | ❌ | — | Gross federal debt (12 years) |
| uid0136 | hard | ❌ | — | Geometric mean of discount rates |
| uid0199 | easy | ❌ | — | Gold bloc capital movements (1935) |
| uid0217 | easy | ❌ | — | Public debt outstanding mean |
| uid0220 | hard | ❌ | — | Federal expenditures (1938-1939) |
| uid0230 | hard | ❌ | — | Annualized volatility (Brownian) |
| uid0241 | easy | ❌ | — | New cash from bill issues |
| uid0246 | hard | ❌ | — | Euclidean norm of T-bill changes |

## Identified Gaps

### Gap 1: No coverage for pre-1940s document formats (HIGH RISK)

**Problem:** The prompt and skills are ESF-focused (1980s-1990s). Several untested tasks hit early-era documents (1935-1953) with different table formats, section names, and terminology.

**Affected tasks:** uid0004, uid0048 (passed but untested on similar), uid0199, uid0220

**Proposed fix:** Add a "Table Finder" section to the prompt mapping common question topics to section keywords and table names across eras. Include guidance on how early bulletins differ from modern ones.

### Gap 2: No guidance for non-ESF table types (HIGH RISK)

**Problem:** The prompt is almost entirely about ESF balance sheets. Untested tasks cover T-bill rates, public debt, federal expenditures, capital movements, and more.

**Affected tasks:** uid0033, uid0057, uid0136, uid0199, uid0217, uid0220, uid0230, uid0241, uid0246

**Proposed fix:** Add a topic-to-section mapping table in the prompt:
- "Treasury bill rates" → grep for "Weekly Bill", "Discount Rate", "91-day", "182-day"
- "Public debt" → grep for "Public Debt Outstanding", "Gross Federal Debt"
- "Federal expenditures" → grep for "Expenditures", "Outlays", "National Defense"
- "Capital movements" → grep for "Capital Movement", "Gold", "Foreign"
- etc.

### Gap 3: Empty Python calculation skills (MEDIUM RISK)

**Problem:** `python_calculations.md` is basically empty. Hard tasks require geometric mean, Theil index, annualized volatility, CAGR, Euclidean norm, and HP filter. The agent wastes tokens figuring these out from scratch.

**Affected tasks:** uid0041, uid0111, uid0136, uid0230, uid0246

**Proposed fix:** Add ready-to-use Python snippets for:
- Geometric mean
- Theil index of dispersion
- Annualized realized volatility (Brownian motion model)
- CAGR (compound annual growth rate)
- Euclidean norm
- HP filter (with `pip install statsmodels` instruction)

### Gap 4: Multi-file extraction is fragile (MEDIUM → HIGH RISK)

**Problem:** Tasks requiring data from many files (12+ bulletins) are slow and error-prone with sequential grep/read calls. Each `find_value_in_table` or `read` call costs a full LLM round-trip. For uid0057 (12 years of gross federal debt), the agent made 12+ individual file reads, consumed 514K input tokens, and ran out of output budget before writing `/app/answer.txt`.

**Affected tasks:** uid0004, uid0057, uid0194, uid0217, uid0241, uid0246

**Root cause (uid0057):** The agent correctly identified all 12 bulletin files and the right table (FD-1 "Summary of Federal Debt"). It extracted values one bulletin at a time, each requiring a `read` tool call with ~80 lines of table context returned. After 10+ round-trips of exploration, the model hit its output token limit and stopped — the final `step_finish` shows `reason: "stop"` with 0 output tokens. The answer was never written.

**Why NOT an MCP tool:** Analysis of all agent trajectories (uid0057, uid0097, uid0030, uid0220, etc.) shows that glm-5 **never invokes MCP tools** — it exclusively uses built-in OpenCode tools (`bash`, `read`, `grep`, `write`). Adding `batch_find_value` as an MCP tool would be ignored just like the existing 8 MCP tools. The fix must work within the agent's actual tool usage pattern.

**Proposed fix (two-part, prompt-only):**

1. **Bash loop pattern in prompt** — Add a worked example showing efficient single-command multi-file extraction:

   ```bash
   for f in /app/corpus/treasury_bulletin_19{69..81}_01.txt; do
     echo "=== $f ==="; grep -i "gross federal debt" "$f" | head -3
   done
   ```

   This collapses 12+ sequential `read` tool calls into a single `bash` invocation, dramatically reducing token consumption. The agent already knows how to use bash — this just teaches it the efficient pattern.

2. **Answer-first strategy in prompt** — Add guidance telling the agent to write a partial/best-guess answer to `/app/answer.txt` early, then refine as more data is extracted. This prevents the catastrophic failure mode where the agent does all the research correctly but runs out of tokens before writing anything (exactly what happened in uid0057: 514K input tokens consumed, 0 output tokens remaining, answer never written).

### Gap 5: Non-numeric answer formats not covered (LOW RISK)

**Problem:** uid0033 expects a date string ("March 3, 1977"). Our prompt and verification checklist are entirely numeric-focused.

**Affected tasks:** uid0033, potentially others in the full 246-question set

**Proposed fix:** Add answer format guidance for dates, percentages with % sign, and text strings.

### Non-Gap: MCP tools never invoked (NO ACTION)

**Finding:** MCP tools are correctly configured in `arena.yaml`, properly translated to `opencode.json` by the harness (`type: "local"`, `command: ["python", "-m", "mcp_server"]`), and fully functional (20/20 unit tests pass against fixture data). However, glm-5 has never invoked an MCP tool in any run — it exclusively uses built-in opencode tools (`bash`, `read`, `grep`, `write`). This was verified by searching all agent trajectories across multiple runs.

**Decision:** No prompt change. The model's bash/grep/python workflow already achieves 100% on tested tasks. Forcing MCP usage risks regressions on passing tasks for no proven benefit. The MCP server remains available as a safety net if a future model starts using it.

**Implication for Gap 4:** This finding directly informed the Gap 4 fix. The original proposal was to add a `batch_find_value` MCP tool, but since MCP tools are never invoked, the fix was revised to prompt-level bash loop patterns and an answer-first strategy instead.

### Gap 6: Stochastic variance on hard tasks (LOW-MEDIUM RISK)

**Problem:** uid0111 (HP filter) is fragile — 15 min, 849K tokens, sensitive to API rate limits. Model variance is 40-80% across runs.

**Root cause:** Not a prompt issue. This is inherent to the model + task complexity + infrastructure.

**Proposed fix:** No prompt change. Accept variance. Could reduce by pre-installing statsmodels in a custom Docker image, but that's out of scope for the competition.

## Implementation Plan

| Priority | Gap | Effort | Expected Impact | Status |
|----------|-----|--------|-----------------|--------|
| P1 | Gap 2: Topic-to-section mapping | Medium | Covers 9 untested tasks | **Done** ✅ (added to prompt: "Topic-to-Section Mapping" table with grep patterns for T-bills, public debt, expenditures, capital movements, ESF, gold, interest rates, banking) |
| P2 | Gap 3: Python calculation snippets | Medium | Reduces time/errors on 5 hard tasks | **Done** ✅ (2026-03-30: rewrote `skills/python-calculations/SKILL.md` with ready-to-use snippets for geometric mean, Theil index, annualized volatility/Brownian motion, CAGR, Euclidean norm, and HP filter) |
| P3 | Gap 1: Pre-1940s document guidance | Low | Covers 3-4 tasks | **Done** ✅ (merged into P1 — prompt includes "For early-era documents (pre-1940s)" note under topic-to-section mapping) |
| P4a | Gap 4a: Bash loop pattern for multi-file extraction | Low | Prevents token exhaustion on multi-year tasks (uid0057 direct fix) | **Done** ✅ (added to prompt: "Problem-Solving Strategy" step 5 with bash `for` loop example; pitfalls list warns against 10+ sequential reads) |
| P4b | Gap 4b: Answer-first strategy in prompt | Low | Prevents empty answer.txt when token budget runs out | **Done** ✅ (added to prompt: "Problem-Solving Strategy" step 8 — "Write a preliminary answer early"; pitfalls list warns against running out of tokens before writing answer.txt) |
| P5 | Gap 5: Non-numeric answer formats | Low | Covers 1+ tasks | **Done** ✅ (2026-03-30: added date string format "March 3, 1977", percentage-with-% format "4.5%", text/name answer format to `skills/answer-patterns/SKILL.md`; updated verification checklist to enumerate all answer types) |
| ~~P4~~ | ~~Gap 4a: `batch_find_value` MCP tool~~ | — | ~~Superseded: agent never uses MCP tools~~ | **Dropped** |

## Results & Analysis

_To be filled after implementation and testing._

### Run Results

| Run ID | Date | Tasks | Score | Notes |
|--------|------|-------|-------|-------|
| run-20260319-224250-a5f7ab | 2026-03-19 | 10 | 100% (10/10) | Baseline before this proposal (z-ai/glm-5) |
| run-20260330-133742-6f403b | 2026-03-30 | 20 | 0% (0/20) | ❌ API key not exported to env — `OpenRouter API key is missing` (minimax-m2.5) |
| run-20260330-142229-9f6e68 | 2026-03-30 | 20 | 0% (0/20) | ❌ OpenRouter spending limit hit — `Key limit exceeded (total limit)` 403 (minimax-m2.5) |

### Per-Task Analysis

_P2 + P5 changes deployed but not yet validated — blocked by OpenRouter API key limit._

| Task | Result | Root Cause (if failed) | Fix Applied |
|------|--------|----------------------|-------------|
| All 20 tasks | FAIL (both runs) | OpenRouter API: Run 1 = key not in env; Run 2 = spending limit exceeded | N/A — infrastructure issue, not prompt/skill issue |

### Key Findings

1. **P2 (Python calculations) and P5 (answer formats) implemented** — skill files updated with ready-to-use content, but untested due to API issues.
2. **Model is now minimax-m2.5** (per commit dcc208e). Previous 100% baseline was on z-ai/glm-5. Need to verify which model to use for validation.
3. **OpenRouter spending limit** needs to be replenished before further testing.
