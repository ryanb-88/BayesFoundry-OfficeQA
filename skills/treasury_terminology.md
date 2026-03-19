# U.S. Treasury Terminology Reference

## Exchange Stabilization Fund (ESF)

The Exchange Stabilization Fund was established under the Gold Reserve Act of 1934 to stabilize the exchange value of the dollar.

### Balance Sheet Structure

| Term | Definition | Notes |
|------|------------|-------|
| **Capital account** | Original $2B appropriated minus $1.8B transferred to IMF | ~$200 million (relatively fixed) |
| **Net income (loss)** | Cumulative profits/losses from SDR and forex operations | Varies widely |
| **Total capital** | Capital account + Net income (loss) | **This is "total capital held"** |
| **Total liabilities** | SDR certificates + SDR allocations + other liabilities | Varies |
| **Total liabilities and capital** | Sum of all liabilities plus total capital | Varies |

### Key Distinction

⚠️ **"Total nominal capital held" = "Total capital"**, NOT "Capital account"

- Capital account ≈ $200 million (the nominal/original appropriation)
- Total capital = much larger (includes accumulated earnings over decades)

When a question asks for "total capital" or "total nominal capital held", use the **Total capital** line item, which includes both the capital account and cumulative net income.

### ESF Table Types
- **ESF-1:** Balance sheet (assets, liabilities, capital)
- **ESF-2:** Income and expense statement

### Where to Find ESF Data
- Look for "Exchange Stabilization Fund" section
- Use `search_tables_for_value(search_term="Exchange Stabilization Fund", year=YYYY)`
- Or use `get_row_by_label(filename="...", row_label="Total capital")`
- Typically in mid-to-late year issues for quarterly data

---

## Budget and Fiscal Terms

### Fiscal Year — CRITICAL DISTINCTION

The U.S. fiscal year boundary **changed in 1977**:

| Period | Fiscal Year Start | Fiscal Year End | Example |
|--------|-------------------|-----------------|---------|
| **Pre-1977** | July 1 | June 30 | FY1976 = Jul 1975 – Jun 1976 |
| **Transition** | Jul 1, 1976 | Sep 30, 1976 | "Transition Quarter" (TQ) |
| **Post-1976** | October 1 | September 30 | FY2024 = Oct 2023 – Sep 2024 |

⚠️ Always check whether a question asks for **calendar year** or **fiscal year** data — they are NOT the same.

### Receipts and Outlays

| Term | Definition |
|------|------------|
| **Receipts** | Total government revenue (taxes, fees, etc.) |
| **Outlays** | Total government spending/expenditures |
| **Surplus** | Receipts > Outlays (positive value) |
| **Deficit** | Receipts < Outlays (negative value, sometimes in parentheses) |
| **Balance** | Receipts - Outlays |
| **Budget Authority** | Legal authority to incur financial obligations |
| **Off-budget** | Items excluded from unified budget totals (e.g., Social Security) |
| **Unified Budget** | Combined on-budget and off-budget totals |

### Dollar Types

| Type | Definition |
|------|------------|
| **Nominal dollars** | Face value, not adjusted for inflation |
| **Current dollars** | Same as nominal dollars |
| **Real dollars** | Adjusted for inflation (constant purchasing power) |

---

## Securities Terms

| Term | Definition |
|------|------------|
| **Marketable Securities** | Publicly traded (bills, notes, bonds) |
| **Nonmarketable Securities** | Not publicly traded (savings bonds, state/local series) |
| **Treasury Bills** | Short-term (≤1 year), sold at discount |
| **Treasury Notes** | Medium-term (2–10 years), semiannual coupon |
| **Treasury Bonds** | Long-term (>10 years), semiannual coupon |
| **Par Value** | Face value of a security (not market value) |

---

## Unit Conventions

Treasury data is typically reported in:
- **Thousands of dollars:** Most common (check column headers!)
- **Millions of dollars:** Some summary tables
- **Billions of dollars:** Rare, usually explicitly marked

### Conversion Examples

```
8,124,453 thousand  = 8,124.453 million = 8.124453 billion
200,000 thousand    = 200 million       = 0.200 billion
```

### Reading Table Values

- Values in parentheses `(1,234)` mean **negative** numbers
- `n.a.` or `—` means data not available
- Values may be revised in later bulletins — use the bulletin issue specified in the question
- Some tables show both calendar year and fiscal year data — verify which column you're reading

---

## Data Sources in Treasury Bulletins

### Where to Find Budget Data
- "Federal Finances" section
- Receipts and outlays tables
- September issues have full fiscal year data

### Historical Data
- September bulletins contain fiscal year summaries
- Multiple years of data may be needed for time series analysis
- Table of Contents appears at the front of each bulletin

### Report Pages vs PDF Pages
Some questions reference specific "report pages" — this means the page number printed on the document, NOT the PDF page number. These may differ due to front matter.
