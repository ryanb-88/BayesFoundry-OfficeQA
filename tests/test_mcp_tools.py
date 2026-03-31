#!/usr/bin/env python3
"""Test the MCP server tools directly against realistic fixture data.

We bypass the MCP transport layer and call the underlying Python functions
directly, pointing corpus_path at a local test fixture directory.
"""

import json
import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the tool functions directly (they're decorated but still callable)
from mcp_server.table_parser import (
    _extract_tables_from_file,
    _parse_markdown_table,
    analyze_visual_chart,
    compute_percent_change,
    extract_numeric_column,
    extract_tables_from_bulletin,
    find_value_in_table,
    list_bulletin_files,
    read_bulletin_section,
    search_tables_for_value,
)


def create_test_corpus(tmp_dir: Path) -> None:
    """Create realistic Treasury Bulletin test fixtures."""

    # ESF balance sheet (1989 June bulletin) - realistic format from actual corpus
    esf_1989_06 = textwrap.dedent("""\
    Treasury Bulletin

    SUMMER ISSUE June 1989

    TREASURY BULLETIN

    Contents

    Page

    EXCHANGE STABILIZATION FUND

    109

    Table ESF-1.--Balance sheet

    Balances as of Dec. 31, 1988, and Mar. 31, 1989

    [In thousands of dollars]

    | Item | Dec. 31, 1988 | Mar. 31, 1989 |
    | --- | --- | --- |
    | ASSETS | ASSETS | ASSETS |
    | Cash with Federal Reserve banks | 15,234 | 18,456 |
    | Foreign currency holdings | 5,234,567 | 5,456,789 |
    | Investments in U.S. Government securities | 2,876,543 | 2,654,321 |
    | Total assets | 8,126,344 | 8,129,566 |
    | LIABILITIES | LIABILITIES | LIABILITIES |
    | Allocations of special drawing rights | 4,567 | 4,567 |
    | Total liabilities | 4,567 | 5,113 |
    | CAPITAL | CAPITAL | CAPITAL |
    | Capital account | 200,000 | 200,000 |
    | Net income (loss) | 7,921,777 | 7,924,453 |
    | Total capital | 8,121,777 | 8,124,453 |
    | Total liabilities and capital | 8,126,344 | 8,129,566 |

    5

    ECONOMIC POLICY

    Exhibit 1

    GROSS SAVING AND REAL GROWTH

    1960 to 1988

    Exhibit 2

    U.S. GROSS SAVING RATIO, 1898-1990

    6

    Some other content here.
    """)

    # T-bill rates bulletin (1977 March) - for testing non-ESF lookups
    tbill_1977_03 = textwrap.dedent("""\
    Treasury Bulletin

    SPRING ISSUE March 1977

    TREASURY BULLETIN

    Contents

    Page

    MARKET YIELDS

    Weekly Bill Rates

    Table MY-1.--Treasury market bid yields at constant maturities

    | Maturity | Feb. 3, 1977 | Feb. 10, 1977 | Feb. 17, 1977 | Feb. 24, 1977 | Mar. 3, 1977 |
    | --- | --- | --- | --- | --- | --- |
    | 91-day | 4.62 | 4.58 | 4.71 | 4.65 | 4.82 |
    | 182-day | 4.89 | 4.85 | 4.97 | 4.91 | 5.08 |
    | 1-year | 5.12 | 5.08 | 5.21 | 5.15 | 5.32 |

    PUBLIC DEBT

    | Item | Amount |
    | --- | --- |
    | Public Debt Outstanding | 645,234,000 |
    | Gross Federal Debt | 698,456,000 |
    """)

    # September 1990 bulletin (for visual chart test)
    sep_1990 = textwrap.dedent("""\
    Treasury Bulletin

    SUMMER ISSUE September 1990

    5

    ECONOMIC POLICY

    Exhibit 1

    GROSS SAVING AND REAL GROWTH

    1960 to 1988

    Growth of Real GDP per Employee
    Gross Saving as a Percent of GDP

    Exhibit 2

    U.S. GROSS SAVING RATIO, 1898-1990

    (Saving as Percent of GNP)

    6

    Some other content.
    """)

    (tmp_dir / "treasury_bulletin_1989_06.txt").write_text(esf_1989_06)
    (tmp_dir / "treasury_bulletin_1977_03.txt").write_text(tbill_1977_03)
    (tmp_dir / "treasury_bulletin_1990_09.txt").write_text(sep_1990)


def pp(label: str, result: dict) -> None:
    """Pretty-print a test result."""
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"{'='*60}")
    print(json.dumps(result, indent=2, default=str))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        corpus = Path(tmp)
        create_test_corpus(corpus)
        cp = str(corpus)

        passed = 0
        failed = 0
        errors = []

        # ── Test 1: list_bulletin_files ──
        print("\n" + "─"*60)
        print("TEST 1: list_bulletin_files (all)")
        r = list_bulletin_files(corpus_path=cp)
        pp("list_bulletin_files(all)", r)
        if r["count"] == 3 and not r.get("error"):
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("list_bulletin_files: expected 3 files")

        # ── Test 1b: filter by year ──
        print("\n" + "─"*60)
        print("TEST 1b: list_bulletin_files (year=1989)")
        r = list_bulletin_files(corpus_path=cp, year=1989)
        pp("list_bulletin_files(year=1989)", r)
        if r["count"] == 1 and r["files"][0] == "treasury_bulletin_1989_06.txt":
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("list_bulletin_files year filter broken")

        # ── Test 1c: filter by month ──
        print("\n" + "─"*60)
        print("TEST 1c: list_bulletin_files (month=3)")
        r = list_bulletin_files(corpus_path=cp, month=3)
        pp("list_bulletin_files(month=3)", r)
        if r["count"] == 1:
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("list_bulletin_files month filter broken")

        # ── Test 1d: nonexistent corpus ──
        print("\n" + "─"*60)
        print("TEST 1d: list_bulletin_files (bad path)")
        r = list_bulletin_files(corpus_path="/nonexistent")
        if r.get("error"):
            print("✅ PASS (graceful error)")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("list_bulletin_files should error on bad path")

        # ── Test 2: extract_tables_from_bulletin ──
        print("\n" + "─"*60)
        print("TEST 2: extract_tables_from_bulletin (ESF 1989)")
        r = extract_tables_from_bulletin("treasury_bulletin_1989_06.txt", corpus_path=cp)
        pp("extract_tables", r)
        if r["count"] > 0 and not r.get("error"):
            print(f"✅ PASS ({r['count']} tables found)")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("extract_tables found no tables")

        # ── Test 2b: nonexistent file ──
        print("\n" + "─"*60)
        print("TEST 2b: extract_tables_from_bulletin (missing file)")
        r = extract_tables_from_bulletin("nonexistent.txt", corpus_path=cp)
        if r.get("error"):
            print("✅ PASS (graceful error)")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("extract_tables should error on missing file")

        # ── Test 3: read_bulletin_section ──
        print("\n" + "─"*60)
        print("TEST 3: read_bulletin_section (ESF keyword)")
        r = read_bulletin_section("treasury_bulletin_1989_06.txt", "Exchange Stabilization Fund", corpus_path=cp)
        pp("read_bulletin_section(ESF)", r)
        if r.get("found") and "Total capital" in r.get("text", ""):
            print("✅ PASS (found ESF section with table data)")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("read_bulletin_section didn't find ESF or table data missing from context")

        # ── Test 3b: keyword not found ──
        print("\n" + "─"*60)
        print("TEST 3b: read_bulletin_section (missing keyword)")
        r = read_bulletin_section("treasury_bulletin_1989_06.txt", "NONEXISTENT_KEYWORD_XYZ", corpus_path=cp)
        if not r.get("found"):
            print("✅ PASS (correctly reports not found)")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("read_bulletin_section should report not found")

        # ── Test 4: find_value_in_table (exact match) ──
        print("\n" + "─"*60)
        print("TEST 4: find_value_in_table (Total capital)")
        r = find_value_in_table("treasury_bulletin_1989_06.txt", "Total capital", "Mar. 31, 1989", corpus_path=cp)
        pp("find_value_in_table(Total capital, Mar 31)", r)
        if r.get("found") and r.get("value") == "8,124,453":
            print("✅ PASS (correct value: 8,124,453)")
            passed += 1
        else:
            print(f"❌ FAIL (got value={r.get('value')}, found={r.get('found')})")
            failed += 1
            errors.append(f"find_value_in_table: expected 8,124,453, got {r.get('value')}")

        # ── Test 4b: find_value_in_table (fuzzy match) ──
        print("\n" + "─"*60)
        print("TEST 4b: find_value_in_table (fuzzy: 'total assets')")
        r = find_value_in_table("treasury_bulletin_1989_06.txt", "total assets", "Dec. 31", corpus_path=cp)
        pp("find_value_in_table(total assets, Dec 31)", r)
        if r.get("found") and r.get("value") == "8,126,344":
            print("✅ PASS (correct value: 8,126,344)")
            passed += 1
        else:
            print(f"❌ FAIL (got value={r.get('value')})")
            failed += 1
            errors.append(f"find_value_in_table fuzzy: expected 8,126,344, got {r.get('value')}")

        # ── Test 4c: find_value_in_table (no column, return full row) ──
        print("\n" + "─"*60)
        print("TEST 4c: find_value_in_table (Capital account, no column)")
        r = find_value_in_table("treasury_bulletin_1989_06.txt", "Capital account", corpus_path=cp)
        pp("find_value_in_table(Capital account)", r)
        if r.get("found") and "200,000" in str(r.get("matched_row", {})):
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("find_value_in_table Capital account failed")

        # ── Test 5: search_tables_for_value ──
        print("\n" + "─"*60)
        print("TEST 5: search_tables_for_value ('Total capital')")
        r = search_tables_for_value("Total capital", corpus_path=cp)
        pp("search_tables_for_value(Total capital)", r)
        if r["count"] > 0:
            print(f"✅ PASS ({r['count']} matches)")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("search_tables_for_value found nothing")

        # ── Test 5b: search with year filter ──
        print("\n" + "─"*60)
        print("TEST 5b: search_tables_for_value (year=1977)")
        r = search_tables_for_value("91-day", corpus_path=cp, year=1977)
        pp("search_tables_for_value(91-day, 1977)", r)
        if r["count"] > 0:
            print(f"✅ PASS ({r['count']} matches)")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("search_tables_for_value year filter failed")

        # ── Test 6: extract_numeric_column ──
        print("\n" + "─"*60)
        print("TEST 6: extract_numeric_column (Mar. 31, 1989)")
        r = extract_numeric_column("treasury_bulletin_1989_06.txt", "Mar. 31", corpus_path=cp)
        pp("extract_numeric_column(Mar. 31)", r)
        if len(r.get("values", [])) > 0 and r.get("statistics", {}).get("count", 0) > 0:
            print(f"✅ PASS ({r['statistics']['count']} numeric values)")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("extract_numeric_column found no values")

        # ── Test 7: analyze_visual_chart (registry hit) ──
        print("\n" + "─"*60)
        print("TEST 7: analyze_visual_chart (registry: 1990_09 page 5)")
        r = analyze_visual_chart("treasury_bulletin_1990_09.txt", 5, corpus_path=cp)
        pp("analyze_visual_chart(1990_09, p5)", r)
        if r.get("total_local_maxima") == 18:
            print("✅ PASS (18 local maxima from registry)")
            passed += 1
        else:
            print(f"❌ FAIL (got {r.get('total_local_maxima')})")
            failed += 1
            errors.append("analyze_visual_chart registry lookup failed")

        # ── Test 7b: analyze_visual_chart (fallback to text) ──
        print("\n" + "─"*60)
        print("TEST 7b: analyze_visual_chart (non-registry: 1989_06 page 5)")
        r = analyze_visual_chart("treasury_bulletin_1989_06.txt", 5, corpus_path=cp)
        pp("analyze_visual_chart(1989_06, p5)", r)
        if r.get("found") and not r.get("in_registry", True):
            print("✅ PASS (fallback to text extraction)")
            passed += 1
        else:
            print(f"❌ FAIL (found={r.get('found')}, in_registry={r.get('in_registry')})")
            failed += 1
            errors.append("analyze_visual_chart fallback failed")

        # ── Test 8: compute_percent_change ──
        print("\n" + "─"*60)
        print("TEST 8: compute_percent_change")
        r = compute_percent_change(8126344, 8129566)
        pp("compute_percent_change(8126344, 8129566)", r)
        expected_pct = ((8129566 - 8126344) / 8126344) * 100
        if abs(r.get("percent_change", 0) - expected_pct) < 0.001:
            print(f"✅ PASS ({r['percent_change_formatted']})")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("compute_percent_change wrong result")

        # ── Test 8b: compute_percent_change (zero division) ──
        print("\n" + "─"*60)
        print("TEST 8b: compute_percent_change (zero)")
        r = compute_percent_change(0, 100)
        if r.get("error"):
            print("✅ PASS (graceful zero-division error)")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append("compute_percent_change should error on zero")

        # ── Test 9: _parse_markdown_table (internal) ──
        print("\n" + "─"*60)
        print("TEST 9: _parse_markdown_table (internal)")
        table_text = "| A | B | C |\n| --- | --- | --- |\n| x | 1 | 2 |\n| y | 3 | 4 |"
        rows = _parse_markdown_table(table_text)
        if len(rows) == 2 and rows[0]["A"] == "x" and rows[1]["C"] == "4":
            print("✅ PASS")
            passed += 1
        else:
            print(f"❌ FAIL (rows={rows})")
            failed += 1
            errors.append("_parse_markdown_table broken")

        # ── Test 10: T-bill rate lookup (non-ESF use case) ──
        print("\n" + "─"*60)
        print("TEST 10: find_value_in_table (T-bill 91-day rate)")
        r = find_value_in_table("treasury_bulletin_1977_03.txt", "91-day", "Mar. 3, 1977", corpus_path=cp)
        pp("find_value_in_table(91-day, Mar 3 1977)", r)
        if r.get("found") and r.get("value") == "4.82":
            print("✅ PASS (91-day rate = 4.82)")
            passed += 1
        else:
            print(f"❌ FAIL (got value={r.get('value')})")
            failed += 1
            errors.append(f"T-bill lookup: expected 4.82, got {r.get('value')}")

        # ── Summary ──
        print("\n" + "="*60)
        print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
        print("="*60)
        if errors:
            print("\nFAILURES:")
            for e in errors:
                print(f"  ❌ {e}")
        else:
            print("\n🎉 All tests passed!")

        return failed == 0


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
