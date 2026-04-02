# Run Diagnosis: run-20260402-031308-cb4f99

**Date:** 2026-04-02
**Score:** 55% (11/20) — down from 85% (17/20) baseline
**Model:** minimax/minimax-m2.5 via OpenRouter
**Harness:** openhands-sdk v1.16.0
**Config:** condensed prompt + ToT integration + remote MCP servers

---

## Result Summary

| UID | Reward | Failure Mode | Agent Answer | Cost | Tokens (in) | Exec Time |
|-----|--------|-------------|-------------|------|-------------|-----------|
| uid0030 | 0.0 | Wrong answer (chart) | 2 (expected: 18) | $0.046 | 442K | 5m13s |
| uid0097 | 0.0 | Wrong answer (interpretation) | [0.200, 20.776] | $0.073 | 789K | 5m29s |
| uid0127 | 0.0 | Wrong answer (data extraction) | 35065198.67 | $0.108 | 1.12M | 10m46s |
| uid0194 | 0.0 | No answer.txt (terminated mid-turn) | — | $0.024 | 224K | 1m26s |
| uid0023 | 0.0 | No answer.txt (Finish without write) | 2.24 (not written) | $0.034 | 325K | 3m12s |
| uid0220 | 0.0 | Wrong answer (formula flip) | 31.3 (expected: ~27.0) | $0.069 | 694K | 5m31s |
| uid0004 | 0.0 | No answer.txt (terminated mid-extraction) | — | $0.035 | 324K | 2m58s |
| uid0136 | 0.0 | No answer.txt (terminated mid-extraction) | — | $0.022 | 236K | 1m55s |
| uid0246 | 0.0 | Wrong answer (data extraction) | 9124.06 | $0.221 | 2.3M | 15m36s |

---

## Gap 1: Skills Not Loading (CRITICAL — affects ALL 20 trials)

Every trial log shows `Loaded 0 skills`. The 5 skill files in `skills/` (answer-patterns, treasury-terminology, mcp-tools, visual-analysis, python-calculations) are never injected into agent context.

**Impact:** The prompt was condensed by ~47% specifically because skills were supposed to carry the deduplicated content. Without skills, the agent runs on a stripped-down prompt with no supplementary knowledge — no compute.py library, no MCP tool reference, no answer format patterns, no treasury terminology guide.

**Root cause (confirmed):** The openhands-sdk harness does NOT support the `skills_dir` mechanism that the opencode harness used. Here's the full chain:

1. `arena.yaml` sets `skills_dir: "skills/"` → passed as kwarg to agent constructor
2. `harbor.agents.base.BaseAgent.__init__` stores it as `self.skills_dir = "skills/"`
3. The `opencode` harness used `self.skills_dir` to copy skills into the container via `_build_register_skills_command()`: `cp -r "skills/"/* ~/.config/opencode/skills/`
4. The `openhands_sdk` harness (`harbor.agents.installed.openhands_sdk.OpenHandsSDK`) does NOT read `self.skills_dir` at all. It has its own `skill_paths` parameter (a list, not a string) that defaults to `DEFAULT_SKILL_PATHS`:
   ```python
   DEFAULT_SKILL_PATHS = [
       "/root/.openhands-sdk/skills",
       "/root/.claude/skills",
       "/root/.codex/skills",
       ...
   ]
   ```
5. These default paths don't exist in the container → `discover_skills()` finds nothing → "Loaded 0 skills"
6. Even if `skill_paths` were set correctly in `arena.yaml`, the openhands-sdk harness never copies skill files into the container — there's no equivalent of opencode's `_build_register_skills_command()`.

**The naming mismatch (`skills_dir` vs `skill_paths`) AND the missing file-copy step are both bugs in the openhands-sdk harness integration.**

**Fix options:**
- **Option A (workaround):** Inline all skill content directly into the prompt template (`officeqa_prompt.j2`). This bypasses the broken skill loading entirely. Downside: larger prompt, but the content was already condensed.
- **Option B (proper fix):** Modify `arena.yaml` to use `skill_paths: ["/root/.openhands-sdk/skills"]` AND add a pre-run command that copies skills into the container. However, the harness doesn't expose a pre-run hook for this.
- **Option C (upstream fix):** File a bug against harbor's `OpenHandsSDK` to implement `_build_register_skills_command()` like the opencode agent does, reading from `self.skills_dir`.

**Recommended:** Option A (inline skills into prompt) for immediate fix. Option C for long-term.

**Priority:** P0 — this alone could explain the 30-point regression from 85% to 55%.

---

## Gap 2: Agent Terminates Without Writing answer.txt (4/9 failures)

Four questions failed because `/app/answer.txt` was never created:

### uid0194 — Terminated mid-turn (CAGR calculation)
- Agent found June 2003 data (2,289,997M), was about to search for June 2013
- Terminated after only $0.024 spend and 224K input tokens
- **Root cause:** Exhausted iteration budget. Too many turns on verbose reasoning before reaching second data point.

### uid0023 — Finish without write (WW2 intergovernmental transfers)
- Agent computed correct answer (2.24) and said "I've written this answer to /app/answer.txt" in Finish message
- **Root cause:** Used `Finish` tool to report answer but never executed `file_editor create` or `echo > /app/answer.txt`. The Finish tool does NOT write files.

### uid0004 — Terminated mid-extraction (1953 vs 1940 defense expenditures)
- Still navigating tables for December 1953 data when terminated
- **Root cause:** Multi-file extraction across two distant year ranges (1940 and 1953) consumed too many turns.

### uid0136 — Terminated mid-extraction (geometric mean of T-bill rates)
- Still searching through bulletin tables when terminated
- **Root cause:** Complex multi-year, multi-week extraction exceeded iteration budget.

**Common pattern:** Agent spends too many turns on exploratory reads and verbose reasoning, exhausting iteration budget before writing an answer. ToT planning overhead may be contributing — generates long reasoning blocks but doesn't execute efficiently.

---

## Gap 3: Formula/Interpretation Errors (3/9 failures)

### uid0220 — Percent difference formula flip
- Agent initially computed correct symmetric percent difference: 27.027% → 27.0
- Then second-guessed itself and overwrote with simple percent change: 31.25% → 31.3
- **Root cause:** Despite prompt having explicit "Percent Change vs Percent Difference" section, agent ignored it. Known recurring failure (flagged in April 1 changelog).

### uid0097 — ESF capital interpretation
- Agent answered [0.200, 20.776] using "Capital account" ($200K thousands = $0.2B)
- "Total nominal capital" likely means "Total capital" ($8,124,453 thousands = $8.124B), not just the fixed capital account
- Absolute difference would then be |8.124 - 20.976| = 12.852, not 20.776
- **Root cause:** Ambiguous financial terminology. Agent chose the wrong interpretation of "nominal capital."

### uid0127 — ESF mean total assets (data extraction error)
- Agent answered 35,065,198.67 (in thousands)
- Used same value (37,455,070) for both June 1992 AND September 1992 — clearly wrong
- Question asks for "nominal dollars" but agent reported in thousands
- **Root cause:** (1) Duplicate data point from sloppy extraction, (2) possible unit mismatch.

---

## Gap 4: Chart Question Still Unsolvable (uid0030)

Agent answered "2" (expected: 18). Visual/chart question about local maxima on line plots. Text corpus doesn't contain actual data points. Agent identified only 2 peaks from annotations, missing the 18 local maxima visible in the original chart. Known failure since March 19 — fundamentally unsolvable from text-only corpus.

---

## Gap 5: High Token Consumption (uid0246)

Consumed 2.3M input tokens and $0.22 — most expensive trial by 2x. Agent spent 15+ minutes navigating Treasury bill tables across multiple bulletins with extensive reasoning blocks. Wrote answer (9124.06) but got it wrong due to incorrect tax anticipation bill data for January 1975.

---

## Priority Fixes

1. **P0 — Fix skill loading.** The openhands-sdk harness ignores `skills_dir` (it expects `skill_paths`, a list) and never copies skill files into the container. Immediate fix: inline all 5 skill files into the prompt template. Long-term: file upstream bug against harbor's `OpenHandsSDK` to implement skill copying like the opencode agent does.

2. **P1 — Write answer early.** The prompt says to write a preliminary answer in step 8, but the agent ignores this. 4/9 failures had no answer.txt at all. Consider stronger language or a mandatory first-action pattern.

3. **P1 — Fix Finish-without-write pattern.** uid0023 agent said "I've written the answer" in Finish but never actually wrote it. Add explicit rule: "You MUST write /app/answer.txt BEFORE calling Finish."

4. **P2 — Percent difference formula.** uid0220 keeps recurring. Add a more forceful rule or worked example showing the symmetric formula and explicitly warning against overwriting correct answers.

5. **P2 — Reduce ToT verbosity.** The Tree of Thought planning generates long reasoning blocks that consume iteration budget without proportional benefit. Consider making the planning step more concise or optional for simple lookup questions.
