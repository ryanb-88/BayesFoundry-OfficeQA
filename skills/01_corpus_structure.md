# Treasury Bulletin Corpus Structure

## File Layout
- Location: `/app/corpus/`
- 697 files: `treasury_bulletin_YYYY_MM.txt`
- Index listing: `/app/corpus/index.txt`
- Format: Markdown with pipe-delimited tables (`|col1|col2|`)
- Coverage: 1939–2025 (monthly until ~1996, then quarterly)

## Navigating to the Right File

The filename encodes the **publication date**, not the data date.
Data in a bulletin is usually 1–2 months behind publication:
- `treasury_bulletin_1954_02.txt` = February 1954 issue → contains full 1953 annual data

**Rule of thumb:**
| You need data for... | Look in bulletin from... |
|---|---|
| Calendar year 1953 totals | Early 1954 (Jan–Mar) |
| Fiscal year 1953 (pre-1977 FY ends June) | Late 1953 or early 1954 |
| Monthly data for March 1977 | March or April 1977 |
| Most recent revision of any value | The LATEST bulletin that covers that period |

## Common Table Types and Where to Find Them

| Data Type | Typical Section Heading | Key Search Terms |
|---|---|---|
| Federal receipts & expenditures | "Budget Receipts and Expenditures" | `receipts`, `expenditures`, `budget` |
| National defense spending | "National Defense" or under expenditures table | `national defense`, `defense and` |
| Public/gross debt | "Public Debt" or "Federal Debt" | `gross debt`, `public debt`, `outstanding` |
| Intergovernmental transfers | "Intergovernmental" | `intergovernmental`, `trust fund` |
| Treasury bills & rates | "Treasury Bills" | `91-day`, `182-day`, `weekly bills`, `discount rate` |
| T-bills outstanding by type | "Ownership of Treasury Bills" or "Treasury Bills Outstanding" | `regular weekly`, `tax anticipation`, `outstanding` — use table showing amounts as of a **specific date**, not maturity schedules |
| Exchange Stabilization Fund | "Exchange Stabilization Fund" | `ESF`, `exchange stabilization`, `gold` |
| Capital flows | "Capital Movements" | `capital movement`, `gold bloc`, `foreign` |
| Interest rates | "Market Yields" or "Interest Rates" | `bond rate`, `yield`, `coupon` |

## ⚠️ T-Bills Outstanding by TYPE (Regular Weekly vs Tax Anticipation)

**This is a common failure mode — read carefully.**

When the question asks for T-bills outstanding **by type** (regular weekly/annual vs tax anticipation) **as of a specific date**:

### ✅ Correct approach
1. Open the bulletin for the month AFTER the target date (e.g., Feb 1970 bulletin for Jan 31, 1970 data)
2. Search for: `grep -n "Ownership of Treasury Bills\|Outstanding.*Treasury bill\|regular weekly.*tax anticipation" bulletin.txt`
3. Look for a **snapshot table** with:
   - Rows for each T-bill type: `Regular weekly`, `Annual maturing`, `Tax anticipation`
   - A total column that matches the total bills in the Status Under Limitation table
   - The date (e.g., "January 31, 1970") in the table title or heading

### ❌ Wrong tables — do NOT use for outstanding balances
| Table | Why it's wrong |
|---|---|
| **PDO-1** "Maturity Schedule of Interest-Bearing Marketable Public Debt Securities Other than Regular Weekly and Annual Treasury Bills" | Shows bills that WILL MATURE on future dates — NOT current balances |
| **PDO-2** "Offerings of Bills" | Shows issuance data and running total-outstanding-after-each-auction — complex, not a simple snapshot |
| Summing maturity schedule entries | Summing future maturities ≠ current outstanding balance |

### Key verification
After finding the breakdown values, check:
`Regular weekly + Annual maturing + Tax anticipation = Total Treasury bills` from Status Under Limitation table.

---

## Table Format in These Files

Tables look like this:
```
## Section Heading

| Category | Jan | Feb | Mar | ... | Total |
|---|---|---|---|---|---|
| Defense | 1,234.5 | 2,345.6 | ... | 45,678.9 |
| Education | 567.8 | ... |
```

**Always check:**
1. The section heading (above the table) for context
2. The first 2–3 header rows — some tables have multi-row headers
3. The unit note near the heading (e.g., "In millions of dollars")
