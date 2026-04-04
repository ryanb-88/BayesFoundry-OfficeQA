# U.S. Fiscal Year Rules — Critical Reference

This is one of the most common failure points. Treasury Bulletins report BOTH fiscal year
and calendar year data. Getting these mixed up causes large cascading errors.

## Fiscal Year Timeline

| Period | Fiscal Year Ends | Example |
|---|---|---|
| Before Oct 1, 1976 | **June 30** | FY1953 = July 1, 1952 – June 30, 1953 |
| Transition | Jul 1 – Sep 30, 1976 | "Transition Quarter" (TQ) — 3-month period |
| Oct 1, 1976 onward | **September 30** | FY1977 = Oct 1, 1976 – Sep 30, 1977 |

## How to Tell if a Table Is Fiscal or Calendar Year

- Look for the label: "fiscal year", "FY", "calendar year", or month names
- Annual totals labeled "Total" or "Year" without months → likely fiscal year
- Tables with all 12 individual months → can compute either FY or CY from them
- Pre-1977: if a table shows "July–June" totals, that's the fiscal year

## Which Bulletin Has Which Year's Annual Data?

**Pre-1977 fiscal year (ends June 30):**
- FY1953 annual totals first appear in: `treasury_bulletin_1953_07.txt` or `_08.txt` or `_09.txt`
- Revised FY1953 totals: check bulletins through early 1954

**Calendar year:**
- CY1953 totals (all 12 months Jan–Dec): appear in early 1954 bulletins
- To compute CY total yourself: sum January through December individual monthly values

## The "Transition Quarter" (TQ)
- July 1–September 30, 1976
- Sometimes labeled "TQ" or "Transition Period" in tables
- Don't confuse with FY1976 or FY1977 data

## Key Rule
If a question asks about a **calendar year**, find individual monthly values
and sum them yourself — don't use the "Total" column which is often fiscal year.
