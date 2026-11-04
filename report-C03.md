# C03: MES approved products, consultants and works policy (mes.gov.in)

**Status:** ✅ COMPLETE. All 38 items are done: **290** rows (263 product-approval rows, 10 technical-information, 10 contract-policy
letters, 7 consultancy rows) and their PDFs. Since 3 Nov the project borrows only the proxies mes.gov.in accepts (`proxy_only`).
The contractor enlistment itself (CCEP) is login-only.
**Updated:** 4 Nov 2026 09:55 CET · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@51547a2` (`main`)
**Projects:** `contractor-registration-mes-works` (adapter `mes`, target `mes.gov.in`, `proxy="IN"`, `proxy_only=["91.124.42."]`, 2 workers)
**Data:** `select … from public.records where project = 'contractor-registration-mes-works'` · bucket `contractor-registration-mes-works/`
**Previous report:** 2 Nov 2026 10:32 CET (stalled at 23 / 38 on refused proxies)

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **290 rows stored**, every page: 263 product-approval rows, 10 technical-information rows, 10 contract-policy letters and 7
  consultancy rows, plus their PDFs. The PDFs include the consolidated list of approved products and the list of approved consultants.
- **What fixed it:** mes.gov.in answers only proxies in `91.124.42.x`. The hub added `proxy_only` (3 Nov) and the project now asks
  for those two; on 4 Nov two runs (one per proxy) finished the remaining 15 items in minutes. One attachment did not load (404).
- MES **enlistment** (CCEP) and **product approval** (PAP) portals are login-only. MES tenders are already in `gepnic-defproc`.

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-mes-works` | ✅ COMPLETE | 38 / 38 | 0 · 0 · 0 | 290 | 15 | weekly refresh |

- 4 Nov, 08:54 CET: two runs, through `91.124.42.191` (70 records) and `.193` (60), finished the 15 items left from 2 Nov.

## 3. Pick up here
- **Repo:** `~/contractor-registration` · **Run tests:** `~/.venvs/cr/bin/python -m pytest -q tests` · **Try one item:**
  `myproxy run ~/.venvs/cr/bin/python crawl.py --local mes '{"path": "works/product-approval", "page": 3, "files": true}'`.
  Check the exit IP first (`myproxy run curl -s https://api.ipify.org`): only `91.124.42.x` works.
- **Next action:** none; the weekly refresh runs by itself.
- **Waiting on:** nothing.

## 4. What stands out
1. **The site picks proxies.** Per exit IP since 1 Nov: `91.124.42.191` gave 174 records and `.193` gave 47. `191.219.20.105` / `.177` / `.178` / `.199`
   and `95.134.119.235` / `.238` / `.254` gave 0 records and 1,006 connection errors between them. It fails at the TLS handshake (client
   hello sent, no answer), which looks like a block on those ranges rather than an outage. *So what:* proxy choice matters per site;
   `proxy_only` (hub, 3 Nov) solved it.
2. **The useful documents are PDFs, not rows.** The "list of approved products as on 15 Oct 2026" and the consolidated approved
   consultants list sit behind single rows. Their text is stored beside them (`.pdf.txt`), so they can be searched without OCR.

## 5. The source
- `mes.gov.in`: Drupal 11, server-rendered tables, `?page=N`, PDFs. Indian addresses only, and only some Indian proxies (above).
  No captcha on the public pages.

### 5.1 Site map

| What | URL | Notes |
|---|---|---|
| Product approval letters + approved products list | `/works/product-approval?page=0..26` | 27 pages |
| Approved consultants, renewals, enlistment policy | `/works/consultancy-miscellaneous` | 1 page |
| Contract policy letters | `/works-policies-data/contracts` | 1 page |
| Technical information | `/works-directorate-technical-information` | 1 page |
| Tenders | `/tenders` (~535 pages) | not queued: `gepnic-defproc` holds them |
| Contractor / consultant enlistment (CCEP) | `egov.mes.gov.in/CCEP/login` | **login** |
| Product approval portal (PAP) | `egov.mes.gov.in/PAP/login` | **login** |

## 6. How it is collected
- **Code:** `adapters/mes.py` reads each table row (columns and links) and downloads every attachment (`ctx.download`, with the
  `seen/` markers so unchanged files are not fetched again).
- **Queue:** 30 table pages plus weekly first pages (`<path>-<YYYY>w<WW>-p0`).
- **Pace:** 0.5 s minimum between requests, at most 2 workers.

## 7. The data
- Record id `<page>-<row hash>`. Fields: `path`, `page`, `columns` (as on the site), `urls`, `files` (stored PDFs with `path`, `pages`,
  `needs_ocr`, `text`).

| Page | Rows |
|---|---:|
| `works/product-approval` | 186 |
| `works-policies-data/contracts` | 10 |
| `works/consultancy-miscellaneous` | 7 |

```sql
select data->>'path', data->'columns', data->'files'->0->>'path' from public.records
where project = 'contractor-registration-mes-works' order by data->>'path', (data->>'page')::int;
```

## 8. Verification
- Tests: 49 passed. scrape-check through proxy `95.134.119.238` (2 Nov): a refused proxy makes the run exit with code 3 and claim nothing.
- Pool: 38 / 38 items done, 0 failed (4 Nov). The product-approval pages give 263 rows over 27 pages.
- **Not checked:** the approved-products PDF against the rows.

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | Pages not loaded through refused proxies (fixed 4 Nov) | 0 | `proxy_only` picks the accepted proxies. |
| 2 | Enlisted contractors are behind the CCEP login (at the source) | the whole enlistment | Not collectable without an MES account. |
| 3 | Scanned attachments not OCR'd (by decision) | few | Stored under `ocr-needed/` for later. |

## 10. Risks and open decisions
- **Risks:** only 2 of the hub's 10 proxies are accepted; if mes.gov.in drops those too, the weekly item waits (it does not fail).
- **To decide:** nothing open.

## 11. Next steps
**To do now:** none.
**Later:** 1. Read the approved-products and approved-consultants PDFs into rows (they have a text layer).
**Housekeeping:** none.
