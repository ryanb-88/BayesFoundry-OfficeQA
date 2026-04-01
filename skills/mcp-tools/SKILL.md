---
name: mcp-tools
description: Guide for using the two remote MCP tool servers available to the agent — mcpcalc (300+ calculators, CAS, statistics, finance) and math-learning (math operations, statistics).
---
# MCP Tools Guide

You have two remote MCP tool servers available. Use them to avoid implementing calculations from scratch.

## When to Use MCP Tools vs Built-in Tools

| Task | Use MCP Tool | Use Built-in (bash/grep/read/python3) |
|------|-------------|---------------------------------------|
| Find data in corpus | ❌ | ✅ grep + read |
| Extract table values | ❌ | ✅ grep + awk |
| Arithmetic / expressions | ✅ mcpcalc `calculate` | ✅ python3 (simple cases) |
| Statistics (mean, std, regression) | ✅ mcpcalc or math-learning | ✅ python3 statistics module |
| Financial math (NPV, IRR, CAGR) | ✅ mcpcalc `calculate` with finance calculators | ✅ python3 |
| Symbolic algebra / calculus | ✅ mcpcalc CAS session | Only if MCP unavailable |
| HP filter / signal processing | ⚠️ Try mcpcalc CAS | ✅ python3 with scipy (apt-get) |
| Currency conversion / exchange rates | ✅ currency-conversion `convert_currency` or `get_historical_rates` | Only if MCP unavailable |
| Write answer.txt | ❌ | ✅ write tool |

**Rule:** Prefer MCP tools for complex calculations. For simple arithmetic, python3 is fine. Always fall back to Python if MCP tools are unavailable or return errors.

---

## 1. mcpcalc (MCPCalc — Remote Hosted)

**URL:** `https://mcpcalc.com/api/v1/mcp`
**Auth:** None required (free, open)
**Purpose:** 300+ calculators including a full CAS, spreadsheet engine, statistics, finance, and more.

### Available Tools

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
- **health** — BMI, BMR, TDEE, etc.
- **construction** — Concrete, lumber, electrical, etc.

### Quick Usage — Direct Calculation

For simple calculations, use `calculate` directly:
```
Tool: calculate
Args: { calculator: "mean", inputs: { values: [18120, 19539, 20205, 21461, 22680, 26900] } }
```

For percent change:
```
Tool: calculate
Args: { calculator: "percentage_change", inputs: { old_value: 528, new_value: 693 } }
```

### Advanced Usage — CAS Session

For symbolic math, multi-step calculations, or anything not covered by a specific calculator:

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

### Advanced Usage — Spreadsheet Session

For tabular data and formulas:

1. `create_session` with `calculator: "spreadsheet"` → get session_id
2. `push_session_action` to set cells:
   ```json
   { "actions": [
     { "type": "set_cells", "cells": { "A1": "Year", "B1": "Value", "A2": 2015, "B2": 18120 } },
     { "type": "set_cells", "cells": { "B7": "=AVERAGE(B2:B6)" } }
   ]}
   ```
3. `get_session_state` → read computed values

### Key Calculators for Treasury QA

| Calculator Slug | Use For |
|----------------|---------|
| `mean` | Average of a series |
| `standard_deviation` | Std dev of a series |
| `percentage_change` | Percent change between two values |
| `compound_interest` | CAGR-style calculations |
| `regression` | Linear/polynomial/exponential regression |
| `normal_distribution` | Z-scores, percentiles |
| `cas` | General symbolic/numeric math (session-based) |
| `spreadsheet` | Tabular calculations (session-based) |

---

## 2. math-learning (Math Learning — Remote Hosted)

**URL:** `https://math-mcp.fastmcp.app/mcp`
**Auth:** None required (free, open)
**Purpose:** Mathematical operations, statistics, and data visualization.

Use this as an alternative to mcpcalc for basic math and statistics. Call its tools for arithmetic, descriptive statistics, and data analysis.

---

## 3. currency-conversion (Wes Bos / Frankfurter API — Remote Hosted)

**URL:** `https://currency-mcp.wesbos.com/sse`
**Auth:** None required (free, open)
**Purpose:** Real-time and historical foreign exchange rates backed by ECB reference rates.

### Available Tools

| Tool | Purpose |
|------|---------|
| `convert_currency` | Convert an amount from one currency to another at the current rate |
| `get_latest_rates` | Fetch the latest exchange rates for a base currency |
| `get_historical_rates` | Get exchange rates for a specific historical date |
| `get_currencies` | List all supported currency codes and names |

### Usage

**Convert a dollar amount to another currency:**
```
Tool: convert_currency
Args: { from: "USD", to: "JPY", amount: 6275000000 }
```

**Get the exchange rate for a specific date:**
```
Tool: get_historical_rates
Args: { date: "2025-03-31", base: "USD", symbols: "JPY" }
```
Returns the USD/JPY rate for that date. Then multiply: `dollar_amount × rate = foreign_amount`.

**Get latest rates:**
```
Tool: get_latest_rates
Args: { base: "USD", symbols: "EUR,GBP,JPY" }
```

### When to Use

Use `currency-conversion` when a question asks to:
- Convert a dollar amount to a foreign currency (or vice versa)
- Look up an exchange rate for a specific date
- Compare values across currencies

⚠️ **Always use `get_historical_rates` with the specific date from the question.** Only use `get_latest_rates` if the question explicitly asks for the current/latest rate.

⚠️ **The Frankfurter API uses ECB reference rates.** If a question specifies a different rate source (e.g., "using Macrotrends data"), the ECB rate is a reasonable approximation but may differ slightly. Note this in your reasoning.

---

## Workflow: Combining MCP Tools with Built-in Tools

The typical workflow for a calculation question:

1. **Extract data**: Use `bash`/`grep`/`read` to find and extract values from the corpus
2. **Compute**: Use mcpcalc `calculate` or CAS session for the calculation
3. **Verify**: Re-extract data and re-compute (self-consistency check)
4. **Write answer**: Use `write` to save to `/app/answer.txt`

---

## Fallback Strategy

If an MCP tool fails or is unavailable:
1. Try the other MCP server (mcpcalc ↔ math-learning)
2. If both fail, use `apt-get install -y python3-numpy python3-scipy 2>/dev/null || true` and write a Python script
3. If apt fails, use the pure-Python implementations from the python-calculations skill
4. **Always write answer.txt** — even a partial answer is better than no answer
