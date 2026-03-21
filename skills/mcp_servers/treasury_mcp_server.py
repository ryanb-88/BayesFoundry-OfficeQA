#!/usr/bin/env python3
"""
Treasury Bulletin MCP Server for OfficeQA.
Provides tools for smart corpus search, table extraction, and precise calculation.
"""
import re
import math
import io
from pathlib import Path
from contextlib import redirect_stdout
from mcp.server.fastmcp import FastMCP

CORPUS_DIR = Path("/app/corpus")

mcp = FastMCP("treasury-tools")


# ─── Helpers ────────────────────────────────────────────────────────────────

def _parse_filename(name: str):
    m = re.match(r"treasury_bulletin_(\d{4})_(\d{2})\.txt", name)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _get_path(year: int, month: int) -> Path:
    return CORPUS_DIR / f"treasury_bulletin_{year:04d}_{month:02d}.txt"


def _find_table_bounds(lines: list, idx: int):
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
    for i in range(from_idx - 1, max(0, from_idx - look_back), -1):
        if lines[i].startswith("#"):
            return i
    return max(0, from_idx - 5)


def _read_lines(path: Path):
    return path.read_text(encoding="utf-8", errors="replace").split("\n")


# ─── Tools ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_bulletins(year_from: int = 1939, year_to: int = 2025) -> str:
    """List available Treasury Bulletin filenames within a year range."""
    files = sorted(CORPUS_DIR.glob("treasury_bulletin_*.txt"))
    out = [f.name for f in files if (p := _parse_filename(f.name)) and year_from <= p[0] <= year_to]
    return "\n".join(out) if out else f"No bulletins found for {year_from}–{year_to}"


@mcp.tool()
def read_bulletin(year: int, month: int) -> str:
    """Read the full content of a specific Treasury Bulletin. Only use if extract_tables finds nothing."""
    path = _get_path(year, month)
    if not path.exists():
        return f"NOT FOUND: treasury_bulletin_{year:04d}_{month:02d}.txt"
    return path.read_text(encoding="utf-8", errors="replace")


@mcp.tool()
def search_corpus(
    keyword: str,
    year_from: int = 1939,
    year_to: int = 2025,
    month: int = 0,
    max_results: int = 8,
) -> str:
    """
    Search for a keyword across Treasury Bulletin files and return matches
    with full surrounding table context. Use month=0 for all months.
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
                results.append(f"=== {fpath.name} (line {i + 1}) ===\n" + "\n".join(lines[h:e]))
                if len(results) >= max_results:
                    return "\n\n".join(results)

    return "\n\n".join(results) if results else f"No matches for '{keyword}' in {year_from}–{year_to}"


@mcp.tool()
def extract_tables(year: int, month: int, keyword: str) -> str:
    """
    START HERE. Extract tables containing a keyword from ONE specific bulletin.
    Returns ~5K tokens vs 150K for a full file read.
    """
    path = _get_path(year, month)
    if not path.exists():
        return f"NOT FOUND: treasury_bulletin_{year:04d}_{month:02d}.txt"
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
            found.append("\n".join(lines[h:e]))
    if not found:
        return f"No tables containing '{keyword}' in treasury_bulletin_{year:04d}_{month:02d}.txt"
    return ("\n\n" + "=" * 60 + "\n\n").join(found[:5])


@mcp.tool()
def find_latest_value(keyword: str, year_from: int, year_to: int) -> str:
    """
    Search bulletins NEWEST-FIRST to get the most recently revised value.
    Treasury bulletins frequently revise prior figures — always use the most recent.
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
    Ideal for list questions requiring data across multiple years.
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
    return "\n\n".join(results) if results else f"No matches for '{keyword}' in {year_from}–{year_to}"


@mcp.tool()
def calculate(code: str) -> str:
    """
    Run Python code for precise arithmetic. Always use this for math — never mental calculations.
    Use print() to output results.
    """
    safe_globals = {
        "__builtins__": {},
        "math": math, "abs": abs, "round": round, "sum": sum,
        "min": min, "max": max, "len": len, "range": range,
        "list": list, "zip": zip, "enumerate": enumerate, "print": print,
        "int": int, "float": float, "str": str, "sorted": sorted,
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


if __name__ == "__main__":
    mcp.run()
