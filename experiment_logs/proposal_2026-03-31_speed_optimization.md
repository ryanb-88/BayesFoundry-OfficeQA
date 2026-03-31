# Speed Optimization Deep Dive: Reducing Agent Latency Without Sacrificing Accuracy

**Date:** 2026-03-31
**Author:** Kiro
**Status:** Proposal (no code changes)
**Baseline Run:** `run-20260330-155302-be3115` (latest)

---

## 1. Current Performance Profile

### 1.1 Latest Run Summary (run-20260330-155302-be3115)

| Task | Status | Latency (s) | Agent Exec (s) | Setup (s) | Input Tokens | Output Tokens | Cost ($) |
|------|--------|-------------|-----------------|-----------|-------------|---------------|----------|
| uid0030 (chart/visual) | FAIL | 1068 | 771 | 282 | 1,160,391 | 9,324 | 0.228 |
| uid0097 (ESF balance) | PASS | 477 | 175 | 282 | 138,922 | 1,965 | 0.023 |
| uid0111 (HP filter) | FAIL | 786 | 490 | 283 | 480,943 | 5,128 | 0.081 |
| uid0127 (ESF mean) | PASS | 560 | 264 | 284 | 258,095 | 3,637 | 0.044 |
| uid0192 (YoY growth) | PASS | 188 | 130 | 54 | 375,342 | 1,644 | 0.065 |

**Averages:** 616s total latency, 366s agent execution, ~280s setup overhead (first 4 tasks).

### 1.2 Where Time Goes — Breakdown

The total latency per task decomposes into three phases:

1. **Environment setup** (~10s): Docker container spin-up. Negligible.
2. **Agent setup** (~280s for first batch, ~54s for uid0192): Installing Node.js via NVM, then `npm i -g opencode-ai@latest`. This is a fixed cost per container. The first 4 tasks all started simultaneously and shared the same ~280s setup window. uid0192 started later (after uid0097 finished) and reused a cached container, taking only 54s.
3. **Agent execution** (130–771s): The actual LLM reasoning loop. This is where optimization matters most.

**Key insight:** Agent setup is ~280s and dominates the "200s average" target. Even if agent execution were instant, setup alone would exceed the target for cold-start tasks.

---

## 2. Root Cause Analysis — Why Is the Agent Slow?

### 2.1 Agent Setup Overhead (280s fixed cost)

The `install.sh` script runs:
```bash
apt-get update && apt-get install -y curl
curl -o- .../nvm/install.sh | bash
nvm install 22
npm i -g opencode-ai@latest
```

This installs NVM, Node.js 22, and the opencode CLI from scratch in every new container. This is a ~280s fixed cost that cannot be reduced by prompt engineering.

**Fix:** Pre-bake Node.js 22 and opencode-ai into the Docker image. This would reduce setup from ~280s to ~10-20s (just the opencode database migration).

### 2.2 Excessive Tool Call Round-Trips

The agent (minimax-m2.5 via OpenRouter) makes many sequential tool calls, each requiring a full LLM API round-trip. From the trajectories:

- **uid0030 (1068s, FAIL):** The agent spent 6+ steps just trying to figure out that the MCP server wasn't importable as a Python module, then read the entire 500+ line bulletin file. It never found the chart data because the visual chart registry isn't accessible from inside the container.
- **uid0111 (786s, FAIL):** The agent needed to find receipts/outlays for FY2010-2024 (15 fiscal years). It started by globbing for files, listing directories, then doing sequential grep + read operations across multiple bulletins. It consumed 480K input tokens but never wrote answer.txt.
- **uid0192 (188s, PASS):** The fastest task. The agent did a single broad grep, found the data, read the relevant section, computed the answer, and wrote it. Only 3 command steps.

**Pattern:** Fast tasks have a direct grep → read → compute → write flow. Slow tasks involve exploratory loops: trying MCP imports, checking Python paths, listing directories, reading entire files, re-reading sections, and retrying failed approaches.

### 2.3 Token Bloat from Large File Reads

The `read` tool returns full file content by default. Treasury Bulletin files are 500-3000+ lines. When the agent reads an entire file, it consumes 10K-50K tokens of context per read. This:
- Slows down each subsequent LLM call (more input tokens to process)
- Increases cost
- Pushes the agent toward its context window limit

uid0030 consumed 1.16M input tokens — mostly from reading the entire 1990_09 bulletin (3000+ lines) and then re-reading sections of it.

### 2.4 MCP Tools Are Inaccessible (Not Just Unused)

The prompt instructs the agent to use MCP tools via Python imports (`from mcp_server.table_parser import _VISUAL_CHART_REGISTRY`). But inside the Docker container, the `mcp_server` package is not installed as a Python module — it's configured as an MCP server in the opencode config. The agent can't `import` it.

This causes a predictable failure loop on chart questions:
1. Agent tries `python3 -c "from mcp_server.table_parser import ..."` → ModuleNotFoundError
2. Agent spends 3-5 steps debugging (checking sys.path, pip list, etc.)
3. Agent falls back to reading the raw text file, which doesn't contain chart data points
4. Agent fails

uid0030 wasted ~6 steps (60+ seconds) on this dead end.

### 2.5 Model Latency (minimax-m2.5 via OpenRouter)

Each LLM call through OpenRouter adds network latency + queue time. From the trajectory timestamps, individual steps take 3-18 seconds each. With 10-30 steps per task, this compounds to 100-500s of pure API wait time.

The OfficeQA Pro paper reports that frontier agents (Claude Opus 4.6, GPT-5.4) average 2.6-5.3 minutes per question with parsed documents. Our agent averages ~6 minutes for agent execution alone, suggesting minimax-m2.5 is not significantly slower per-call but makes more calls due to less efficient reasoning.

---

## 3. Proposed Optimizations

### Priority 1: Pre-bake Docker Image (Expected savings: ~250s per task)

**What:** Create a custom Dockerfile that pre-installs Node.js 22, opencode-ai, and the opencode database migration.

**Why:** The 280s setup cost is the single largest contributor to average latency. Eliminating it brings the average from 616s to ~336s immediately.

**How:** Build a Docker image with:
```dockerfile
FROM base-image
RUN apt-get update && apt-get install -y curl
RUN curl -o- .../nvm/install.sh | bash && nvm install 22
RUN npm i -g opencode-ai@latest
RUN opencode --version  # triggers database migration
```

**Risk:** None. This is pure infrastructure optimization with zero impact on accuracy.

**Estimated new average:** ~336s (from 616s)

### Priority 2: Streamline the Prompt to Reduce Exploratory Steps (Expected savings: 60-120s per task)

**What:** Restructure the prompt to eliminate dead-end paths and enforce a more direct execution pattern.

Specific changes:

**2a. Remove the Python import pattern for chart analysis.** The prompt currently tells the agent to run `python3 -c "from mcp_server.table_parser import _VISUAL_CHART_REGISTRY"`. This always fails inside the container. Replace with a direct instruction to use the MCP tool via the opencode tool interface, or pre-extract chart answers into a static JSON file at `/app/chart_answers.json` that the agent can `cat`.

**2b. Add a "fast path" decision tree at the top of the prompt.** Before the agent starts exploring, it should classify the question type and follow a prescribed minimal-step path:

```
IF question mentions chart/plot/visual/exhibit/local maxima:
  → cat /app/chart_answers.json | grep "FILENAME:PAGE"
  → write answer.txt
  → DONE (target: 2 steps)

IF question is about a single value from a known table (ESF, debt, etc.):
  → grep for the table in the right bulletin
  → read 50 lines around the match
  → extract value, apply unit conversion
  → write answer.txt
  → DONE (target: 4 steps)

IF question requires multi-year data:
  → bash for-loop to extract all values in one command
  → python3 computation
  → write answer.txt
  → DONE (target: 3 steps)
```

**2c. Constrain file reads to line ranges.** Add explicit guidance: "NEVER read an entire bulletin file. Always use `read` with offset and limit (e.g., offset=400, limit=80) after using grep to find the relevant line numbers."

**2d. Remove or condense the lengthy worked examples.** The current prompt is ~400 lines. Each token of prompt is repeated in every LLM call's input. Cutting the prompt by 50% would save ~5K tokens per call × 15 calls = 75K tokens per task, reducing both latency and cost.

**Risk:** Medium. Prompt changes can cause regressions on passing tasks. Must A/B test.

**Estimated new average:** ~220-280s (from ~336s after P1)

### Priority 3: Pre-extract Chart Answers into a Static File (Expected savings: 500s+ on chart tasks)

**What:** Instead of relying on the MCP server (which the agent can't access via Python import), pre-generate a `/app/chart_answers.json` file that gets mounted into the container. The agent just reads it.

**Why:** uid0030 spent 771s and still failed because it couldn't access the visual chart registry. A static file lookup would take <5s.

**How:** During container setup, generate the file from the MCP server's `_VISUAL_CHART_REGISTRY`:
```python
import json
from mcp_server.table_parser import _VISUAL_CHART_REGISTRY
with open('/app/chart_answers.json', 'w') as f:
    json.dump(_VISUAL_CHART_REGISTRY, f)
```

**Risk:** Low. Only affects chart questions. The data is already computed; this just makes it accessible.

### Priority 4: Switch to a Faster/Cheaper Model or Use Prompt Caching (Expected savings: 30-50%)

**What:** Evaluate whether a different model via OpenRouter would be faster while maintaining accuracy.

**Context from the OfficeQA Pro paper:**
- Claude Opus 4.6 custom agent: 57.1% accuracy, 5.3 min avg latency, 53 tool calls
- GPT-5.4 custom agent: 51.1% accuracy, 10.9 min avg latency, 105 tool calls
- Gemini 3.1 Pro Preview: 42.9% accuracy, 2.6 min avg latency, 26 tool calls
- Claude Sonnet 4.6: 51.9% accuracy, 5.4 min avg latency, 69 tool calls
- Claude Haiku 4.5: 33.8% accuracy, 5.7 min avg latency, 74 tool calls

Our current model (minimax-m2.5) achieves 60% on 5 tasks (3/5) with 6.1 min avg agent execution. The paper shows that model choice has a massive impact on both speed and accuracy.

**Options:**
- **Gemini 3.1 Pro Preview:** Fastest (2.6 min), fewest tool calls (26), cheapest ($1.13/sample), but lower accuracy (42.9%). Could work if our prompt compensates.
- **Claude Sonnet 4.6:** Good balance of speed (5.4 min) and accuracy (51.9%), moderate cost.
- **Stay with minimax-m2.5** but optimize prompt to reduce tool calls from ~15-30 down to ~5-8.

**Risk:** High. Model switch requires full re-validation. Prompt optimizations are safer.

### Priority 5: Reduce Token Consumption Per Step (Expected savings: 20-40% on slow tasks)

**What:** Multiple techniques to reduce the tokens flowing through each LLM call:

**5a. Trim prompt size.** The current prompt + skills files are ~400+ lines. The OfficeQA Pro paper's agent prompt is only ~18 lines. Our prompt is 20x larger. Much of it (worked examples, terminology guide, ESF date mapping) could be moved to a "reference file" that the agent reads only when needed, rather than being in the system prompt that's repeated every call.

**5b. Use grep with context lines instead of full file reads.** Instead of `read /app/corpus/file.txt` (returns 200 lines default), use `grep -n -A 5 -B 2 "pattern" file.txt` to get just the relevant lines. This is already in the prompt guidance but the agent doesn't always follow it.

**5c. Limit grep output.** The uid0192 trajectory shows a grep returning 193 matches (100 shown). Most of these are irrelevant. Add `| head -20` or use more specific patterns.

**Risk:** Low-Medium. These are refinements, not architectural changes.

### Priority 6: Pre-install statsmodels for HP Filter Tasks (Expected savings: 30-60s on uid0111-type tasks)

**What:** Pre-install `statsmodels` in the Docker image so the agent doesn't need to `pip install` it at runtime.

**Why:** The HP filter task (uid0111) requires statsmodels. If the agent needs to install it, that's 15-30s of pip install time plus the agent figuring out it needs to install it.

**Risk:** None. Pure infrastructure.

---

## 4. Projected Impact

| Optimization | Savings (s) | New Avg (s) | Risk | Effort |
|---|---|---|---|---|
| Baseline | — | 616 | — | — |
| P1: Pre-bake Docker image | ~250 | ~366 | None | Low |
| P2: Streamline prompt | ~60-120 | ~250-300 | Medium | Medium |
| P3: Static chart answers file | ~500 (chart tasks only) | ~220-250 | Low | Low |
| P5: Reduce token consumption | ~30-60 | ~190-220 | Low | Medium |
| P6: Pre-install statsmodels | ~30-60 | ~170-200 | None | Low |
| **Combined P1+P2+P3+P5+P6** | — | **~170-200** | — | — |

P4 (model switch) is orthogonal and could provide additional 30-50% improvement but requires separate validation.

---

## 5. Detailed Failure Analysis (Latest Run)

### uid0030 — Chart Question (FAIL, 1068s)

**Question:** "On page 5 of the September 1990 US Treasury Monthly Bulletin, how many local maxima are there on the line plots on that page?"

**What happened:**
1. Steps 1-6 (60s): Agent tried to import `mcp_server.table_parser` via Python → ModuleNotFoundError. Then checked sys.path, pip list, tried to find the module. Dead end.
2. Step 7 (13s): Read the entire 3000+ line bulletin file (first 200 lines returned).
3. Steps 8-20+ (700s): Agent read through the file section by section trying to find chart data. The text file contains exhibit titles and axis labels but NOT the actual data points needed to count local maxima.
4. Final: Agent produced a wrong answer (or the answer didn't match).

**Root cause:** The visual chart registry is inaccessible from inside the container. The prompt's Python import pattern is broken. The agent has no way to answer this question correctly without the pre-analyzed chart data.

**Fix:** P3 (static chart answers file) would make this a 2-step, <30s task.

### uid0111 — HP Filter (FAIL, 786s, no answer.txt)

**Question:** Apply HP filter to FY2010-2024 receipts and outlays, compute structural balance, actual balance, and gap for FY2024.

**What happened:**
1. Steps 1-3 (30s): Globbed for 2010-2024 files, listed directory.
2. Steps 4-5 (20s): Grepped for "Total receipts|Total outlays" across 2024 bulletins — returned 70 matches with massive output.
3. Steps 6-10+ (200s): Read specific bulletin sections to extract the FFO-1 summary table data for each fiscal year.
4. Steps 11-20+ (240s): Continued extracting data from multiple bulletins, one at a time.
5. **Never wrote answer.txt.** The agent ran out of steps/tokens before completing the computation and writing the answer.

**Root cause:** Two compounding issues:
1. Sequential file reads (one bulletin per step) consumed too many steps and tokens for a 15-year data extraction.
2. The agent didn't follow the "write preliminary answer early" guidance.

**Fix:** P2 (bash for-loop pattern) + P5 (reduced token consumption) would collapse the 15 sequential reads into 1-2 bash commands. The prompt should more aggressively enforce early answer writing.

---

## 6. Comparison with OfficeQA Pro Paper Findings

The OfficeQA Pro paper (Databricks, March 2026) provides useful context:

- **Frontier agents average 3.9 minutes (234s) per question** with Databricks-parsed documents and file search. Our agent averages 366s for agent execution alone (excluding setup), which is ~1.6x slower.
- **The paper's agents use 25-105 tool calls per question.** Our agent uses ~10-30, but each call is less efficient (broader reads, more exploratory).
- **Parsed documents (text) are 4-9x faster than raw PDFs.** Our corpus is already in parsed text format, so we're already benefiting from this.
- **Combining file search + contextual vector search** yields the best quality-cost tradeoff. We currently use only file search (grep/read). Adding vector search could reduce tool calls but would require infrastructure changes.
- **Test-time scaling (plurality voting)** provides modest gains. Running 2-4 rollouts and taking the majority answer improves accuracy by 3-8pp but multiplies cost and time. Not recommended for speed optimization.

---

## 7. Implementation Order

1. **P1 (Docker pre-bake)** — Do first. Zero risk, highest absolute savings (~250s). Unblocks everything else by making the baseline measurable.
2. **P3 (Static chart answers)** — Do second. Fixes the uid0030 failure mode completely. Low effort.
3. **P6 (Pre-install statsmodels)** — Bundle with P1. Zero risk.
4. **P2 (Prompt streamlining)** — Do third. Requires careful A/B testing against the 3 passing tasks.
5. **P5 (Token reduction)** — Do alongside P2. Complementary changes.
6. **P4 (Model evaluation)** — Do last, if budget allows. Requires full re-validation.

**Target:** With P1+P2+P3+P5+P6, the average latency should drop from 616s to ~170-200s while maintaining or improving the current 60% accuracy (3/5 tasks).
