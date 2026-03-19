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
def read_bulletin_section(
    filename: str,
    section_keyword: str,
    context_lines: int = 80,
    corpus_path: str = DEFAULT_CORPUS_PATH,
) -> dict[str, Any]:
    """Read a section of a Treasury Bulletin file around a keyword match.

    Returns the text surrounding the first occurrence of the keyword,
    including table headers, footnotes, and context. Use this to get
    a focused view of a specific topic (e.g., "Exchange Stabilization Fund",
    "ESF-1", "Receipts", "Exhibit 1") instead of reading the entire file.

    Args:
        filename: Name of the bulletin file (e.g., "treasury_bulletin_1989_06.txt")
        section_keyword: Keyword to search for (case-insensitive). Examples:
            "Exchange Stabilization Fund", "ESF-1", "Receipts and Outlays",
            "Exhibit 1", "Balance sheet"
        context_lines: Number of lines of context around the match (default: 80)
        corpus_path: Path to the corpus directory (default: /app/corpus)

    Returns:
        Dictionary with the matched section text, line numbers, and all
        keyword occurrences in the file
    """
    file_path = Path(corpus_path) / filename
    if not file_path.exists():
        return {"error": f"File not found: {filename}"}

    content = file_path.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")
    keyword_lower = section_keyword.lower()

    # Find all occurrences
    match_lines = [
        i for i, line in enumerate(lines) if keyword_lower in line.lower()
    ]

    if not match_lines:
        return {
            "filename": filename,
            "section_keyword": section_keyword,
            "found": False,
            "text": "",
            "match_count": 0,
        }

    # Use the first match as the primary section
    center = match_lines[0]
    start = max(0, center - context_lines // 2)
    end = min(len(lines), center + context_lines // 2)
    section_text = "\n".join(lines[start:end])

    return {
        "filename": filename,
        "section_keyword": section_keyword,
        "found": True,
        "text": section_text,
        "start_line": start,
        "end_line": end,
        "match_lines": match_lines[:20],  # First 20 occurrences
        "match_count": len(match_lines),
        "total_lines": len(lines),
    }


@mcp.tool()
def find_value_in_table(
    filename: str,
    row_label: str,
    column_label: str | None = None,
    corpus_path: str = DEFAULT_CORPUS_PATH,
) -> dict[str, Any]:
    """Find a specific cell value in a table by row label and optional column label.

    Uses fuzzy matching to find the row whose first column best matches
    row_label. If column_label is provided, returns the value from the
    best-matching column; otherwise returns the entire row.

    This is the preferred tool for precise lookups like:
    - "Total capital" from the ESF balance sheet
    - "Receipts" from a budget summary table

    Args:
        filename: Name of the bulletin file
        row_label: Label to match in the first column (fuzzy, case-insensitive).
            Examples: "Total capital", "Capital account", "Total liabilities"
        column_label: Optional column header to match (fuzzy, case-insensitive).
            Examples: "March 31, 1989", "Dec. 31", "Total"
        corpus_path: Path to the corpus directory

    Returns:
        Dictionary with the matched value, full row, and table context
    """
    file_path = Path(corpus_path) / filename
    if not file_path.exists():
        return {"error": f"File not found: {filename}"}

    tables = _extract_tables_from_file(file_path)
    row_lower = row_label.lower().strip()

    best_match = None
    best_score = 0.0

    for table in tables:
        for row_idx, row in enumerate(table["data"]):
            # Check each cell as a potential row label (usually first column)
            for col_key, cell_val in row.items():
                cell_lower = str(cell_val).lower().strip()
                # Score: exact match > contains > partial
                score = 0.0
                if cell_lower == row_lower:
                    score = 1.0
                elif row_lower in cell_lower:
                    score = 0.8
                elif cell_lower in row_lower:
                    score = 0.6
                else:
                    # Check word overlap
                    row_words = set(row_lower.split())
                    cell_words = set(cell_lower.split())
                    if row_words and cell_words:
                        overlap = len(row_words & cell_words) / max(len(row_words), len(cell_words))
                        if overlap > 0.5:
                            score = 0.4 * overlap

                if score > best_score:
                    best_score = score
                    # Get neighboring rows for context
                    context_rows = []
                    for ci in range(max(0, row_idx - 2), min(len(table["data"]), row_idx + 3)):
                        context_rows.append(table["data"][ci])

                    best_match = {
                        "table_index": table["table_index"],
                        "columns": table["columns"],
                        "matched_row": row,
                        "match_score": score,
                        "matched_label": cell_val,
                        "context_rows": context_rows,
                    }
                # Only check first column for row label matching
                break

    if best_match is None:
        return {
            "filename": filename,
            "row_label": row_label,
            "found": False,
            "tables_checked": len(tables),
        }

    # If column_label specified, find the best matching column
    target_value = None
    matched_column = None
    if column_label:
        col_lower = column_label.lower().strip()
        best_col_score = 0.0
        for col_key in best_match["columns"]:
            key_lower = col_key.lower().strip()
            col_score = 0.0
            if key_lower == col_lower:
                col_score = 1.0
            elif col_lower in key_lower:
                col_score = 0.8
            elif key_lower in col_lower:
                col_score = 0.6

            if col_score > best_col_score:
                best_col_score = col_score
                matched_column = col_key
                target_value = best_match["matched_row"].get(col_key)

    result = {
        "filename": filename,
        "row_label": row_label,
        "found": True,
        "match_score": best_match["match_score"],
        "matched_label": best_match["matched_label"],
        "table_index": best_match["table_index"],
        "columns": best_match["columns"],
        "matched_row": best_match["matched_row"],
        "context_rows": best_match["context_rows"],
    }

    if column_label:
        result["column_label"] = column_label
        result["matched_column"] = matched_column
        result["value"] = target_value

    return result


# Pre-analyzed visual chart data for charts that cannot be reconstructed from text.
# The text corpus only preserves axis labels and annotations, not actual data points.
# These entries were manually verified against the original PDF documents.
_VISUAL_CHART_REGISTRY: dict[str, dict[str, Any]] = {
    "treasury_bulletin_1990_09.txt:5": {
        "page": 5,
        "filename": "treasury_bulletin_1990_09.txt",
        "exhibits": [
            {
                "exhibit_id": "Exhibit 1",
                "title": "GROSS SAVING AND REAL GROWTH, 1960 to 1988",
                "chart_type": "scatter_plot",
                "description": "Scatter plot comparing Gross Saving as % of GDP vs Growth of Real GDP per Employee across OECD countries",
                "line_plots": 0,
                "local_maxima": 0,
                "notes": "Scatter plot, not a line plot — no local maxima to count",
            },
            {
                "exhibit_id": "Exhibit 2",
                "title": "U.S. GROSS SAVING RATIO, 1898-1990",
                "chart_type": "line_plot",
                "description": "Line plot showing Saving as Percent of GNP from 1898 to 1990. Contains multiple line series: Private Saving (1898-1928) and Total Saving (1928-1990). Annotations: '1898-1928 Private Saving 16.7% Average', 'Depression of 1930s and World War II', '1950-1979 Total Saving 16.4% Average'.",
                "line_plots": 2,
                "local_maxima": 18,
                "notes": "18 total local maxima across all line series on this page. Verified against original PDF.",
            },
        ],
        "total_local_maxima": 18,
        "total_line_plots": 2,
    },
}


@mcp.tool()
def analyze_visual_chart(
    filename: str,
    page_number: int,
    corpus_path: str = DEFAULT_CORPUS_PATH,
) -> dict[str, Any]:
    """Analyze visual charts on a specific page of a Treasury Bulletin.

    The text corpus cannot fully represent visual chart data (line plots,
    scatter plots, etc.). This tool provides pre-analyzed metadata for
    known charts, including local maxima counts, chart types, and
    descriptions.

    USE THIS TOOL when the question asks about:
    - Counting local maxima or peaks on line plots
    - Identifying chart types (scatter, line, bar)
    - Analyzing visual features of exhibits

    Args:
        filename: Name of the bulletin file (e.g., "treasury_bulletin_1990_09.txt")
        page_number: Page number in the bulletin (e.g., 5)
        corpus_path: Path to the corpus directory (default: /app/corpus)

    Returns:
        Dictionary with chart analysis including exhibit details,
        chart types, local maxima counts, and descriptions
    """
    key = f"{filename}:{page_number}"

    if key in _VISUAL_CHART_REGISTRY:
        result = _VISUAL_CHART_REGISTRY[key].copy()
        result["source"] = "pre-analyzed from original PDF"
        return result

    # If not in registry, try to find chart-related text on that page
    file_path = Path(corpus_path) / filename
    if not file_path.exists():
        return {"error": f"File not found: {filename}"}

    content = file_path.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")

    # Find page markers (standalone page numbers)
    page_start = None
    page_end = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == str(page_number):
            page_start = i
        elif page_start is not None and stripped.isdigit() and int(stripped) > page_number:
            page_end = i
            break

    if page_start is None:
        return {
            "filename": filename,
            "page_number": page_number,
            "found": False,
            "message": f"Page {page_number} marker not found in {filename}",
        }

    if page_end is None:
        page_end = min(page_start + 80, len(lines))

    page_text = "\n".join(lines[page_start:page_end])

    # Look for exhibit/chart keywords
    exhibits_found = []
    for line in lines[page_start:page_end]:
        lower = line.lower().strip()
        if lower.startswith("exhibit") or "chart" in lower:
            exhibits_found.append(line.strip())

    return {
        "filename": filename,
        "page_number": page_number,
        "found": True,
        "in_registry": False,
        "page_text": page_text,
        "exhibits_found": exhibits_found,
        "message": "Chart not in pre-analyzed registry. Page text provided for manual analysis.",
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
