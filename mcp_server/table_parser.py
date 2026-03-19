#!/usr/bin/env python3
"""MCP server for parsing tables in OfficeQA Treasury Bulletin documents.

This server provides tools for extracting and analyzing tabular data from
the parsed Treasury Bulletin text files (Markdown format with tables).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP(
    name="officeqa-table-parser",
    instructions="Tools for extracting and analyzing tables from U.S. Treasury Bulletin documents",
)

# Default corpus location in the Docker environment
DEFAULT_CORPUS_PATH = "/app/corpus"


def _parse_markdown_table(table_text: str) -> list[dict[str, Any]]:
    """Parse a markdown table into a list of row dictionaries.

    Args:
        table_text: Raw markdown table text

    Returns:
        List of dictionaries, one per row, with column headers as keys
    """
    lines = [line.strip() for line in table_text.strip().split("\n") if line.strip()]
    if len(lines) < 2:
        return []

    # Parse header row - preserve empty cells to avoid column misalignment
    header_line = lines[0]
    parts = header_line.split("|")
    # Remove first and last empty strings from split (before first | and after last |)
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    headers = [cell.strip() if cell.strip() else f"col_{i}" for i, cell in enumerate(parts)]

    if not headers:
        return []

    # Skip separator line (e.g., |---|---|---|)
    data_start = 1
    if len(lines) > 1 and re.match(r"^\|[\s\-:|]+\|?$", lines[1]):
        data_start = 2

    rows = []
    for line in lines[data_start:]:
        cell_parts = line.split("|")
        # Same trimming logic as headers
        if cell_parts and cell_parts[0].strip() == "":
            cell_parts = cell_parts[1:]
        if cell_parts and cell_parts[-1].strip() == "":
            cell_parts = cell_parts[:-1]

        if cell_parts:
            row = {}
            for i, cell in enumerate(cell_parts):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row[key] = cell.strip()
            rows.append(row)

    return rows


def _extract_tables_from_file(file_path: Path) -> list[dict[str, Any]]:
    """Extract all markdown tables from a file.

    Args:
        file_path: Path to the Treasury Bulletin text file

    Returns:
        List of table dictionaries with metadata and data
    """
    if not file_path.exists():
        return []

    content = file_path.read_text(encoding="utf-8", errors="replace")

    # Find markdown tables - consecutive lines starting with |
    # Match blocks of lines that contain | characters (table rows)
    table_pattern = r"((?:^[ \t]*\|[^\n]*$\n?)+)"
    table_matches = re.finditer(table_pattern, content, re.MULTILINE)

    tables = []
    for i, match in enumerate(table_matches):
        table_text = match.group(1)
        rows = _parse_markdown_table(table_text)
        if rows:
            # Extract a context snippet: the 3 lines before the table for section headers
            start_pos = match.start()
            preceding_text = content[max(0, start_pos - 200):start_pos]
            context_lines = [
                ln.strip() for ln in preceding_text.split("\n")
                if ln.strip() and not ln.strip().startswith("|")
            ]
            section_context = " > ".join(context_lines[-3:]) if context_lines else ""

            tables.append({
                "table_index": i,
                "row_count": len(rows),
                "columns": list(rows[0].keys()) if rows else [],
                "context": section_context,
                "data": rows,
            })

    return tables


@mcp.tool()
def list_bulletin_files(
    corpus_path: str = DEFAULT_CORPUS_PATH,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    """List available Treasury Bulletin files in the corpus.

    Args:
        corpus_path: Path to the corpus directory (default: /app/corpus)
        year: Filter by year (optional)
        month: Filter by month 1-12 (optional)

    Returns:
        Dictionary with file list and count. If exact match returns no files
        but the year has other months available, includes suggestions.
    """
    corpus = Path(corpus_path)
    if not corpus.exists():
        return {"error": f"Corpus path not found: {corpus_path}", "files": [], "count": 0}

    all_files = sorted(corpus.glob("treasury_bulletin_*.txt"))

    files = all_files
    if year is not None:
        files = [f for f in files if len(f.stem.split("_")) > 2 and f.stem.split("_")[2] == str(year)]
    if month is not None:
        month_str = f"{month:02d}"
        files = [f for f in files if len(f.stem.split("_")) > 3 and f.stem.split("_")[3] == month_str]

    result: dict[str, Any] = {
        "corpus_path": str(corpus),
        "files": [f.name for f in files],
        "count": len(files),
    }

    # If no exact match but year was specified, suggest available months
    if not files and year is not None:
        year_files = [
            f for f in all_files
            if len(f.stem.split("_")) > 2 and f.stem.split("_")[2] == str(year)
        ]
        if year_files:
            result["suggestions"] = [f.name for f in year_files]
            result["suggestion_note"] = (
                f"No exact match for year={year}"
                + (f", month={month}" if month is not None else "")
                + f". Available files for {year} listed in 'suggestions'."
            )

    return result


@mcp.tool()
def extract_tables_from_bulletin(
    filename: str,
    corpus_path: str = DEFAULT_CORPUS_PATH,
) -> dict[str, Any]:
    """Extract all tables from a specific Treasury Bulletin file.

    Args:
        filename: Name of the bulletin file (e.g., "treasury_bulletin_1941_01.txt")
        corpus_path: Path to the corpus directory (default: /app/corpus)

    Returns:
        Dictionary with extracted tables and metadata
    """
    file_path = Path(corpus_path) / filename
    if not file_path.exists():
        # Try to suggest similar files
        corpus = Path(corpus_path)
        similar = sorted(corpus.glob(f"treasury_bulletin_{filename.split('_')[2] if len(filename.split('_')) > 2 else '*'}*.txt"))
        suggestions = [f.name for f in similar[:10]]
        return {
            "error": f"File not found: {filename}",
            "tables": [],
            "count": 0,
            "suggestions": suggestions,
        }

    tables = _extract_tables_from_file(file_path)

    return {
        "filename": filename,
        "tables": tables,
        "count": len(tables),
    }


@mcp.tool()
def search_tables_for_value(
    search_term: str,
    corpus_path: str = DEFAULT_CORPUS_PATH,
    year: int | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """Search across all tables for rows containing a specific value or keyword.

    IMPORTANT: Always specify 'year' when possible to avoid scanning all 697 files.

    Args:
        search_term: Value or keyword to search for (case-insensitive)
        corpus_path: Path to the corpus directory (default: /app/corpus)
        year: Filter by year (optional but strongly recommended for performance)
        max_results: Maximum number of matching rows to return

    Returns:
        Dictionary with matching rows and their source files
    """
    corpus = Path(corpus_path)
    if not corpus.exists():
        return {"error": f"Corpus path not found: {corpus_path}", "matches": [], "count": 0}

    files = sorted(corpus.glob("treasury_bulletin_*.txt"))
    if year is not None:
        files = [f for f in files if len(f.stem.split("_")) > 2 and f.stem.split("_")[2] == str(year)]

    matches = []
    files_scanned = 0
    search_lower = search_term.lower()

    for file_path in files:
        files_scanned += 1
        tables = _extract_tables_from_file(file_path)
        for table in tables:
            for row in table["data"]:
                # Check if any cell contains the search term
                for key, value in row.items():
                    if search_lower in str(value).lower():
                        matches.append({
                            "filename": file_path.name,
                            "table_index": table["table_index"],
                            "context": table.get("context", ""),
                            "column": key,
                            "row": row,
                        })
                        if len(matches) >= max_results:
                            return {
                                "search_term": search_term,
                                "matches": matches,
                                "count": len(matches),
                                "files_scanned": files_scanned,
                                "truncated": True,
                            }
                        break  # Only one match per row

    return {
        "search_term": search_term,
        "matches": matches,
        "count": len(matches),
        "files_scanned": files_scanned,
        "truncated": False,
    }


@mcp.tool()
def get_row_by_label(
    filename: str,
    row_label: str,
    corpus_path: str = DEFAULT_CORPUS_PATH,
) -> dict[str, Any]:
    """Find a specific row by its label text across all tables in a file.

    This is the most direct way to look up a value: provide the filename
    and the row label (e.g., "Total capital", "Individual income taxes").
    Matching is case-insensitive and supports partial matches.

    Args:
        filename: Name of the bulletin file
        row_label: Text label of the row to find (partial match, case-insensitive)
        corpus_path: Path to the corpus directory

    Returns:
        Dictionary with all matching rows and their full column data
    """
    file_path = Path(corpus_path) / filename
    if not file_path.exists():
        return {"error": f"File not found: {filename}", "rows": []}

    tables = _extract_tables_from_file(file_path)
    label_lower = row_label.lower()

    results = []
    for table in tables:
        for row in table["data"]:
            # Check the first column (row label) for a match
            first_col_key = table["columns"][0] if table["columns"] else None
            if first_col_key and label_lower in str(row.get(first_col_key, "")).lower():
                results.append({
                    "table_index": table["table_index"],
                    "context": table.get("context", ""),
                    "columns": table["columns"],
                    "row": row,
                })
            else:
                # Also check all cells in case the label is in a non-first column
                for key, value in row.items():
                    if label_lower in str(value).lower():
                        results.append({
                            "table_index": table["table_index"],
                            "context": table.get("context", ""),
                            "columns": table["columns"],
                            "row": row,
                            "matched_column": key,
                        })
                        break

    return {
        "filename": filename,
        "search_label": row_label,
        "rows": results,
        "count": len(results),
    }


@mcp.tool()
def extract_numeric_column(
    filename: str,
    column_name: str,
    corpus_path: str = DEFAULT_CORPUS_PATH,
) -> dict[str, Any]:
    """Extract a specific numeric column from all tables in a bulletin.

    Args:
        filename: Name of the bulletin file
        column_name: Name of the column to extract (partial match, case-insensitive)
        corpus_path: Path to the corpus directory

    Returns:
        Dictionary with extracted values (including row labels) and statistics
    """
    file_path = Path(corpus_path) / filename
    if not file_path.exists():
        return {"error": f"File not found: {filename}", "values": []}

    tables = _extract_tables_from_file(file_path)

    values = []
    column_lower = column_name.lower()

    for table in tables:
        # Identify the label column (first column)
        label_key = table["columns"][0] if table["columns"] else None

        for row in table["data"]:
            for key, value in row.items():
                if column_lower in key.lower():
                    # Try to extract numeric value
                    try:
                        # Remove commas, parentheses (negative), and parse
                        numeric_str = str(value).replace(",", "").strip()
                        is_negative = False
                        if numeric_str.startswith("(") and numeric_str.endswith(")"):
                            numeric_str = numeric_str[1:-1]
                            is_negative = True
                        if numeric_str and numeric_str not in ["-", "n/a", "n.a.", ""]:
                            numeric_val = float(numeric_str)
                            if is_negative:
                                numeric_val = -numeric_val
                            values.append({
                                "row_label": row.get(label_key, "") if label_key else "",
                                "original_value": value,
                                "numeric_value": numeric_val,
                                "column": key,
                                "table_index": table["table_index"],
                            })
                    except ValueError:
                        pass

    # Calculate statistics
    numeric_vals = [v["numeric_value"] for v in values]
    stats = {}
    if numeric_vals:
        stats = {
            "count": len(numeric_vals),
            "sum": sum(numeric_vals),
            "mean": sum(numeric_vals) / len(numeric_vals),
            "min": min(numeric_vals),
            "max": max(numeric_vals),
        }

    return {
        "filename": filename,
        "column_search": column_name,
        "values": values,
        "statistics": stats,
    }


@mcp.tool()
def compute_percent_change(
    value1: float,
    value2: float,
) -> dict[str, Any]:
    """Compute the percent change between two values.

    Args:
        value1: Initial value (older)
        value2: Final value (newer)

    Returns:
        Dictionary with absolute difference and percent change
    """
    if value1 == 0:
        return {
            "error": "Cannot compute percent change when initial value is zero",
            "value1": value1,
            "value2": value2,
        }

    absolute_diff = value2 - value1
    percent_change = (absolute_diff / abs(value1)) * 100

    return {
        "value1": value1,
        "value2": value2,
        "absolute_difference": absolute_diff,
        "percent_change": percent_change,
        "percent_change_formatted": f"{percent_change:.4f}%",
    }


if __name__ == "__main__":
    mcp.run()
