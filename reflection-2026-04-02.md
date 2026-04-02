# Reflection: OfficeQA Hackathon — April 2, 2026

## Score Progression

| Version | Score | Key Change |
|---------|-------|-----------|
| v0.3.0 | 150.952 | Baseline openhands-sdk + GLM-5 |
| v0.4.0 | 152.022 | Initial skills + corpus tools |
| v0.4.0 | 165.837 | Inline prompt: topic mapping, verification checklist, self-consistency, bash loops, chart triage, mangled headers |
| v0.4.0 v7 | 161.229 | LLM classifier in Step 0 + skills 06/07 (regression) |
| **v0.5.0** | **172.369** | **SKILL.md auto-injection — new best** |

---

## Biggest Insights

### 1. The harness was never loading skills (until v0.5.0)

The single most impactful discovery: the openhands-sdk harness only uploads skill files
that live in subdirectories named with a `SKILL.md` file. Our flat `.md` files
(`01_corpus_structure.md`, etc.) at the root of `skills/` were **never uploaded to the
container** — let alone loaded. The agent was running completely blind to all our skill
content from the start.

**Fix:** Restructure to `skills/{skill-name}/SKILL.md`. Harness now uploads all 7 skills
and `run_agent.py` auto-injects them into the system prompt before the agent starts.
Result: "Loaded 0 skills" → "Loaded 7 skills", +6.5 points.

### 2. Step 0 was always ignored

GLM-5 consistently skipped Step 0 regardless of how it was written — Python classifier,
keyword classifier, LLM decision table, all ignored. By step 4 of every trajectory the
agent was already running grep without having executed Step 0. Skills never loaded
manually either way.

**Lesson:** Don't design prompt logic that requires the agent to follow a specific
first-step routine. Build systems where knowledge is delivered passively (auto-injected)
rather than requiring agent action.

### 3. What actually drove the 165.837 score

It was NOT skills (they weren't loading). It was the **inline prompt content** the agent
reads naturally. The single most impactful pattern was the **scratchpad**.

#### Scratchpad — the most important single pattern

GLM-5 loses track of intermediate values across multiple tool calls. OfficeQA questions
frequently require extracting values across multiple bulletin files, years, and turns.
Without persistent storage, the agent extracts a 1970 value in turn 3, a 1975 value in
turn 5, a 1980 value in turn 7 — and by turn 9 when it calculates, the early values have
scrolled out of active attention. It either hallucinates them or uses wrong numbers.

The scratchpad pattern forces the agent to write every extracted value to disk with source
annotation:
```bash
mkdir -p /app/scratchpad
echo "1985: 123.4 (from bulletin 1986_03, Table FO-1)" >> /app/scratchpad/notes.txt
```
Then `cat /app/scratchpad/notes.txt` before calculating ensures it computes with the full,
accurate dataset. The verification checklist and topic mapping help find the right data —
the scratchpad ensures the agent **uses** the right data when it actually computes. These
are two different failure modes and the scratchpad covers the one everything else misses.

#### Other inline elements that helped:
- Topic → table mapping (which bulletin sections to grep for each financial topic)
- Verification checklist (unit check, fiscal year check, latest revision check)
- Self-consistency (re-extract via different grep, recompute)
- Bash loops for multi-year extractions
- Chart/visual triage (look ±50 lines from exhibit reference for underlying table)
- Mangled header guidance (`>` separators, `Unnamed: X_level_Y` patterns)

These work because the agent reads the full prompt naturally before starting.

### 4. More content ≠ better performance (but skills injection is an exception)

Adding 13 math patterns + LLM classifier (v7) caused a regression to 161.2. The
concern was that 7 fully injected skills (~15K tokens overhead) would "lose" the agent.
The data said otherwise: 172.369 shows GLM-5 handles the extra context well when the
content is structured knowledge, not redundant instructions.

The key distinction: **passive reference material** (skill content) helps. **More
imperative instructions** (extra steps, longer classifiers) hurts.

### 5. Score variance is real

Two runs with identical v0.4.0 code produced 165.837 and 161.229. That's ~4.6 points
of variance (~7 questions). Single data points don't tell the full story. The 172.369
is a meaningful improvement (+6.5 from best) but expect ±3-4 points run-to-run.

### 6. The Python classifier in Step 0 had a subtle flaw

The 165.8 Step 0 had `q = '''{{ instruction }}'''.lower()` — the question was
hardcoded into the Python script at template render time. If the agent HAD run it, the
script would have thrown `FileNotFoundError` (files weren't in the container). So it
was doubly broken: agent ignored it AND it would have failed if run. The LLM table
in v7's Step 0 was equally useless but in a different way.

### 7. What the harness actually does

- `skills_dir: "skills/"` → harness scans for `{subdir}/SKILL.md` and uploads each to
  `/root/.openhands-sdk/skills/{subdir}/SKILL.md` in the container
- `run_agent.py` reads `SKILL_PATHS=/root/.openhands-sdk/skills`, discovers all SKILL.md
  files, creates `Skill(trigger=None)` objects (always active), passes to `AgentContext`
- OpenHands SDK injects skill content into `agent.static_system_message` before first turn
- `skill_paths: ["/app/skills"]` in `arena.yaml` config was **ignored** entirely —
  the container path is hardcoded to `/root/.openhands-sdk/skills`
- Treasury corpus tools (`treasury_mcp_server.py`) are **pre-installed** in the competition
  container at `/app/skills/mcp_servers/` — we never needed to upload them

### 8. GLM-5 architecture notes

- Context: 128K tokens; at 28K tokens/turn (with skills injected), ~4-5 turns before
  context pressure builds
- Reasoning effort "high" adds ~800-1100 reasoning tokens per turn
- Visual/chart questions are effectively unsolvable without image data (~3% of questions)
- GLM-5 is very cheap: $0.27 for a 12-turn run at 368K total input tokens
- Cost-adjusted Arena scoring means lower cost per task = higher score at same pass rate

---

## What Didn't Work / Dead Ends

- **Step 0 skill classifier (all versions)** — agent ignores it universally
- **Flat skill files** — harness never uploaded them, agent never saw them
- **`skill_paths` in arena.yaml config** — completely ignored by harness
- **Expanding the prompt with rare edge case patterns** — dilutes agent focus on common cases
- **v7 LLM decision table in Step 0** — same outcome as Python classifier: ignored

---

## Open Questions for Next Iteration

1. **Which skills contributed most to the +6.5 gain?** We injected all 7; `external-knowledge`
   (Italy/ESF/FO-1) and `fiscal-year-dates` (57% of questions) are likely the biggest drivers.
2. **Can we trim `statistical-operations` (384 lines) to just formulas** — no Python code — and
   get the same signal with less noise?
3. **Are there still systematic failure patterns** in question types we haven't addressed?
4. **Leaderboard position** — where does 172.369 put us vs competitors?
5. **Is 3/day quota sufficient**, or should we do more careful local testing before burning slots?
