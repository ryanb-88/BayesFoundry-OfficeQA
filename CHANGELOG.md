# CHANGELOG — BayesFoundry-OfficeQA v2

## v2.0.0 (2026-04-03) — Enhanced Goose Agent

### Major Improvements

#### 1. Prompt Template (`prompts/officeqa_prompt.j2`)
- **Question classification**: Agent categorizes question type (SINGLE_LOOKUP, MULTI_YEAR, COMPUTATION, COMPARISON, CHART_VISUAL) before starting — selects optimal strategy per type
- **Immediate preliminary answer**: `echo "PRELIMINARY" > /app/answer.txt` is now the FIRST action, protecting against timeout
- **Streamlined tools table**: Cleaner tool reference with MCP + bash fallback in one table
- **Enhanced output format section**: Two-step format (explicit instructions first, then general rules) — prevents the most common failure mode (format errors)
- **Stronger scratchpad enforcement**: Marked as MANDATORY, with review step before every calculation
- **Answer validation step**: New validate_answer tool integrated into solving strategy

#### 2. Treasury MCP Server (`skills/mcp_servers/treasury_mcp_server.py`)
- **NEW: `smart_search`** — Fuzzy keyword search using rapidfuzz; tolerates typos, abbreviations, and partial matches. Falls back gracefully when rapidfuzz is unavailable
- **NEW: `extract_row`** — Precision extraction of a single row from a specific table. Returns only the row + header context (saves ~80% context vs full table)
- **NEW: `validate_answer`** — Format compliance checker: detects missing brackets, units, dollar signs, text verdicts, trailing zeros, and leftover "PRELIMINARY" text
- **File caching** — `@lru_cache` on file reads; avoids re-reading the same bulletin multiple times in one session
- **Output truncation** — All tools cap output at 12K chars with smart truncation (keeps beginning + end)
- **Better "not found" messages** — Suggests similar filenames and keywords when exact match fails
- **Keyword variant generation** — Auto-tries hyphen variants, plurals, and abbreviation expansions

#### 3. Skill Loader (`skills/skill_loader.py`)
- **Priority scoring** — Skills sorted by relevance score, not just matched/unmatched. High-confidence keywords (marked with `*`) count 3x
- **Multi-word phrase matching** — Better matching for compound terms
- **Diagnostic output** — Shows which keywords triggered each skill load

#### 4. Self-Improvement Loop (`self_improve.py`)
- **Failure categorization** — Classifies each failure as DATA_NOT_FOUND, WRONG_TABLE, COMPUTATION_ERROR, FORMAT_ERROR, TIMEOUT, CHART_VISUAL, WRONG_PERIOD, or HALLUCINATION
- **Priority-ordered fixing** — Fixes FORMAT_ERROR first (easiest), then WRONG_PERIOD, then COMPUTATION, then DATA
- **Agent answer extraction** — Shows what the agent actually answered vs expected
- **Dry-run mode** — `--dry-run` flag for analysis without applying patches
- **Patches target SKILL.md subdirs** — Patches go into the proper `{skill-name}/SKILL.md` file for auto-injection
- **Markdown report generation** — Each improvement session creates a detailed report

#### 5. Run Analyzer (`analyze_run.py`)
- **Enhanced diagnostics** — Shows question, expected answer, and agent's actual answer for each failure
- **Run comparison** — `--compare` flag to diff two runs and see gains/regressions

#### 6. Configuration (`arena.yaml`)
- **Updated model** — `anthropic/claude-sonnet-4-20250514` (latest Sonnet)
- **Reduced max_turns** — 50 (from 60) — forces efficiency, saves cost
- **MCP server installs rapidfuzz** — For fuzzy search capability

### Architecture Unchanged
- Goose harness + stdio MCP for treasury tools
- SSE MCP for mcpcalc and math-learning
- Skills organized as `skills/{name}/SKILL.md` for harness auto-injection
- Jinja2 prompt template with `{{ instruction }}` variable

### Expected Impact
Based on the v1 learnings:
- Format validation alone should recover 1-3 FORMAT_ERROR tasks
- Fuzzy search should help with DATA_NOT_FOUND failures  
- Better question classification should reduce wasted turns
- Cost savings from reduced max_turns and output truncation
- Target: 180+ score (up from 172.4)
