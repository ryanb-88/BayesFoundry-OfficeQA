#!/usr/bin/env python3
"""
Treasury Bulletin MCP Server v2 for OfficeQA.
Enhanced with: fuzzy search, answer validation, structured output, caching.
"""
import re
import math
import io
import json
import hashlib
from pathlib import Path
from contextlib import redirect_stdout
from functools import lru_cache

CORPUS_DIR = Path("/app/corpus")

# ---------------------------------------------------------------------------
# Lazy imports
# ---------------------------------------------------------------------------
try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("treasury-tools")
except ImportError:
    class _Dummy:
        def tool(self):
            return lambda f: f
        def run(self):
            raise RuntimeError("mcp package not installed")
    mcp = _Dummy()

# Optional fuzzy matching
try:
    from rapidfuzz import fuzz, process as rfprocess
    HAS_FUZZY = True
except ImportError:
    HAS_FUZZY = False


# ─── Helpers ────────────────────────────────────────────────────────────────

def _parse_filename(name: str):
    m = re.match(r"treasury_bulletin_(\d{4})_(\d{2})\.txt", name)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _get_path(year: int, month: int) -> Path:
    return CORPUS_DIR / f"treasury_bulletin_{year:04d}_{month:02d}.txt"


def _find_table_bounds(lines: list, idx: int):
    """Find the start and end of a table block containing line idx."""
    start = idx
    while start > 0:
        prev = lines[start - 1].strip()
        if prev.startswith("|") or (prev == "" and start - 2 >= 0 and lines[start - 2].strip().startswith("|")):
            start -= 1
        else:
            break
    end = idx + 1
    while end < len(lines):
        curr = lines[end].strip()
        if curr.startswith("|"):
            end += 1
        elif curr == "":
            peek = end + 1
            while peek < len(lines) and lines[peek].strip() == "":
                peek += 1
            if peek < len(lines) and lines[peek].strip().startswith("|"):
                end = peek + 1
            else:
                break
        else:
            break
    return max(0, start), min(len(lines), end)


def _nearest_header(lines: list, from_idx: int, look_back: int = 40) -> int:
    """Find the nearest markdown header above from_idx."""
    for i in range(from_idx - 1, max(0, from_idx - look_back), -1):
        if lines[i].startswith("#"):
            return i
    return max(0, from_idx - 5)


@lru_cache(maxsize=64)
def _read_lines_cached(path_str: str) -> tuple:
    """Read and cache file lines (as tuple for hashability)."""
    return tuple(Path(path_str).read_text(encoding="utf-8", errors="replace").split("\n"))


def _read_lines(path: Path) -> list:
    try:
        return list(_read_lines_cached(str(path)))
    except Exception:
        return path.read_text(encoding="utf-8", errors="replace").split("\n")


def _truncate_output(text: str, max_chars: int = 12000) -> str:
    """Truncate output to save context budget."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + f"\n\n... [TRUNCATED {len(text) - max_chars} chars] ...\n\n" + text[-half:]


# ─── Core Tools ──────────────────────────────────────────────────────────────

@mcp.tool()
def list_bulletins(year_from: int = 1939, year_to: int = 2025) -> str:
    """List available Treasury Bulletin filenames within a year range."""
    files = sorted(CORPUS_DIR.glob("treasury_bulletin_*.txt"))
    out = [f.name for f in files if (p := _parse_filename(f.name)) and year_from <= p[0] <= year_to]
    return "\n".join(out) if out else f"No bulletins found for {year_from}–{year_to}"


@mcp.tool()
def read_bulletin(year: int, month: int) -> str:
    """Read the full content of a specific Treasury Bulletin. LAST RESORT — very large."""
    path = _get_path(year, month)
    if not path.exists():
        return f"NOT FOUND: treasury_bulletin_{year:04d}_{month:02d}.txt"
    content = path.read_text(encoding="utf-8", errors="replace")
    return _truncate_output(content, max_chars=30000)


@mcp.tool()
def extract_tables(year: int, month: int, keyword: str) -> str:
    """
    START HERE. Extract tables containing a keyword from ONE specific bulletin.
    Returns ~5K tokens vs 150K for a full file read.
    """
    path = _get_path(year, month)
    if not path.exists():
        # Try to find the closest available bulletin
        available = sorted(CORPUS_DIR.glob(f"treasury_bulletin_{year:04d}_*.txt"))
        if available:
            alt = available[0].name
            return f"NOT FOUND: treasury_bulletin_{year:04d}_{month:02d}.txt\nDid you mean: {alt}?"
        return f"NOT FOUND: treasury_bulletin_{year:04d}_{month:02d}.txt\nNo bulletins found for year {year}."
    
    lines = _read_lines(path)
    pattern = re.compile(keyword, re.IGNORECASE)
    found = []
    seen = set()
    
    for i, line in enumerate(lines):
        if pattern.search(line):
            s, e = _find_table_bounds(lines, i)
            if (s, e) in seen:
                continue
            seen.add((s, e))
            h = _nearest_header(lines, s)
            table_text = "\n".join(lines[h:e])
            found.append(table_text)
    
    if not found:
        # Suggest alternatives
        suggestions = _suggest_keywords(lines, keyword)
        msg = f"No tables containing '{keyword}' in treasury_bulletin_{year:04d}_{month:02d}.txt"
        if suggestions:
            msg += f"\nSimilar terms found: {', '.join(suggestions[:5])}"
        return msg
    
    result = ("\n\n" + "=" * 60 + "\n\n").join(found[:5])
    return _truncate_output(result)


@mcp.tool()
def search_corpus(
    keyword: str,
    year_from: int = 1939,
    year_to: int = 2025,
    month: int = 0,
    max_results: int = 8,
) -> str:
    """
    Search for a keyword across Treasury Bulletin files (oldest-first).
    Use month=0 for all months.
    """
    pattern = re.compile(keyword, re.IGNORECASE)
    results = []

    for fpath in sorted(CORPUS_DIR.glob("treasury_bulletin_*.txt")):
        parsed = _parse_filename(fpath.name)
        if not parsed:
            continue
        fy, fm = parsed
        if fy < year_from or fy > year_to:
            continue
        if month > 0 and fm != month:
            continue
        try:
            lines = _read_lines(fpath)
        except Exception:
            continue
        seen_bounds = set()
        for i, line in enumerate(lines):
            if pattern.search(line):
                s, e = _find_table_bounds(lines, i)
                if (s, e) in seen_bounds:
                    continue
                seen_bounds.add((s, e))
                h = _nearest_header(lines, s)
                table_text = "\n".join(lines[h:e])
                results.append(f"=== {fpath.name} (line {i + 1}) ===\n{table_text}")
                if len(results) >= max_results:
                    return _truncate_output("\n\n".join(results))

    return _truncate_output("\n\n".join(results)) if results else f"No matches for '{keyword}' in {year_from}–{year_to}"


@mcp.tool()
def find_latest_value(keyword: str, year_from: int, year_to: int) -> str:
    """
    Search bulletins NEWEST-FIRST to get the most recently revised value.
    Treasury bulletins revise prior figures — always prefer the latest.
    """
    pattern = re.compile(keyword, re.IGNORECASE)
    for fpath in sorted(CORPUS_DIR.glob("treasury_bulletin_*.txt"), reverse=True):
        parsed = _parse_filename(fpath.name)
        if not parsed:
            continue
        fy, fm = parsed
        if fy < year_from or fy > year_to:
            continue
        try:
            lines = _read_lines(fpath)
        except Exception:
            continue
        for i, line in enumerate(lines):
            if pattern.search(line):
                s, e = _find_table_bounds(lines, i)
                h = _nearest_header(lines, s)
                return f"LATEST in {fpath.name} (line {i + 1}):\n\n" + "\n".join(lines[h:e])
    return f"No match for '{keyword}' in bulletins {year_from}–{year_to}"


@mcp.tool()
def batch_extract(keyword: str, year_from: int, year_to: int, month: int = 0) -> str:
    """
    Extract matching table sections from ALL bulletins in a year range at once.
    Returns ONE match per bulletin. Ideal for multi-year list questions.
    """
    pattern = re.compile(keyword, re.IGNORECASE)
    results = []
    for fpath in sorted(CORPUS_DIR.glob("treasury_bulletin_*.txt")):
        parsed = _parse_filename(fpath.name)
        if not parsed:
            continue
        fy, fm = parsed
        if fy < year_from or fy > year_to:
            continue
        if month > 0 and fm != month:
            continue
        try:
            lines = _read_lines(fpath)
        except Exception:
            continue
        for i, line in enumerate(lines):
            if pattern.search(line):
                s, e = _find_table_bounds(lines, i)
                h = _nearest_header(lines, s)
                results.append(f"=== {fpath.name} ===\n" + "\n".join(lines[h:e]))
                break
    return _truncate_output("\n\n".join(results)) if results else f"No matches for '{keyword}' in {year_from}–{year_to}"


# ─── NEW: Enhanced Tools ────────────────────────────────────────────────────

def _suggest_keywords(lines: list, keyword: str, max_suggestions: int = 5) -> list:
    """Find similar keywords in the file using fuzzy matching or simple heuristics."""
    # Collect unique row labels from pipe-delimited tables
    labels = set()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            parts = stripped.split("|")
            if len(parts) > 1:
                label = parts[1].strip()
                if label and not label.startswith("-") and len(label) > 3:
                    labels.add(label)
    
    if HAS_FUZZY and labels:
        matches = rfprocess.extract(keyword, list(labels), scorer=fuzz.partial_ratio, limit=max_suggestions)
        return [m[0] for m in matches if m[1] > 50]
    else:
        # Simple substring match fallback
        keyword_lower = keyword.lower()
        return [l for l in labels if keyword_lower[:4] in l.lower()][:max_suggestions]


@mcp.tool()
def smart_search(
    keyword: str,
    year_from: int = 1939,
    year_to: int = 2025,
    month: int = 0,
    max_results: int = 5,
) -> str:
    """
    Fuzzy keyword search — tolerates typos, abbreviations, and partial matches.
    Use when exact keyword search returns nothing.
    """
    exact_result = search_corpus(keyword, year_from, year_to, month, max_results)
    if "No matches" not in exact_result:
        return exact_result
    
    # Try variations
    variations = _generate_keyword_variants(keyword)
    for variant in variations:
        try:
            pattern = re.compile(variant, re.IGNORECASE)
        except re.error:
            continue
        
        results = []
        for fpath in sorted(CORPUS_DIR.glob("treasury_bulletin_*.txt")):
            parsed = _parse_filename(fpath.name)
            if not parsed:
                continue
            fy, fm = parsed
            if fy < year_from or fy > year_to:
                continue
            if month > 0 and fm != month:
                continue
            try:
                lines = _read_lines(fpath)
            except Exception:
                continue
            for i, line in enumerate(lines):
                if pattern.search(line):
                    s, e = _find_table_bounds(lines, i)
                    h = _nearest_header(lines, s)
                    results.append(f"=== {fpath.name} (fuzzy: '{variant}') ===\n" + "\n".join(lines[h:e]))
                    if len(results) >= max_results:
                        return _truncate_output("\n\n".join(results))
                    break
        
        if results:
            return _truncate_output("\n\n".join(results))
    
    return f"No matches for '{keyword}' (or variants) in {year_from}–{year_to}"


def _generate_keyword_variants(keyword: str) -> list:
    """Generate spelling/format variants of a keyword."""
    variants = []
    kw = keyword.strip()
    
    # Hyphen variants: "T-bill" ↔ "T bill" ↔ "Tbill"
    if "-" in kw:
        variants.append(kw.replace("-", " "))
        variants.append(kw.replace("-", ""))
    else:
        words = kw.split()
        if len(words) == 2:
            variants.append(f"{words[0]}-{words[1]}")
    
    # Plural variants
    if kw.endswith("s"):
        variants.append(kw[:-1])
    else:
        variants.append(kw + "s")
    
    # Abbreviation expansion
    abbrevs = {
        "FY": "Fiscal Year",
        "CY": "Calendar Year",
        "ESF": "Exchange Stabilization Fund",
        "SDR": "Special Drawing Rights",
        "IMF": "International Monetary Fund",
        "PDO": "Public Debt Operations",
        "FFO": "Federal Fiscal Operations",
    }
    kw_upper = kw.upper()
    if kw_upper in abbrevs:
        variants.append(abbrevs[kw_upper])
    
    # Partial match pattern
    if len(kw) > 5:
        variants.append(kw[:len(kw)//2])
    
    return variants


@mcp.tool()
def extract_row(year: int, month: int, table_keyword: str, row_keyword: str) -> str:
    """
    Extract a SPECIFIC ROW from a table. More precise than extract_tables.
    Returns the row with its header context for column identification.
    
    Example: extract_row(1977, 3, "FD-1", "Gross Federal Debt")
    """
    path = _get_path(year, month)
    if not path.exists():
        return f"NOT FOUND: treasury_bulletin_{year:04d}_{month:02d}.txt"
    
    lines = _read_lines(path)
    table_pat = re.compile(table_keyword, re.IGNORECASE)
    row_pat = re.compile(row_keyword, re.IGNORECASE)
    
    results = []
    
    for i, line in enumerate(lines):
        if table_pat.search(line):
            # Found a table reference — now search within this table for the row
            s, e = _find_table_bounds(lines, i)
            h = _nearest_header(lines, s)
            
            # Find the header rows (first few | lines) and the matching data row
            header_lines = []
            data_line = None
            for j in range(s, e):
                stripped = lines[j].strip()
                if stripped.startswith("|"):
                    if row_pat.search(stripped):
                        data_line = (j, stripped)
                    elif data_line is None:
                        # Collect header lines before the data row
                        header_lines.append(stripped)
            
            if data_line:
                # Return: section header + table headers + matched row
                context = "\n".join(lines[h:s]) + "\n"
                context += "\n".join(header_lines[-3:]) + "\n"  # Last 3 header rows
                context += f">>> {data_line[1]}"  # Mark the matched row
                results.append(f"=== {_get_path(year, month).name} (line {data_line[0]+1}) ===\n{context}")
    
    if results:
        return "\n\n".join(results[:3])
    return f"No row matching '{row_keyword}' in tables matching '{table_keyword}' in bulletin {year:04d}_{month:02d}"


@mcp.tool()
def validate_answer(answer: str, question: str) -> str:
    """
    Validate answer format against question requirements.
    Returns warnings if format doesn't match expected pattern.
    """
    warnings = []
    q_lower = question.lower()
    a_stripped = answer.strip()
    
    # Check for bracket format
    if any(phrase in q_lower for phrase in ["enclosed in square brackets", "in the format [", "output as ["]):
        if not (a_stripped.startswith("[") and a_stripped.endswith("]")):
            warnings.append("MISSING BRACKETS: Question asks for bracket format [...]")
    
    # Check for unit suffix
    for unit in ["million", "millions", "billion", "billions"]:
        if f"in {unit}" in q_lower or f"report.*{unit}" in q_lower:
            if unit not in a_stripped.lower():
                warnings.append(f"MISSING UNIT: Question asks for '{unit}' suffix")
    
    # Check for dollar sign
    if "$" in question and "$" not in a_stripped:
        warnings.append("MISSING $: Question uses dollar notation but answer doesn't")
    
    # Check for percentage
    if "%" in question and "%" not in a_stripped:
        # Only warn if question explicitly uses % in output format context
        if any(phrase in q_lower for phrase in ["report as %", "express as %", "in percentage"]):
            warnings.append("MISSING %: Question asks for percentage notation")
    
    # Check for text verdict in brackets
    verdict_pairs = [
        (["surplus", "deficit"], "surplus/deficit"),
        (["unusual", "normal"], "normal/unusual"),
        (["increased", "decreased"], "Increased/Decreased"),
    ]
    for terms, label in verdict_pairs:
        if any(t in q_lower for t in terms):
            if not any(t in a_stripped.lower() for t in terms):
                warnings.append(f"MISSING VERDICT: Question asks for {label} classification")
    
    # Check for trailing zeros
    trailing_zero = re.search(r'\d+\.0(?!\d)', a_stripped)
    if trailing_zero:
        warnings.append(f"TRAILING ZERO: '{trailing_zero.group()}' should drop the .0")
    
    # Check for "PRELIMINARY" still in answer
    if "PRELIMINARY" in a_stripped.upper():
        warnings.append("PRELIMINARY ANSWER: Still contains placeholder text!")
    
    if warnings:
        return "⚠️ FORMAT WARNINGS:\n" + "\n".join(f"  - {w}" for w in warnings)
    return "✅ Format looks correct."


@mcp.tool()
def calculate(code: str) -> str:
    """
    Run Python code for precise arithmetic. Always use this for math.
    Use print() to output results.
    """
    safe_globals = {
        "__builtins__": {},
        "math": math, "abs": abs, "round": round, "sum": sum,
        "min": min, "max": max, "len": len, "range": range,
        "list": list, "zip": zip, "enumerate": enumerate, "print": print,
        "int": int, "float": float, "str": str, "sorted": sorted,
        "pow": pow, "map": map, "filter": filter,
    }
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            exec(code, safe_globals)
        output = buf.getvalue().strip()
        if output:
            return output
        try:
            return str(eval(code, safe_globals))
        except Exception:
            return "(no output — did you forget print()?)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


# ─── CLI Mode ──────────────────────────────────────────────────────────────

def _cli():
    """CLI fallback when MCP is unavailable."""
    import sys
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 treasury_mcp_server.py <tool> [args...]")
        print("Tools: list_bulletins, extract_tables, search_corpus, find_latest_value,")
        print("       batch_extract, smart_search, extract_row, validate_answer, calculate")
        sys.exit(1)

    tool = args[0]
    rest = args[1:]

    dispatch = {
        "list_bulletins": lambda a: list_bulletins(
            int(a[0]) if a else 1939,
            int(a[1]) if len(a) > 1 else 2025,
        ),
        "extract_tables": lambda a: extract_tables(int(a[0]), int(a[1]), a[2]),
        "search_corpus": lambda a: search_corpus(
            a[0],
            int(a[1]) if len(a) > 1 else 1939,
            int(a[2]) if len(a) > 2 else 2025,
            int(a[3]) if len(a) > 3 else 0,
            int(a[4]) if len(a) > 4 else 8,
        ),
        "find_latest_value": lambda a: find_latest_value(a[0], int(a[1]), int(a[2])),
        "batch_extract": lambda a: batch_extract(
            a[0], int(a[1]), int(a[2]),
            int(a[3]) if len(a) > 3 else 0,
        ),
        "smart_search": lambda a: smart_search(
            a[0],
            int(a[1]) if len(a) > 1 else 1939,
            int(a[2]) if len(a) > 2 else 2025,
            int(a[3]) if len(a) > 3 else 0,
            int(a[4]) if len(a) > 4 else 5,
        ),
        "extract_row": lambda a: extract_row(int(a[0]), int(a[1]), a[2], a[3]),
        "read_bulletin": lambda a: read_bulletin(int(a[0]), int(a[1])),
        "validate_answer": lambda a: validate_answer(a[0], a[1] if len(a) > 1 else ""),
        "calculate": lambda a: calculate(" ".join(a)),
    }

    if tool not in dispatch:
        print(f"Unknown tool '{tool}'. Available: {', '.join(dispatch)}")
        sys.exit(1)

    try:
        print(dispatch[tool](rest))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        _cli()
    else:
        mcp.run()
