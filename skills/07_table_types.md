# Obscure Table Types — Navigation Guide

This skill covers table types NOT in the main topic mapping. Load when the question involves
savings bonds, silver/gold, trust funds, seigniorage, money in circulation, IRS collections,
or Treasury survey of ownership.

---

## Savings Bonds (Series E, EE, I, D, H, Savings Notes)

**Grep patterns:**
```bash
grep -n "Savings Bond\|Series E\|Series EE\|Series HH\|Savings Note\|Accrued Discount\|Redemption" \
  /app/corpus/treasury_bulletin_YYYY_MM.txt | head -20
```

**Key row labels:**
- `Sales` / `Total Sales` — amount sold in the period
- `Redemptions — Total` / `Unmatured Redemptions` — bonds redeemed before maturity
- `Accrued Discount` — interest accrued but not yet paid
- `Total Interest-Bearing Debt` — outstanding by series

**Series naming:**
| Series | Notes |
|--------|-------|
| Series E | Original war bonds; issued at discount, redeemed at face value |
| Series EE | Replaced Series E in 1980 |
| Series I | Inflation-indexed bonds |
| Series H / HH | Current income bonds (paid interest periodically) |
| Series D | Early series, mostly pre-1940s |
| Savings Notes (Series C) | Sold through payroll savings plans |

**Units:** Usually in millions of nominal dollars. Check table header.

---

## Silver and Gold Monetary Stocks

**Grep patterns:**
```bash
grep -n "Silver Stock\|Gold Stock\|Monetary Stock\|Fine Ounce\|Fine Pound\|Seigniorage\|Silver Certificate\|Gold Certificate" \
  /app/corpus/treasury_bulletin_YYYY_MM.txt | head -20
```

**Key concepts:**
- **Monetary gold stock** — gold held by U.S. Treasury at official price (pre-1971: $35/oz)
- **Silver monetary stock** — silver held for currency backing
- **Seigniorage** — profit from issuing currency = face value of coins issued minus their production cost; appears as a receipt in budget tables
- **Fine ounces / fine pounds** — weight of pure metal (not gross weight); 1 fine pound = 12 troy ounces

**Unit note:** Silver tables may be in thousands of fine ounces or millions of dollars. Always check header.

**Where to find:**
- Gold: `treasury_bulletin_193*.txt` through `treasury_bulletin_197*.txt` (gold data less prominent post-1971)
- Silver: `treasury_bulletin_193*.txt` through `treasury_bulletin_196*.txt`
- Seigniorage: In the budget receipts section — grep `Seigniorage\|Coinage`

---

## Trust Funds

**Grep patterns:**
```bash
grep -n "Trust Fund\|OASI\|Hospital Insurance\|Highway Trust\|Airport.*Airway\|Unemployment.*Trust\|Postal" \
  /app/corpus/treasury_bulletin_YYYY_MM.txt | head -20
```

**Major trust funds:**
| Fund | Grep pattern | Notes |
|------|-------------|-------|
| Social Security (OASI) | `OASI`, `Old-Age and Survivors` | Largest trust fund |
| Medicare (HI) | `Hospital Insurance`, `HI Trust` | Post-1965 |
| Unemployment | `Unemployment Trust`, `Unemployment Insurance` | State-level data |
| Highway Trust | `Highway Trust`, `Highway` | Fuel taxes → road spending |
| Airport & Airway | `Airport`, `Airway Trust` | Airline ticket taxes |
| Civil Service Retirement | `Civil Service`, `Retirement` | Federal employees |

**Key row labels:**
- `Receipts` / `Total Receipts` — money coming in
- `Expenditures` / `Total Expenditures` / `Outlays` — money going out
- `Net Balance` / `Total Balance` — fund balance at end of period
- `Transfers from General Fund` — intergovernmental transfers

---

## Money in Circulation / Paper Money

**Grep patterns:**
```bash
grep -n "Money in Circulation\|Paper Money\|Federal Reserve Note\|Currency in Circulation\|Coin" \
  /app/corpus/treasury_bulletin_YYYY_MM.txt | head -20
```

**Key row labels:**
- `Federal Reserve Notes` — paper currency issued by Fed
- `U.S. Notes` / `Legal Tender Notes` — older Treasury currency
- `Silver Certificates` — pre-1964 silver-backed bills
- `Total Money in Circulation` — all currency in public hands
- `Coin` — metallic currency

**Units:** Usually in millions of dollars. Earlier tables may be in thousands.

---

## Treasury Survey of Ownership (Federal Securities)

**Grep patterns:**
```bash
grep -n "Survey of Ownership\|Ownership of Federal\|Investor.*Holdings\|Commercial Bank\|Insurance Compan\|Individual" \
  /app/corpus/treasury_bulletin_YYYY_MM.txt | head -20
```

**Key investor categories:**
- U.S. Government accounts and Federal Reserve banks
- Commercial banks
- Mutual savings banks
- Insurance companies
- Other corporations
- Individuals / households
- Foreign and international

**Note:** Survey dates are specific (e.g., "end of February"). The question may specify which survey date to use — check column headers carefully.

---

## IRS Internal Revenue Collections (by State or Category)

**Grep patterns:**
```bash
grep -n "Internal Revenue\|Collections by State\|Individual Income\|Corporation Income\|Employment Tax\|Excise" \
  /app/corpus/treasury_bulletin_YYYY_MM.txt | head -20
```

**State-level data:** Some tables break down IRS collections by state. To find a specific state:
```bash
grep -n "California\|New York\|Texas\|[State Name]" /app/corpus/treasury_bulletin_YYYY_MM.txt | head -10
```

**Key categories:**
- Individual income taxes (net of refunds)
- Corporation income taxes
- Employment taxes (Social Security, Medicare)
- Excise taxes (alcohol, tobacco, fuel)
- Estate and gift taxes

**Units:** Often in thousands of dollars for state-level tables. Check header.

---

## Foreign Exchange Operations / ESF Positions

**Grep patterns:**
```bash
grep -n "Foreign Exchange Operations\|Net Euro\|Net Yen\|Options.*Position\|Forward\|Intervention" \
  /app/corpus/treasury_bulletin_YYYY_MM.txt | head -20
```

**Key concepts:**
- **Net position** — long minus short in a currency
- **Forward contracts** — agreements to buy/sell currency at a future date
- **Options** — right to buy/sell; Net options position = calls minus puts
- **Cumulative net** — running total of interventions

---

## CPI / Inflation Adjustment

⚠️ **CPI data is NOT in the Treasury corpus.** If the question requires inflation adjustment:

1. Use **web search**: `"BLS CPI-U annual averages"` or `"BLS CPI-U monthly index"` to find the correct index values
2. Apply: `real_value = nominal_value / (CPI_target_year / CPI_base_year)`
3. Common base years used by Treasury: 1982-84 = 100 (CPI-U standard base)

Example: "convert 1940 value to June 1979 dollars"
```python
# CPI-U: 1940 ≈ 14.0, June 1979 ≈ 216.6 / 12 (monthly)
# real = nominal * (cpi_target / cpi_source)
real = nominal * (cpi_june_1979 / cpi_1940)
```

---

## Page-Number Questions

The corpus files do NOT have page markers embedded in the text.

**Strategy:**
1. Search for the **Table of Contents** near the top of the bulletin file:
   ```bash
   grep -n "Contents\|TABLE OF CONTENTS\|Index" /app/corpus/treasury_bulletin_YYYY_MM.txt | head -5
   # Then read the ToC section (usually within first 100 lines)
   ```
2. The ToC maps section names to page numbers — use it to identify which section is on the target page
3. Search for that section's content further in the file
4. For "pdf page X vs report page Y" — bulletins often have a cover + blank pages before page 1; the ToC uses report page numbers
