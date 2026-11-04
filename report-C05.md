# C05: NHAI / MoRTH tenders, empanelment, ratings and debarment orders (nhai.gov.in, morth.gov.in)

**Status:** ✅ COMPLETE. **10,903** NHAI tenders (10,648 archive 2018–2025 + 255 live, daily), 243 NHAI page records, and **6,934** MoRTH
documents are stored. The re-fetch of the 2,789 archive documents stored empty (1,551 distinct links) ran on 2 Nov: **every one is
still empty at NHAI**, so this is a gap at the source.
**Updated:** 4 Nov 2026 09:55 CET · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@51547a2` (`main`)
**Projects:** `-nhai-tenders` (daily), `-nhai-tender-archive` (5 workers), `-nhai-pages` (weekly), `-morth-documents` (weekly).
All run on GitHub runners, direct, with no proxy (all names start with `contractor-registration`).
**Data:** `select … from public.records where project like 'contractor-registration-nhai-%'` / `'contractor-registration-morth-documents'` ·
bucket `contractor-registration-nhai-tender-archive/` etc. · [DATA.md](DATA.md)
**Previous report:** 2 Nov 2026 10:32 CET (re-fetch queued)

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **NHAI:** 10,648 archive tenders (2018–2025) and 251 live ones, each with its details and every document. **323** are empanelment calls.
  The ratings of DPR / AE-IE consultants and contractors are stored, along with **101** debarment rows.
- **MoRTH:** 6,934 orders, notices, circulars, gazettes and guidelines, including **38** debarment / blacklisting orders.
- **No captcha met:** both sites' JSON APIs are open. The planned-sources page's "captcha wall" does not apply to them.
- **Empty documents are empty at NHAI:** 2,789 archive documents (in 1,426 tenders, 1,551 distinct links) were stored as empty files in
  the first pass. All 58 re-fetch items ran (2 Nov, 18:55 CET) and each link still answered HTTP 200 with no body, so no record was
  added. They are listed as download failures; nothing more to do unless NHAI re-uploads them.
- About 48 GiB of documents are in the bucket (from the 1 Nov [DATA.md](DATA.md) report, not re-measured).

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-nhai-tenders` | ✅ COMPLETE | 38 / 38 | 0 · 0 · 0 | 255 | 16 | daily refresh |
| `-nhai-tender-archive` | ✅ COMPLETE | 281 / 281 | 0 · 0 · 0 | 10,648 | 58 | done (incl. 58 re-fetch items; 0 documents came back) |
| `-nhai-pages` | ✅ COMPLETE | 24 / 24 | 0 · 0 · 0 | 243 | 16 | weekly refresh |
| `-morth-documents` | ✅ COMPLETE | 90 / 90 | 0 · 0 · 0 | 6,934 | 17 | weekly refresh (new documents only) |

- The archive pass (29–30 Oct) made 62,835 requests and uploaded 66,274 files (50.6 GB). The site answered 54 × 503 and 2,690 × 404.
- The hub's health checks for nhai.gov.in / morth.gov.in fail from the hub's own server (since 30 Oct). No project names a probe, so work is not held.

## 3. Pick up here
- **Repo:** `~/contractor-registration` · **Run tests:** `~/.venvs/cr/bin/python -m pytest -q tests` · **Try one item:** these sites
  refuse the team box and some proxies, so test in CI (`check` workflow) or on a GitHub runner.
- **Next action:** none; the daily and weekly refreshes run on their own.
- **Waiting on:** nothing.

## 4. What stands out
1. **NHAI serves empty files for part of its archive.** 2,789 document links answer HTTP 200 with an empty body: 2,066 of them in the
   2020 archive (`tenderarchivetwe`), 425 in 2019, 297 in 2018, and 1 in 2022. A second try two days later gave the same for all
   1,551 distinct links. Downloads now refuse empty bodies, so they show as download failures, not as stored files.
2. **Only 22% of NHAI's archive tender numbers appear on CPPP** (846 of 3,824 matched `gepnic-etenders`; [DATA.md](DATA.md), 1 Nov).
   *So what:* this archive is the main record of NHAI's tenders, not a duplicate.
3. **323 empanelment calls** among the tenders: requests for empanelment of consultants, contractors and fee collection agencies,
   flagged `is_empanelment`.
4. **MoRTH's debarment group has 38 orders**, 21 of them scans waiting for OCR (off by decision; stored under `ocr-needed/`).

## 5. The source
- **NHAI:** Angular app with a Drupal backend. `POST nhai.gov.in/nhai/api/<endpoint>` with multipart fields (`tenderlist`,
  `tenderdetail`, 8 `tenderarchive*` endpoints, `rest_api`, `commontype`). GitHub runners reach it directly; the team box and some
  proxies do not.
- **MoRTH:** Angular app with a Laravel backend. `GET morth.gov.in/backend/api/<slug>?page=&per_page=` returns JSON.

### 5.1 Site map

| What | Endpoint | Notes |
|---|---|---|
| Live tenders | `tenderlist` | ~242 live; read daily, 8 pages of 50 |
| Tender details and documents | `tenderdetail` (`nid`) | dates, tender no, document links |
| Archive 2018–2025 | `tenderarchive`, `…nin`, `…twe`, `…tweone`, `…twetwo`, `…twethree`, `…twefour`, `…twefive` | ~10,900 tenders |
| Ratings, debarment, standard documents | `rest_api` (`nid=publication-rating-dpr-consultants`, …) | 7 CMS pages |
| Blacklisted / debarred firms | `commontype` (`tid=blacklisted-debarred-firms`) | also a Power BI embed (no table behind it) |
| MoRTH documents | `backend/api/orders-and-notices` and 7 more slugs | 6,972 documents listed |

## 6. How it is collected
- **Code:** `adapters/nhai.py` (`run_tenders`, `run_page`, `run_commontype`, and `run_refetch`), `adapters/morth.py` (pages of
  100 documents; `new_only` skips the ids in `queues/morth_known.txt.gz`), `adapters/common.py` (downloads with `seen/` markers).
- **Queue:** archive `<endpoint>-p<k>` (223); live `tenders-<YYYYMMDD>-p<k>` daily; pages `-<YYYY>w<WW>` weekly; re-fetch
  `refetch-<endpoint>-<hash>` (58 items of up to 50 documents, from `tools/build_queues.py`).
- **Decision (Claude, 30 Oct 2026):** the archive is capped at 5 of the 8 workers per target, leaving room for the live tenders.

## 7. The data
- Records: `tender-<nhai id>` (fields `title`, `tender_no`, `publish_date`, bid dates, `is_empanelment`, `detail`, `documents[]` with
  `stored` file info and text); `page-<nid>`, `<nid>-row-…`, `<nid>-doc-…`; MoRTH `<slug>-<doc id>` with `group`, `title`, dates,
  `contractor_related`, `file`.
- Files: `pdf/…` (with `.pdf.txt` text), `ocr-needed/…` (scans), `docs/…` (other formats).

```sql
select data->>'tender_no', data->>'title', data->>'publish_date' from public.records
where project = 'contractor-registration-nhai-tender-archive' and (data->>'is_empanelment')::bool order by data->>'publish_date' desc;
select data->>'published_date', data->>'title' from public.records
where project = 'contractor-registration-morth-documents' and data->>'group' ilike '%debar%';
```

## 8. Verification
- Tests: 42 passed (NHAI list / detail / pages, MoRTH lists, `new_only`, the re-fetch handler). CI `check` runs scrape-check against
  both sites on every push (green, 2 Nov).
- Cross-checks: the archive items reported 10,924 tenders and 10,648 distinct ids are stored, so 276 tenders appear in two archive
  years (not checked one by one). MoRTH: 6,934 of the 6,972 documents its pages list are stored; the other 38 are not explained yet.
- Re-fetch (2 Nov): 58 / 58 items done, 0 documents loaded, 1,551 download failures (empty body).
- **Not checked:** the 276 tenders listed in two archive years one by one.

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | **Documents empty at NHAI** (at the source; re-fetched 2 Nov) | 2,789 refs / 1,551 links | Nothing to fetch; recheck only if NHAI re-uploads. |
| 2 | Documents that did not load (404 at the source, mostly) | 552 NHAI, 20 MoRTH | Listed on the dashboard. |
| 3 | Files over 80 MB not stored (by rule) | 17 | Links kept. |
| 4 | Scans not OCR'd (by decision) | 16,205 scans | `ocr-needed/`; OCR later. |

## 10. Risks and open decisions
- **Risks:** none for running now.
- **To decide:** when to turn on OCR (`OCR = True` in `family.py`).

## 11. Next steps
**To do now:** none.
**Later:** 1. OCR the debarment scans. 2. Match tenders to awards on CPPP (`gepnic-etenders`).
**Housekeeping:** none (the hub's health checks go through proxies since 3 Nov).
