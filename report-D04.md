# D04: State medical services corporations: blacklisted and debarred suppliers (TNMSC, RMSC, GMSCL)

**Status:** ✅ COMPLETE. The family reads 4 lists from 3 state medical services corporations. The pool stored **130** rows
(84 suppliers) on 14 Nov, through the Indian proxies (the sites do not answer GitHub runners). Each list is read again every week.
**Updated:** 14 Nov 2026 05:30 IST · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@f9efa86` (`main`, pushed)
**Projects:** `contractor-registration-banlists` (task `crawl`, adapter `banlists`, `proxy="IN"`, 1 worker; shared with
[D03](report-D03.md))
**Data:** `select … from public.records where project = 'contractor-registration-banlists' and data->>'list' in ('tnmsc',
'rmsc-company', 'rmsc-product', 'gmscl')` · bucket: none (the lists are web pages; the order PDFs they link are not stored)
**Previous report:** first report

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **New scope (14 Nov 2026).** The ban-list adapter of [D03](report-D03.md) also reads the blacklists of TNMSC (Tamil Nadu), RMSC
  (Rajasthan, by firm and by product) and GMSCL (Gujarat). Each list is read again every week.
- **130 rows, 84 suppliers:** RMSC products 101, TNMSC 11, GMSCL 10, RMSC firms 8.
- **Most bans are for quality:** 54 of 101 RMSC product bans are "not of standard quality" (NOSQ); GMSCL gives the assay result
  (for example 66.17 % of the declared amoxicillin content).
- **4 suppliers are on the lists of two corporations** (indicators: name match only).
- **Known issue:** the 10 GMSCL records name the drug as the firm (stored by a runner with the code before the fix). The weekly
  item of 16 Nov stores them right and marks the old ids `superseded`. Until then, read `columns.name_of_firm`.
- **Next:** nothing to do.

## 2. Where things stand

| List | Organisation | Rows | Suppliers | Bans end in | State |
|---|---|---:|---:|---|---|
| `rmsc-product` | RMSC, product-wise | 101 | 80 | 2026–2029 (5 rows without a date) | ✅ stored |
| `tnmsc` | TNMSC (drugs, equipment) | 11 | 10 | 2027–2031 | ✅ stored |
| `gmscl` | GMSCL | 10 | 8 | 2027–2029 | ✅ stored |
| `rmsc-company` | RMSC, company-wise | 8 | 8 | 2030–2031 | ✅ stored |

- The project and its pace are in [D03, section 2](report-D03.md#2-where-things-stand).

## 3. Pick up here
- **Repo:** `~/contractor-registration` (`main`, clean) · **Run tests:** `~/.venvs/cr/bin/python -m pytest -q tests` (59 pass)
- **Try one list:** `~/.venvs/cr/bin/python crawl.py --local banlists '{"list": "tnmsc"}'`
- **Next action:** none. **Waiting on:** the weekly item of 16 Nov (GMSCL fix).

## 4. What stands out
1. **Quality is the main reason.** RMSC: 54 of 101 product bans are NOSQ (7 of them "grossly substandard"), 37 are for non-supply.
   All 8 RMSC company bans are NOSQ, for five years. TNMSC: 4 of 11 are "misbranded drug".
2. **GMSCL publishes the test result.** Each GMSCL row names the item and the content found (for example folic acid 66.17 %,
   bisacodyl 84.00 %). *So what:* the lists can be checked against the drug regulator's "not of standard quality" alerts (F19).
3. **Large suppliers are on the lists.** TNMSC lists a multinational's Indian unit (blacklisted 11 May 2022 to 10 May 2027, "engaging
   in fraudulent and obstructive practices"); RMSC and GMSCL both list a large biosimilars company.
4. **4 suppliers are on two corporations' lists:** two pairs TNMSC–RMSC, one TNMSC–GMSCL, one RMSC–GMSCL (same normalised name;
   not checked further).

## 5. The source
- The three corporations publish the lists as HTML tables, without a login. All three answer from Germany (a team box) and through
  the Indian proxies, but **not from GitHub runners** (14 Nov: "site did not answer" from an Azure address, 2–3 tries per item).

### 5.1 Site map
| What | URL | Notes |
|---|---|---|
| TNMSC | `tnmsc.tn.gov.in/blacklisted/blacklisted.php` | tables for drugs, laboratories and equipment; "Black Listed Period" over two columns |
| RMSC | `rmsc.health.rajasthan.gov.in/…/Banned-firms0/Banned_Company.html`, `…/Banned_Product.html` | no serial numbers; each row links the order PDF |
| GMSCL | `gmscl.gujarat.gov.in/black-list-firm.htm` | each row links the debarment circular |

## 6. How it is collected
- **Code:** `adapters/banlists.py` (the same parser as D03). For these pages it also handles a header cell over two columns, a header
  line printed twice in one row (TNMSC), rows without a serial number (RMSC), and footnote lines (TNMSC's "* BL… – …").
- **Queue:** items `tnmsc`, `rmsc-company`, `rmsc-product`, `gmscl`, and the same with `-<YYYY>w<WW>` every week.
- **Decision (Claude, 14 Nov 2026):** the order PDFs that the rows link are not downloaded (the row has the facts; about 120 PDFs).

## 7. The data
- One record per row; record id `<list>-<hash of firm, from date, order reference>`.

### 7.1 Fields
| Field | Source | Notes |
|---|---|---|
| `firm` | name column | TNMSC adds a unit code in brackets |
| `item` | item / product / drug column | **RMSC adds its tender item number** ("103 (Ciprofloxacin Tablets IP …)") |
| `from_date`, `upto` | the list | dates as printed; RMSC gives only the end date (sometimes "(5 Year)") |
| `reason`, `order_ref` | the list | RMSC's order number is in `columns.download` |
| `vendor_code` | TNMSC's "BL Code" | e.g. `BL2223002` |
| `columns` | the list | every column as printed |

### 7.2 What is in it
| Reason (RMSC product-wise) | Rows |
|---|---:|
| NOSQ (not of standard quality), incl. grossly substandard | 54 |
| non-supply, incl. with violation of conditions | 37 |
| violation of tender conditions | 8 |
| other | 2 |

### 7.3 How to query it
```sql
select data->>'list', count(*), count(distinct upper(data->>'firm')) from public.records
where project = 'contractor-registration-banlists' and data->>'list' in ('tnmsc', 'rmsc-company', 'rmsc-product', 'gmscl') group by 1;
-- suppliers on more than one corporation's list (by name)
select upper(data->>'firm'), array_agg(distinct data->>'list') from public.records
where project = 'contractor-registration-banlists' and data->>'list' in ('tnmsc', 'rmsc-company', 'rmsc-product', 'gmscl')
group by 1 having count(distinct split_part(data->>'list', '-', 1)) > 1;
```

## 8. Verification
- Tests: 60 passed, including the TNMSC and RMSC page shapes (made-up names).
- Pool (14 Nov 04:50–05:15 IST, proxies `95.134.119.x` and `191.219.x`): 130 rows, the same per list as the local runs. The first
  tries from a GitHub runner (Azure `52.159.229.163`) got no answer (2–5 per item).
- **Not checked:** the rows against the linked order PDFs.

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | **No list found** (at the source): KMSCL (Kerala), BMSICL (Bihar), MPPHSCL, TSMSIDC, CGMSC, OSMC | 6 corporations | Their home pages link no list or do not answer. Recheck monthly. |
| 2 | RMSC rows without an end date | 5 | Kept. |
| 3 | Dates as printed | all | Parse in the query. |
| 4 | **GMSCL: drug name in `firm`** (missed by us; fixed in code) | 10 | Read `columns.name_of_firm` until 16 Nov; filter `kind = 'banned_firm'` after it. |

## 10. Risks and open decisions
- **Risks:** a page redesign fails the item (`parse`) and keeps the old records.
- **To decide:** none.

## 11. Next steps
**Later:** 1. Match the banned products against the CDSCO "not of standard quality" alerts (planned source F19) when a family reads
them. 2. Recheck the other state corporations monthly.
**Housekeeping:** none.
