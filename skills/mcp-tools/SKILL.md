---
name: mcp-tools
description: Detailed guide for using mcpcalc and math-learning MCP tool servers, including tool APIs, calculator categories, and session workflows.
---
# MCP Tools — Detailed API Reference

Refer to the main prompt for when to use MCP tools vs Python, the fallback strategy, and worked examples. This skill covers the detailed tool APIs and session workflows.

## mcpcalc Tools

| Tool | Purpose |
|------|---------|
| `list_calculators` | List available calculators, optionally filtered by category |
| `get_calculator_schema` | Get input schema for a specific calculator |
| `calculate` | Run a calculation and get results |
| `generate_prefilled_url` | Generate a shareable URL for a calculation |
| `create_session` | Create an interactive CAS or spreadsheet session |
| `push_session_action` | Submit expressions, set fields, plot functions in a session |
| `get_session_state` | Read results from a session |
| `close_session` | Close a session |

### Calculator Categories

- **math** — CAS, fractions, statistics, geometry, algebra (60+ calculators)
- **finance** — Mortgage, compound interest, NPV, IRR, CAGR, loan calculators (55+)

### Key Calculators for Treasury QA

| Slug | Use For |
|------|---------|
| `mean` | Average of a series |
| `standard_deviation` | Std dev of a series |
| `percentage_change` | Percent change between two values |
| `compound_interest` | CAGR-style calculations |
| `regression` | Linear/polynomial/exponential regression |
| `cas` | General symbolic/numeric math (session-based) |
| `spreadsheet` | Tabular calculations (session-based) |

### CAS Session Workflow

1. `create_session` with `calculator: "cas"` → get session_id
2. `push_session_action` with expressions:
   ```json
   { "session_id": "...", "actions": [
     { "type": "submit_expression", "expression": "diff(x^3 * sin(x), x)" }
   ]}
   ```
3. `get_session_state` → read computed results
4. `close_session` when done

**CAS supports:** symbolic algebra, calculus (derivatives, integrals, limits, series), equation solving, variable assignment, LaTeX input, symbolic and numeric modes.

### Spreadsheet Session Workflow

1. `create_session` with `calculator: "spreadsheet"` → get session_id
2. `push_session_action` to set cells:
   ```json
   { "actions": [
     { "type": "set_cells", "cells": { "A1": "Year", "B1": "Value", "A2": 2015, "B2": 18120 } },
     { "type": "set_cells", "cells": { "B7": "=AVERAGE(B2:B6)" } }
   ]}
   ```
3. `get_session_state` → read computed values

## math-learning

**Purpose:** Mathematical operations, statistics, and data visualization. Use as an alternative to mcpcalc for basic math and statistics.
