# C01: CPWD enlisted, debarred and suspended contractors (erp.cpwd.gov.in)

**Status:** ✅ COMPLETE. All **9,736** CPWD-enlisted contractors plus the debarred (9) and suspended (20) lists are stored. They are re-read every month.
**Updated:** 2 Nov 2026 10:32 CET · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@685c82a` (`main`, pushed)
**Projects:** `contractor-registration-cpwd-contractors` (task `crawl`, adapter `cpwd`, target `erp.cpwd.gov.in`, `proxy="IN"`, 2 workers)
**Data:** `select … from public.records where project = 'contractor-registration-cpwd-contractors'` · Metabase "Team data (scrape_hub)"
**Previous report:** first report

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **9,765 records**: 9,736 enlisted contractors, 9 debarred, 20 suspended for violating the EMD declaration. All 114 queue items are done, with 0 errors.
- The planned source pointed at cpwd.gov.in, which resets every connection (even from India). The register now lives on
  **erp.cpwd.gov.in**, and its lists are open without a login.
- **1,010 enlistments have lapsed** but are still listed. **30 rows carry a debarment date**, while CPWD's own debarred list has 9 entries.
- The orders behind each row (PDFs) need a CPWD login. Only their links are kept.
- Nothing to do: the monthly refresh runs on its own.

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-cpwd-contractors` | ✅ COMPLETE | 114 / 114 | 0 · 0 · 0 | 9,765 | 114 | next refresh 1 Dec 2026 |

- 114 items: 55 pages of 200 rows plus the 2 short lists, both now and again for the month (`-2026m11`). Each item re-sent the same ids,
  which explains `fetched` 21,162 against 9,765 stored.
- Runs: 2, both finished, through proxies `191.219.20.177` / `.199`, with 0 errors and 0 blocks.

## 3. Pick up here
- **Repo:** `~/contractor-registration` · **Run tests:** `~/.venvs/cr/bin/python -m pytest -q tests` · **Try one item:**
  `myproxy run ~/.venvs/cr/bin/python crawl.py --local cpwd '{"list": "suspended", "cur": 1, "delta": 200}'`
- **Next action:** none. The daily setup adds the monthly items (`contractors-p<k>-<YYYY>m<MM>`).
- **Waiting on:** nothing.

## 4. What stands out
1. **Lapsed but listed.** 1,010 of 9,736 rows have an "Enlistment Valid Upto" date before 2 Nov 2026.
   *So what:* the list is a register of every enlistment ever made, not of the firms currently eligible to bid. Filter on the date.
2. **Two debarment views disagree.** 30 enlisted rows have a "Date of Debarred", but the separate "CPWD debarred contractors" list has 9.
   *So what:* use the column for history and the list for current debarments. We have not reconciled the two.
3. **Small firms dominate.** Class IV (3,201) and V (2,281) make up 56% of the list. The top classes (I(Super), I(AAA), I(AA), I(A))
   together hold 629 firms.
4. **379 rows have no status**; the other 9,357 say "Current".

## 5. The source
- CPWD's new Liferay portal, `erp.cpwd.gov.in`, serves the lists as server-rendered tables of up to 200 rows a page. No captcha, no login.
  It answers **Indian addresses only**: the team box and GitHub runners time out, while the hub's Mumbai proxies get through.
- `cpwd.gov.in` (named on the planned-sources page) resets TLS from every address tried, including a real Chrome on an Indian IP.

### 5.1 Site map

| What | URL / form | Notes |
|---|---|---|
| Enlisted contractors | `/web/cpwd/list-of-cpwd-enlisted-debarred-contractors`, portlet `gov_in_cpwd_contractor_portlet` | `_cur` / `_delta` (≤ 200), 55 pages |
| CPWD debarred | same page, portlet `gov_in_cpwd_ed_contractors_portlet` | 9 rows |
| Suspended (EMD declaration) | `/web/cpwd/list-of-suspended-contractors-due-to-violation-of-emd-declaration` | 20 rows |
| Orders (PDF) behind rows | `/documents/…` | **answer with a CPWD sign-in page**: links only |
| Non-CPWD debarred | JSON service | refuses guests (404) |
| Enlistment portal (CEMS) | `cems.cpwd.gov.in/ContractorLogin.aspx`, `/OfficerLogin.aspx` | login only |

## 6. How it is collected
- **Code:** `adapters/cpwd.py`. `list_url` builds the portlet's paging URL, `portlet_section` cuts out one portlet's HTML, and
  `parse_rows` reads the table (header row, the site's row id from `selected…Id='<n>'`, and document links).
- **Queue:** `contractors-p1` … `-p55` (200 rows each; the last 6 are spares that finish with 0 rows), `debarred`, `suspended`, plus a
  monthly copy of each. `files: false`, because the orders need a login.
- **Pace:** 0.5 s minimum between requests, at most 2 workers, one Indian proxy each. 114 requests took 224 s in total.

## 7. The data
- Record id: `contractors-<site id>`; the two short lists use `debarred-<row hash>` / `suspended-<row hash>`.
- Fields (`data->'columns'`): `Name of Contractor`, `Address`, `State`, `Category`, `Class`, `Date of Enlistment`,
  `Enlistment Valid Upto`, `Date of Debarred`, `Debarred Upto`, `Date of Suspension`, `Suspension Upto`, `Contractor Status`.
  `data->'files'` holds the links to the order PDFs, which are not fetched. **Dates are `DD/MM/YYYY` text.**

| Class | Firms | | Category | Firms |
|---|---:|---|---|---:|
| IV | 3,201 | | Buildings and Road | 8,251 |
| V | 2,281 | | Building | 613 |
| III | 2,015 | | Composite | 559 |
| II | 976 | | Horticulture | 256 |
| I | 615 | | Infrastructure | 28 |
| I(A) / I(AA) / I(AAA) / I(Super) | 229 / 198 / 96 / 106 | | NA | 19 |

```sql
-- current enlistments by class
select data->'columns'->>'Class' class, count(*) from public.records
where project = 'contractor-registration-cpwd-contractors' and data->>'list' = 'contractors'
  and to_date(data->'columns'->>'Enlistment Valid Upto', 'DD/MM/YYYY') >= current_date group by 1 order by 2 desc;
-- rows with a debarment date
select data->'columns'->>'Name of Contractor', data->'columns'->>'Date of Debarred', data->'columns'->>'Debarred Upto'
from public.records where project = 'contractor-registration-cpwd-contractors' and data->'columns'->>'Date of Debarred' <> '';
```

## 8. Verification
- Tests: 42 passed (`pytest tests`), including `cpwd_contractors.html` and `cpwd_suspended.html`. CI `check`: green on `main` (PR #6, 2 Nov).
- Cross-check: 9,736 stored equals the portal's own total on 1 Nov. Ids are the site's own, so they stay stable from run to run.
- **Not checked:** whether the 30 debarment dates match the orders (those need a login).

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | Order PDFs need a CPWD login (missing at the source for us) | every row with an order | Links kept; no way in without a CPWD account. |
| 2 | Non-CPWD debarred list refuses guests | unknown | Not collected. |
| 3 | Lapsed enlistments still listed (at the source) | 1,010 | Filter on `Enlistment Valid Upto`. |
| 4 | Rows without status (at the source) | 379 | Kept as blank. |

## 10. Risks and open decisions
- **Risks:** a portal redesign would show up as 0 rows on an item (`parse_rows` finds no table), and the item would fail rather than store wrong data.
- **To decide:** nothing open.

## 11. Next steps
**To do now:** nothing. The refresh runs monthly.
**Later:** 1. Reconcile the 30 debarment dates with the 9-row debarred list. 2. Join against PMGSY contractors and Gujarat /
Maharashtra registers on normalised firm names ([C06](report-C06.md), [C02](report-C02.md)).
**Housekeeping:** the hub's health checks for India-only sites fail from its own server; Sarthak can route them through a proxy.
