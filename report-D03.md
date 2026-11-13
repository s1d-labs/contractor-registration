# D03: PSU ban, debarment and holiday lists (BHEL, Oil India, OPaL, NHPC, NDDB, BPCL, HPCL)

**Status:** ⏳ RUNNING. The adapter is built and merged, and the pool reads 9 lists from 7 public sector undertakings.
The first pool pass (14 Nov, 03:50–04:20 IST) stored all **456** rows, the same as the local runs.
**Updated:** 14 Nov 2026 04:40 IST · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@f9efa86` (`main`, pushed)
**Projects:** `contractor-registration-banlists` (task `crawl`, adapter `banlists`, target `banlists`, `proxy="IN"` from 14 Nov 04:40, 1 worker),
`contractor-registration-banlists-in` (same adapter, target `www.bharatpetroleum.in`, `proxy="IN"`, 1 worker). The D04 lists
(state medical corporations) are in the first project too: see [report-D04.md](report-D04.md).
**Data:** `select … from public.records where project = 'contractor-registration-banlists'` (and `'…-banlists-in'`), `data->>'list'`
names the list · bucket `contractor-registration-banlists*/pdf/<list>/`
**Previous report:** first report

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **New scope (14 Nov 2026).** No family covered D03. The family now reads 9 lists of firms that PSUs ban, debar or put "on
  holiday": BHEL (2), Oil India, OPaL, NHPC, NDDB, BPCL (2) and HPCL. Each list is read again every week.
- **456 rows** stored: BPCL holiday 121, BHEL banned 131, Oil India 92, BPCL show-cause 53, BHEL debarred 19, HPCL 12,
  OPaL 11, NHPC 11, NDDB 6.
- **Most BPCL holiday listings are about the bid, not the work:** 83 of 121 firms did not accept a letter of award, or withdrew
  or raised a bid after they became the lowest bidder. 12 of 121 gave forged or fake documents.
- **Oil India keeps expired blocks on its list:** the end date of 71 of 92 rows has passed.
- **Cross-check with the registers (indicators only):** 7 banned firms have the same name and state as a contractor in the PMGSY
  master or the CPWD list. A masked PAN is not enough to link firms: 12 of 12 masked-PAN matches were different firms.
- **Next:** nothing to do. The lists refresh every week.

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-banlists` | ⏳ RUNNING | 12 / 20 | 8 · 0 · 0 | 290 (D03 lists) | 12 | the 8 failed items are the D04 lists: see [report-D04.md](report-D04.md) |
| `-banlists-in` | ✅ COMPLETE | 6 / 6 | 0 · 0 · 0 | 186 | 6 | weekly refresh |

| List | Organisation | What the list says | Format | Rows stored (14 Nov) | Version on 14 Nov |
|---|---|---|---|---:|---|
| `bhel-debarred` | BHEL | debarred from business with BHEL; a second part from government instructions | PDF | 19 | 16 Jul 2026 |
| `bhel-banned` | BHEL | banned across BHEL; a second part from government instructions | PDF | 131 | as on 6 Jan 2023 |
| `oil-india` | Oil India | debarred ("blocked") vendors | PDF | 92 | 3 Nov 2026 |
| `opal` | OPaL (ONGC Petro additions) | vendors put on holiday | PDF | 11 | not dated |
| `nhpc` | NHPC | banned firms | HTML table | 11 | not dated |
| `nddb` | NDDB | blacklisted bidders | HTML table | 6 | not dated |
| `bpcl-holiday` | BPCL | vendors on the holiday list | PDF (proxy) | 121 | not dated |
| `bpcl-show-cause` | BPCL | vendors served a show-cause notice (holiday listing proposed) | PDF (proxy) | 53 | last notice 6 Nov 2026 |
| `hpcl-holiday` | HPCL | vendors on the holiday list | PDF (proxy) | 12 | 2023-24 |

## 3. Pick up here
- **Repo:** `~/contractor-registration` (`main`, clean) · **Run tests:** `~/.venvs/cr/bin/python -m pytest -q tests` (58 pass)
- **Try one list:** `~/.venvs/cr/bin/python crawl.py --local banlists '{"list": "nhpc"}'`; for BPCL and HPCL:
  `myproxy run ~/.venvs/cr/bin/python crawl.py --local banlists '{"list": "bpcl-holiday"}'`
- **Next action:** none. The weekly items (`<list>-<YYYY>w<WW>`) come from the daily setup.
- **Waiting on:** nothing.

## 4. What stands out
1. **BPCL lists firms for what they do at the bid stage.** 83 of 121 holiday listings give a bid-stage reason: "Not honoured the
   letter of award" (34 rows and variants), "Withdraws/revises the bid" (17), "LOI not collected & No response" (8). 12 rows give
   forged or fake documents. Retail (46) and CPO-R (20) list the most firms. *So what:* these are bidders, not only contractors
   that failed on site; the same firms can appear in other tenders.
2. **BPCL publishes its pending cases.** The show-cause list names 53 vendors that BPCL proposes to put on holiday. 30 notices are
   from 2026, but 9 are from September 2020 and are still open. *So what:* an early indicator, before a ban.
3. **Old blocks stay on Oil India's list.** 71 of 92 rows have an end date before 14 Nov 2026 (blocks from 2015 to 2026). 29 of 92
   rows give fraudulent documents as the reason. OPaL does the same: 7 of 9 dated rows have ended. *So what:* use `upto` to tell an
   active ban from an expired one.
4. **The same firm can appear in a ban list and in a register.** 7 banned firms have the same normalised name, and a state that their
   address names, as a contractor in the PMGSY master (7 pairs) or the CPWD list (2 pairs). These are indicators: a name match is
   not proof that it is the same firm. 39 names match in any state, but most are common names. Method in [7.3](#73-how-to-query-it).
5. **A masked PAN does not identify a firm.** 18 banned rows print a PAN. 12 PMGSY master rows have the same masked PAN (first five
   and last character), and all 12 are different firms. No full PAN matches the PMGSY scores or the Uttarakhand register.
6. **BHEL's two lists include the government's own bans.** Both PDFs end with a part "as per Government instruction" (5 and 4 firms,
   orders from 2010 to 2025). The records keep the part in `section`.

## 5. The source
- Each organisation publishes its list on its own site, without a login. BHEL, Oil India, OPaL, NHPC and NDDB answer from Germany
  and from GitHub runners; the project uses the Indian proxies anyway, because it also holds the D04 lists. `bharatpetroleum.in` and `hindustanpetroleum.com` answer 403 outside India: their lists go through the
  hub's Indian proxies.
- The PDF address changes with each new version. The adapter reads the page that links the list, then the PDF.

### 5.1 Site map
| What | URL / form | Notes |
|---|---|---|
| BHEL debarred | `bhel.com/list-debarred-firms` → `sites/default/files/Debarred Firms List - BHEL_<n>.pdf` | 2 pages |
| BHEL banned | `bhel.com/list-banned-firms` | redirects to `Banned_firms_list_BHEL_<n>.pdf`, 8 pages |
| Oil India | home page link "Oil's Debarred Vendors List" → `files/<yyyy-mm>/BLOCKED_VENDOR_LIST_<dd_mm_yyyy>.pdf` | 6 pages |
| OPaL | home page → `assets/pdf/List_of_vendors_put_on_holiday.pdf` | 2 pages |
| NHPC | `nhpcindia.com/welcome/language/en/firmbanlist` | table; needs the session cookie of a redirect |
| NDDB | `nddb.coop/resources/tenders/blackfirms` | table |
| BPCL | `bharatpetroleum.in/bharat-petroleum-for/business-associates/vendors.aspx` → `bpcl-holiday-listing.pdf`, `scn-list.pdf` | 25 and 8 pages |
| HPCL | `hindustanpetroleum.com/purchase-procurement` → `documents/pdf/holiday_list.pdf` | the page also links older dated lists |

## 6. How it is collected
- **Code:** `adapters/banlists.py`. `LISTS` names each list (page, PDF link pattern, organisation, kind). `pdf_tables` reads PDF
  tables with pdfplumber, and gives each table the line printed above it (the title of a part). `html_tables` reads HTML tables
  (merged cells kept as columns). `table_rows` finds the header, joins a second header line (From / To), keeps rows with a serial
  number, joins a row that runs over two table lines, and repeats the cell above for "-do-". `to_records` adds the common fields.
- **Queue:** one item per list (`<list>`), and one per list each ISO week (`<list>-<YYYY>w<WW>`): 26 items in week 46.
- **Pace & behaviour:** 2 requests per list (page, PDF); 0.5 s between requests; 1 worker per project.
- **Decision (Claude, 14 Nov 2026):** lists without a fixed page (MIDHANI's monthly PDFs), stale lists (BDL, 2022), and pages
  without a list (Mazagon Dock) are left out. See [9](#9-known-gaps-and-quality-issues).

## 7. The data
- Table `public.records`, one record per row of a list. Record id `<list>-<hash of firm, from date, order reference>`; a second
  identical row gets `-2`. The stored PDF of each version is in the bucket (`pdf_path`).

### 7.1 Fields
| Field | Source | Notes |
|---|---|---|
| `list`, `org`, `list_kind` | the adapter | `list_kind`: `debarred`, `banned`, `blocked`, `holiday`, `show_cause`, `blacklisted` |
| `firm` | the list's name column | **with the address in one cell** for NDDB and OPaL; some rows name a proprietor |
| `address`, `vendor_code`, `pan` | the list | `pan` (derived): a PAN printed anywhere in the row |
| `from_date`, `upto`, `period` | the list | **dates as printed** (`21.08.2015`, `01-Apr-24`, `16-Jul-2026`); not normalised |
| `reason`, `order_ref`, `banned_by`, `remarks` | the list | `banned_by` is the business unit for BPCL (`Retail`, `LPG`, …) |
| `section`, `sr` | the list | `section`: the part of the list (e.g. "Firms Debarred as per Government Instruction") |
| `columns` | the list | every column as printed, keys in snake case |
| `source`, `pdf_url`, `pdf_path`, `pdf_sha256` | the adapter | the version that was read |

### 7.2 What is in it
| Reason group (BPCL holiday list) | Rows |
|---|---:|
| did not accept the award, withdrew or raised the bid, did not collect the LOI | 83 |
| forged or fake documents | 12 |
| other (poor performance, quality) | 26 |
| **Total** | **121** |

### 7.3 How to query it
```sql
-- rows per list
select data->>'list', count(*) from public.records
where project in ('contractor-registration-banlists', 'contractor-registration-banlists-in') group by 1 order by 2 desc;
-- BPCL holiday listings by business unit
select data->>'banned_by', count(*) from public.records
where project = 'contractor-registration-banlists-in' and data->>'list' = 'bpcl-holiday' group by 1 order by 2 desc;
-- banned rows that print a PAN, against the PMGSY contractor scores (full PAN)
select b.data->>'list', b.data->>'pan', k.data->>'state' from public.records b
join public.records k on k.project = 'contractor-registration-pmgsy-contractors' and k.data->>'kind' = 'contractor_kpi'
 and k.data->>'pan' = b.data->>'pan'
where b.project in ('contractor-registration-banlists', 'contractor-registration-banlists-in') and b.data ? 'pan';
```
The name match in [4](#4-what-stands-out) normalises names (upper case; no "M/s", "Pvt", "Ltd", "& Co", punctuation or text in
brackets), needs at least two words and eight characters, and then needs the register's state in the banned row's address.

## 8. Verification
- Tests: 58 passed (`tests/test_adapters.py`: two-line headers, merged cells, rows over two lines, "-do-", part titles; made-up names).
- scrape-check (14 Nov, box): PASS, 242 records on 3 items, the same ids on rerun. CI `check` (GitHub runner): PASS on NDDB and OPaL.
- Pool pass (14 Nov, GitHub runner `52.159.229.163` and the Indian proxies): 456 records, the same count per list as the local
  runs; no `layout` or `parse` failure; serial numbers run without gaps.
- **Not checked:** the dates against the PDFs' own "as on" dates; whether the organisations remove expired rows on their sites.

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | **Lists not read** (at the source): MIDHANI (new PDF each month, no fixed page), BDL (2022), Mazagon Dock (no list), MoD (page moved) | 4 orgs | MIDHANI and BDL repeat MoD's bans. Recheck monthly. |
| 2 | **No list found**: ONGC, GAIL, NTPC, POWERGRID, Coal India, SAIL, HAL, EIL, NMDC | 9 PSUs | Their home pages link no list; some publish bans only in tender conditions. |
| 3 | Dates as printed (at the source) | all lists | Five date formats; parse in the query. |
| 4 | Expired rows kept (at the source) | Oil India 71, OPaL 7 | Use `upto`. |
| 5 | Firm and address in one cell (at the source) | NDDB, OPaL | Split by hand when needed. |
| 6 | BHEL's banned list is "as on 6 Jan 2023" (at the source) | 131 | BHEL has not updated it; its debarred list is from Jul 2026. |

## 10. Risks and open decisions
- **Risks:** a new PDF layout fails the item (`hub.failure("parse", …)`) and keeps the old records. Rows name individuals
  (proprietors) and print PANs: keep them out of reports and published tables.
- **To decide (trideep):** 1. Add MIDHANI by its WordPress media search (more requests, mostly MoD's list). Recommendation: no.

## 11. Next steps
**To do now:** none.
**Later:** 2. A table in `ws_trideep` that joins ban lists to the registers by name and state, for manual review. 3. Recheck
the PSUs without a list each month. 4. MoD's debarred list when its page is found again.
**Housekeeping:** none.
