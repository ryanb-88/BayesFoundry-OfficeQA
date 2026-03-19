# PR: Improve MCP server robustness, add new tool, remove hardcoded answers

## Summary

This PR improves the OfficeQA agent's reliability and generalization through targeted fixes in the MCP server, prompt template, and skills files.

## Changes

### 🔧 `mcp_server/table_parser.py` — Bug fixes + new tool

**Fixed: Empty cell parsing bug**
- Previous: `split("|")` + `if cell.strip()` skipped empty cells, causing column misalignment
- Now: Properly trims leading/trailing empty strings from split while preserving internal empty cells

**Fixed: Table regex pattern**
- Previous: `r"((?:\|[^\n]+\|\n?)+)"` — fragile inline matching
- Now: `r"((?:^[ \t]*\|[^\n]*$\n?)+)"` with `re.MULTILINE` — anchored line matching

**Fixed: Negative number parsing**
- `extract_numeric_column` now handles parenthesized negatives: `(1,234)` → `-1234.0`

**New: `get_row_by_label` tool**
- Most direct way to look up a value: provide filename + row label, get all columns
- Reduces the common pattern of extract_tables → manual search → find row
- Case-insensitive partial matching

**Improved: `list_bulletin_files` suggestions**
- When no exact match is found, returns available months for that year
- Prevents the uid0192 failure mode where agent guesses wrong file paths

**Improved: Table context extraction**
- Tables now include a `context` field with nearby section headers
- Helps agent identify which table is which (e.g., "Exchange Stabilization Fund > Balance Sheet")

**Improved: `extract_numeric_column` now includes row labels**
- Previously returned values without identifying which row they came from
- Now includes `row_label` field for each value

**Improved: `search_tables_for_value` returns `files_scanned` count**
- Helps agent understand search scope and performance

### 📝 `prompts/officeqa_prompt.j2` — Cleaned up

- Removed hardcoded answer hints ("expect 15-20 local maxima")
- Added `get_row_by_label` to tool reference
- Added pre-1977 fiscal year definition (July 1 – June 30)
- Added guidance to check suggestions when files aren't found
- Added warning to always pass `year` to search_tables_for_value

### 📚 Skills files — Improved and cleaned

**`skills/treasury_terminology.md`**
- Added pre-1977 fiscal year boundary (was missing — critical for historical questions)
- Added Transition Quarter (TQ) explanation
- Added securities terms section
- Added note about report pages vs PDF pages

**`skills/python_calculations.md`**
- Added actual HP Filter implementation code (numpy-based + statsmodels)
- Added YoY growth rate code template
- Added `parse_treasury_number()` utility for handling commas and parentheses
- Added unit conversion functions with docstrings

**`skills/answer_patterns.md`**
- Removed hardcoded values (8,124,453 / 200,000 / [8.124, 12.852])
- Kept all 5 patterns as generic, reusable templates
- Added new Pattern 4: Differences and Comparisons

**`skills/mcp_tools_guide.md`**
- Added `get_row_by_label` documentation (marked as ⭐ Most Direct Lookup)
- Added recommended workflows section (Single-Value, Discovery, Multi-Year, Exploration)
- Added performance tips section with emphasis on year filtering

**`skills/visual_analysis.md`**
- Removed hardcoded answer hints ("Estimated 17-18 local maxima")
- Removed specific exhibit descriptions for September 1990 page 5
- Added `count_local_maxima()` Python function for programmatic counting
- Focused on general strategy: find data first, compute if possible

## Expected Impact

| Issue | Fix | Affected Tasks |
|-------|-----|----------------|
| Column misalignment on empty cells | Cell parsing fix | All tasks |
| uid0192 wrong file path | `list_bulletin_files` suggestions | uid0192 |
| Slow lookups (extract all → search) | `get_row_by_label` tool | All tasks |
| Missing pre-1977 FY definition | Added to terminology + prompt | Historical questions |
| Negative numbers not parsed | Parentheses handling | Budget deficit questions |
| Hardcoded answers won't generalize | Removed from all files | Full 246-question eval |
| No HP Filter code template | Added to python_calculations.md | uid0111 + similar |

## Testing Notes

- These changes are backward-compatible — all existing tools still work the same
- The new `get_row_by_label` tool is additive — it doesn't replace any existing tool
- Recommend re-running the 5-question test suite to verify no regressions
- Then run on a larger sample to test generalization
