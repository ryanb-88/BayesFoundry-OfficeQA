#!/usr/bin/env python3
"""
Enhanced Skill loader v2 for OfficeQA agent.

Improvements over v1:
  - Priority scoring (most relevant skills first)
  - Multi-word phrase matching (not just single keywords)
  - Always loads external-knowledge (critical edge cases)
  - Prints a summary header showing what was loaded and why

Usage:
    python3 skill_loader.py "ESF capital balance sheet regression"
    echo "question text" | python3 skill_loader.py
"""

import sys
import re
from pathlib import Path

SKILLS_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Skill index — keywords that trigger each skill file
# priority: higher = loaded first; keywords with * prefix are high-confidence
# ---------------------------------------------------------------------------
SKILL_INDEX = [
    {
        "name": "external-knowledge",
        "desc": "ESF balance sheet, FO-1 calendar-year timing, gold bloc countries, Treasury glossary",
        "keywords": [
            "*esf", "*exchange stabilization", "*total capital", "*nominal capital",
            "*appropriated capital", "*cumulative net income", "*fo-1", "*gross obligations",
            "*gold bloc", "*gold standard", "*bretton woods", "*sdr", "*imf",
            "*oasi", "*hhi", "*trust fund balance", "as of",
        ],
        "default": True,
        "priority": 10,
    },
    {
        "name": "fiscal-year-dates",
        "desc": "Fiscal year rules: ends June 30 pre-1977, Sep 30 post-1977, Transition Quarter",
        "keywords": [
            "*fiscal year", "*fiscal month", "fy", "*calendar year", "cy",
            "*transition quarter", "tq", "june 30", "september 30",
            "annual", "year-end", "end of fiscal",
        ],
        "default": False,
        "priority": 9,
    },
    {
        "name": "corpus-structure",
        "desc": "File layout, T-bills by type (PDO-1/PDO-2 warning), table format rules",
        "keywords": [
            "*t-bill", "*treasury bill", "*bill outstanding", "*pdo", "*pdo-1", "*pdo-2",
            "*regular weekly", "*tax anticipation", "annual maturing",
            "ownership of treasury", "bulletin file", "corpus",
        ],
        "default": False,
        "priority": 7,
    },
    {
        "name": "statistical-operations",
        "desc": "Regression (OLS), z-score, Gini, correlation, geometric mean, VaR, arc elasticity, Theil, IQR",
        "keywords": [
            "*regression", "*ols", "*z-score", "*z score", "*gini", "*correlation",
            "*geometric mean", "*standard deviation", "*variance", "*covariance",
            "*value at risk", "*var", "*arc elasticity", "*elasticity",
            "*theil", "*herfindahl", "*hhi", "*r-squared", "*coefficient",
            "*statistical", "normal distribution", "*unusual", "*significant",
            "*compound annual", "*cagr",
            "*h spread", "*h-spread", "*hspread", "*interquartile", "*iqr",
            "*quartile", "*median", "*percentile", "dispersion", "spread",
            "*skewness", "*kurtosis", "*entropy", "index of",
        ],
        "default": False,
        "priority": 8,
    },
    {
        "name": "table-types",
        "desc": "How to read FD-1, FFO-1, ESF-1, FO-1, IF-1, PDO table structures and column layouts",
        "keywords": [
            "*fd-1", "*fd-2", "*fd-3", "*fd-4", "*fd-5",
            "*ffo-1", "*esf-1", "*fo-1", "*if-1", "*if-2", "*pdo-1", "*pdo-2",
            "table structure", "column layout", "header row",
            "*summary of federal debt", "budget outlays", "*capital movements",
        ],
        "default": False,
        "priority": 6,
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
        "priority": 5,
    },
    {
        "name": "question-patterns",
        "desc": "Pattern recognition: percent change, YoY, multi-part bracket answers, list questions",
        "keywords": [
            "*percent change", "*percentage change", "*yoy", "*year over year",
            "*growth rate", "*compound", "list", "comma-separated list",
            "enclosed in square brackets", "output.*format", "report.*as",
            "*absolute difference", "multi-part",
        ],
        "default": False,
        "priority": 7,
    },
]


def match_skills(text: str) -> list[dict]:
    """Return list of skill entries whose keywords match the text, sorted by priority."""
    text_lower = text.lower()
    scored = []
    
    for skill in SKILL_INDEX:
        if skill.get("default"):
            scored.append((skill["priority"] + 100, skill, ["default"]))
            continue
        
        match_score = 0
        matched_keywords = []
        
        for kw in skill["keywords"]:
            # Strip priority marker
            is_high = kw.startswith("*")
            clean_kw = kw.lstrip("*")
            
            try:
                found = bool(re.search(clean_kw, text_lower))
            except re.error:
                found = clean_kw in text_lower
            
            if found:
                match_score += 3 if is_high else 1
                matched_keywords.append(clean_kw)
        
        if match_score > 0:
            scored.append((skill["priority"] + match_score, skill, matched_keywords))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(s, kws) for _, s, kws in scored]


def load_content(skills_with_reasons: list) -> str:
    sections = []
    for skill, matched_kws in skills_with_reasons:
        path = SKILLS_DIR / skill["name"] / "SKILL.md"
        if path.exists():
            content = path.read_text().strip()
            reason = f"Matched: {', '.join(matched_kws[:3])}" if matched_kws != ["default"] else "Always loaded"
            sections.append(f"### SKILL: {skill['name']} ({reason})\n# {skill['desc']}\n\n{content}")
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
        sys.exit(1)

    matched = match_skills(text)
    names = [s["name"] for s, _ in matched]
    
    print(f"# Loaded {len(matched)} skills: {', '.join(names)}\n")
    for skill, kws in matched:
        reason = "always" if kws == ["default"] else f"matched: {', '.join(kws[:3])}"
        print(f"#   - {skill['name']} ({reason})")
    print()
    print(load_content(matched))


if __name__ == "__main__":
    main()
