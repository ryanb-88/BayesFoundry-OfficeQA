#!/usr/bin/env python3
"""
Skill loader for OfficeQA agent.

Reads a question/keywords from stdin (or args), matches against skill index,
and prints the content of all relevant SKILL.md files.

Usage:
    echo "question text" | python3 skill_loader.py
    python3 skill_loader.py "ESF capital balance sheet regression"
"""

import sys
import re
from pathlib import Path

SKILLS_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Skill index — keywords that trigger each skill file
# Keep keywords lowercase; matching is case-insensitive substring search.
# ---------------------------------------------------------------------------
SKILL_INDEX = [
    {
        "name": "external-knowledge",
        "desc": "ESF balance sheet structure, FO-1 calendar-year timing, gold bloc countries, Treasury glossary",
        "keywords": [
            "esf", "exchange stabilization", "total capital", "nominal capital",
            "appropriated capital", "cumulative net income", "fo-1", "gross obligations",
            "gold bloc", "gold standard", "bretton woods", "sdr", "imf",
            "oasi", "hhi", "trust fund balance", "as of",
        ],
        # Always load this one — it has the most critical edge-case knowledge
        "default": True,
    },
    {
        "name": "fiscal-year-dates",
        "desc": "Fiscal year rules: ends June 30 pre-1977, Sep 30 post-1977, Transition Quarter",
        "keywords": [
            "fiscal year", "fiscal month", "fy", "calendar year", "cy",
            "transition quarter", "tq", "june 30", "september 30",
            "annual", "year-end", "end of fiscal",
        ],
        "default": False,
    },
    {
        "name": "corpus-structure",
        "desc": "File layout, T-bills by type (PDO-1/PDO-2 warning), table format rules",
        "keywords": [
            "t-bill", "treasury bill", "bill outstanding", "pdo", "pdo-1", "pdo-2",
            "regular weekly", "tax anticipation", "annual maturing",
            "ownership of treasury", "bulletin file", "corpus",
        ],
        "default": False,
    },
    {
        "name": "statistical-operations",
        "desc": "Regression (OLS), z-score, Gini, correlation, geometric mean, VaR, arc elasticity, Theil index, H-spread/IQR",
        "keywords": [
            "regression", "ols", "z-score", "z score", "gini", "correlation",
            "geometric mean", "standard deviation", "variance", "covariance",
            "value at risk", "var", "arc elasticity", "elasticity",
            "theil", "herfindahl", "hhi", "r-squared", "coefficient",
            "statistical", "normal distribution", "unusual", "significant",
            "compound annual", "cagr",
            "h spread", "h-spread", "hspread", "interquartile", "iqr",
            "quartile", "median", "percentile", "dispersion", "spread",
            "skewness", "kurtosis", "entropy", "index of",
        ],
        "default": False,
    },
    {
        "name": "table-types",
        "desc": "How to read FD-1, FFO-1, ESF-1, FO-1, IF-1, PDO table structures and column layouts",
        "keywords": [
            "fd-1", "fd-2", "fd-3", "fd-4", "fd-5",
            "ffo-1", "esf-1", "fo-1", "if-1", "if-2", "pdo-1", "pdo-2",
            "table structure", "column layout", "header row",
            "summary of federal debt", "budget outlays", "capital movements",
        ],
        "default": False,
    },
    {
        "name": "number-parsing",
        "desc": "Comma-separated thousands, unit conversions, rounding, negative values",
        "keywords": [
            "million", "billion", "thousand", "in millions", "in billions",
            "convert", "nominal", "real", "inflation", "cpi",
            "round to", "decimal place", "nearest",
        ],
        "default": False,
    },
    {
        "name": "question-patterns",
        "desc": "Pattern recognition: percent change, YoY growth, multi-part bracket answers, list questions",
        "keywords": [
            "percent change", "percentage change", "yoy", "year over year",
            "growth rate", "compound", "list", "comma-separated list",
            "enclosed in square brackets", "output.*format", "report.*as",
            "absolute difference", "multi-part",
        ],
        "default": False,
    },
]


def match_skills(text: str) -> list[dict]:
    """Return list of skill entries whose keywords match the text."""
    text_lower = text.lower()
    matched = []
    for skill in SKILL_INDEX:
        if skill.get("default"):
            matched.append(skill)
            continue
        for kw in skill["keywords"]:
            # Support simple regex patterns (e.g. "output.*format")
            try:
                if re.search(kw, text_lower):
                    matched.append(skill)
                    break
            except re.error:
                if kw in text_lower:
                    matched.append(skill)
                    break
    return matched


def load_content(skills: list[dict]) -> str:
    sections = []
    for skill in skills:
        path = SKILLS_DIR / skill["name"] / "SKILL.md"
        if path.exists():
            content = path.read_text().strip()
            sections.append(f"### SKILL: {skill['name']}\n# {skill['desc']}\n\n{content}")
        else:
            sections.append(f"### SKILL: {skill['name']} — file not found at {path}")
    return "\n\n---\n\n".join(sections)


def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("Usage: python3 skill_loader.py '<question or keywords>'")
        print("       echo '<question>' | python3 skill_loader.py")
        sys.exit(1)

    matched = match_skills(text)
    names = [s["name"] for s in matched]
    print(f"# Loaded skills: {', '.join(names)}\n")
    print(load_content(matched))


if __name__ == "__main__":
    main()
