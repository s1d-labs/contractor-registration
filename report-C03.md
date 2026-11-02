# C03: MES approved products, consultants and works policy (mes.gov.in)

**Status:** ⚠️ STALLED. 23 of 38 items are done (**203** rows). The other 15 fail because mes.gov.in answers only 2 of the hub's
proxy ranges. The fix is in PR #7. The contractor enlistment itself (CCEP) is login-only.
**Updated:** 2 Nov 2026 10:32 CET · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@685c82a` (`main`);
proxy fix on `proxy-check-nhai-refetch` @ `5d02ff5` (PR #7, open)
**Projects:** `contractor-registration-mes-works` (adapter `mes`, target `mes.gov.in`, `proxy="IN"`, 2 workers)
**Data:** `select … from public.records where project = 'contractor-registration-mes-works'` · bucket `contractor-registration-mes-works/`
**Previous report:** first report

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **203 rows stored**: 186 product-approval rows, 10 contract-policy letters and 7 consultancy rows, plus their PDFs. The PDFs include the
  consolidated list of approved products and the list of approved consultants.
- **15 items failed** with "site did not answer". mes.gov.in answers only proxies in `91.124.42.x`: 221 records came through
  `.191` / `.193`, while `191.219.20.x` and `95.134.119.x` gave 0 records and about 1,000 connection errors.
- **Fix (PR #7):** a run that borrowed a proxy the site refuses now gives it back without claiming items, so items stop using
  up their 40 attempts.
- MES **enlistment** (CCEP) and **product approval** (PAP) portals are login-only. MES tenders are already in `gepnic-defproc`.

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-mes-works` | ⚠️ STALLED | 23 / 38 | 15 · 0 · 0 | 203 | 23 | after PR #7 and setup, when an `91.124.42.x` proxy is free |

- Of the 15 failed items, 11 used all 41 tries (`works-product-approval-p3, p5, p8, p9, p10, p15, p18, p21`, `…-technical-information-p0`,
  `…-contracts-p0`, and last week's `…-technical-information-2026w44-p0`). Four of this week's refresh items have 4 tries each.
  The daily setup resets failed items (`reset_failed=True`).
- Nothing new since 2 Nov 00:23 CET.

## 3. Pick up here
- **Repo:** `~/contractor-registration` · **Run tests:** `~/.venvs/cr/bin/python -m pytest -q tests` · **Try one item:**
  `myproxy run ~/.venvs/cr/bin/python crawl.py --local mes '{"path": "works/product-approval", "page": 3, "files": true}'`.
  Check the exit IP first (`myproxy run curl -s https://api.ipify.org`): only `91.124.42.x` works.
- **Next action:** merge PR #7, then run setup. Then watch for `proxy` failures on scrape.s1d.me.
- **Waiting on:** Sarthak, on whether `191.219.20.x` / `95.134.119.x` were banned by mes.gov.in, and whether a project can ask for specific proxies.

## 4. What stands out
1. **The site picks proxies.** Per exit IP since 1 Nov: `91.124.42.191` gave 174 records and `.193` gave 47. `191.219.20.105` / `.177` / `.178` / `.199`
   and `95.134.119.235` / `.238` / `.254` gave 0 records and 1,006 connection errors between them. It fails at the TLS handshake (client
   hello sent, no answer), which looks like a block on those ranges rather than an outage. *So what:* proxy choice matters per site;
   PR #7 stops wasting tries.
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
- Tests: 42 passed. scrape-check through proxy `95.134.119.238` (2 Nov): with PR #7 the run exits with code 3, claims nothing,
  and the hub accepts its `proxy` failure.
- **Not checked:** the 15 missing pages' content (they never loaded).

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | **Pages not loaded: proxies refused** (missed by us) | 15 items | PR #7, then setup; ask Sarthak about proxy choice. |
| 2 | Enlisted contractors are behind the CCEP login (at the source) | the whole enlistment | Not collectable without an MES account. |
| 3 | Scanned attachments not OCR'd (by decision) | few | Stored under `ocr-needed/` for later. |

## 10. Risks and open decisions
- **Risks:** with only 2 of 10 proxies accepted and 4 proxies for the whole family, MES can wait a long time for a proxy it can use.
- **To decide (Sarthak):** a way for a project to name the proxies it needs (or exclude ranges).

## 11. Next steps
**To do now:** 1. Merge PR #7, then run setup. 2. Ask Sarthak about the refused ranges.
**Later:** 3. Read the approved-products and approved-consultants PDFs into rows (they have a text layer).
**Housekeeping:** none.
