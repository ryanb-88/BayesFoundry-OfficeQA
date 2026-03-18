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

    # Parse header row
    header_line = lines[0]
    headers = [cell.strip() for cell in header_line.split("|") if cell.strip()]

    # Skip separator line (e.g., |---|---|---|)
    data_lines = lines[2:] if len(lines) > 2 and re.match(r"^\|[\s\-:|]+\|?$", lines[1]) else lines[1:]

    rows = []
    for line in data_lines:
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        if cells:
            row = {}
            for i, cell in enumerate(cells):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row[key] = cell
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
    # Use finditer with a pattern that matches one or more table rows
    table_pattern = r"((?:\|[^\n]+\|\n?)+)"
    table_matches = re.finditer(table_pattern, content)

    tables = []
    for i, match in enumerate(table_matches):
        table_text = match.group(1)
        rows = _parse_markdown_table(table_text)
        if rows:
            tables.append({
                "table_index": i,
                "row_count": len(rows),
                "columns": list(rows[0].keys()) if rows else [],
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
        Dictionary with file list and count
    """
    corpus = Path(corpus_path)
    if not corpus.exists():
        return {"error": f"Corpus path not found: {corpus_path}", "files": [], "count": 0}

    files = sorted(corpus.glob("treasury_bulletin_*.txt"))

    # Apply filters
    if year is not None:
        files = [f for f in files if f.stem.split("_")[2] == str(year)]
    if month is not None:
        files = [f for f in files if f.stem.split("_")[3] == f"{month:02d}"]

    return {
        "corpus_path": str(corpus),
        "files": [f.name for f in files],
        "count": len(files),
    }


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
        return {"error": f"File not found: {filename}", "tables": [], "count": 0}

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

    Args:
        search_term: Value or keyword to search for (case-insensitive)
        corpus_path: Path to the corpus directory (default: /app/corpus)
        year: Filter by year (optional)
        max_results: Maximum number of matching rows to return

    Returns:
        Dictionary with matching rows and their source files
    """
    corpus = Path(corpus_path)
    if not corpus.exists():
        return {"error": f"Corpus path not found: {corpus_path}", "matches": [], "count": 0}

    files = sorted(corpus.glob("treasury_bulletin_*.txt"))
    if year is not None:
        files = [f for f in files if f.stem.split("_")[2] == str(year)]

    matches = []
    search_lower = search_term.lower()

    for file_path in files:
        tables = _extract_tables_from_file(file_path)
        for table in tables:
            for row in table["data"]:
                # Check if any cell contains the search term
                for key, value in row.items():
                    if search_lower in str(value).lower():
                        matches.append({
                            "filename": file_path.name,
                            "table_index": table["table_index"],
                            "column": key,
                            "row": row,
                        })
                        if len(matches) >= max_results:
                            return {
                                "search_term": search_term,
                                "matches": matches,
                                "count": len(matches),
                                "truncated": True,
                            }
                        break  # Only one match per row

    return {
        "search_term": search_term,
        "matches": matches,
        "count": len(matches),
        "truncated": False,
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
        column_name: Name of the column to extract (partial match)
        corpus_path: Path to the corpus directory

    Returns:
        Dictionary with extracted values and statistics
    """
    file_path = Path(corpus_path) / filename
    if not file_path.exists():
        return {"error": f"File not found: {filename}", "values": []}

    tables = _extract_tables_from_file(file_path)

    values = []
    column_lower = column_name.lower()

    for table in tables:
        for row in table["data"]:
            for key, value in row.items():
                if column_lower in key.lower():
                    # Try to extract numeric value
                    try:
                        # Remove commas and parse
                        numeric_str = str(value).replace(",", "").strip()
                        if numeric_str and numeric_str not in ["-", "n/a", ""]:
                            numeric_val = float(numeric_str)
                            values.append({
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
        "percent_change_formatted": f"{percent_change:.2f}%",
    }


if __name__ == "__main__":
    mcp.run()
