# C02: State PWD / R&B / PHED registered contractors (8 states)

**Status:** ⏳ RUNNING. Seven states are stored, about 58,600 records in total:
- **Uttarakhand** 36,409, with the firm PAN on 33,824;
- **Gujarat** 9,421;
- **Maharashtra** 9,504;
- **Tripura** 1,488 of 1,539;
- **Arunachal Pradesh** 1,276 contractors and 48 documents;
- **Haryana** 297;
- **Odisha** 76.

**West Bengal PHED** has 26 scanned lists (OCR later). The rest of Tripura comes in on the next daily setup. About 20 other states
publish no list, keep it behind a login, or do not answer from India.
**Updated:** 4 Nov 2026 16:20 CET · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@51547a2` (`main`);
new states `24d7efa` (PR #9, merged 4 Nov 10:01 CET)
**Projects:** `contractor-registration-state-pwd` (Gujarat), `-state-pwd-maharashtra`, `-state-pwd-wb`, `-state-pwd-uttarakhand`,
`-state-pwd-tripura`, `-state-pwd-arunachal`, `-state-pwd-haryana`, `-state-pwd-odisha`. All use adapter `statepwd`, 1 worker each;
`proxy="IN"` except Maharashtra (CDN) and Arunachal, which answer from anywhere.
**Data:** `select … from public.records where project like 'contractor-registration-state-pwd%'` · bucket `contractor-registration-state-pwd*/`
**Previous report:** 4 Nov 2026 09:50 CET (five new states merged and queued)

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **Stored (hub, 4 Nov 16:20 CET):**
  - **Uttarakhand PWD** runs an open online register: **36,409 applications** in classes A–D, with office, firm, address,
    category, status, registration number and validity. **33,874 have registration granted**. The registration number ends in
    the **firm's full PAN** (33,824 records, **15,157 different PANs**).
  - **Gujarat R&B** 9,421 and **Maharashtra PWD** 9,504 (8,875 civil + 629 electrical, mostly registrations from 2013–2017).
  - **Tripura PWD (R&B):** 1,488 of 1,539 enlisted contractors in classes I–V and electrical, with tender limits.
  - **Arunachal Pradesh PWD:** 1,276 valid enlisted civil contractors (as on 30-09-2026), and 48 linked documents. Among the
    documents are **21 orders that cancel registrations**.
  - **Haryana PWD:** 297 Class-1 contractors (list for 2014–2020; the PDF gives 5 firms twice). **Odisha Works:** 76.
  - **West Bengal PHED:** 26 approved-vendor lists (scans, kept in the bucket for OCR later).
- **PAN join:** **183** Uttarakhand firms are also in the PMGSY contractor scores ([C06](report-C06.md)), by full PAN.
- **Tripura certificates are not reliable at the source.** The 806 "View PDF" links lead to only 287 different files; one
  file is linked from 26 rows. The scanner's text layer is unreadable on 664 of 714 stored files, so they go to the OCR queue.
- **No usable list:** Kerala, Himachal Pradesh and Rajasthan keep registration behind a contractor login; Karnataka's portal
  answers 502. PWD sites of 16 states (UP, Bihar, MP, Punjab, AP, Telangana, WB PWD and others) don't answer through any of the
  hub's Indian proxies.
- **Next:** nothing to do. The daily setup (02:30 CET) resets the two failed Tripura items; they store the last 51 rows.

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-state-pwd` (Gujarat) | ✅ COMPLETE | 4 / 4 | 0 · 0 · 0 | 9,421 | 0 | monthly refresh |
| `-state-pwd-maharashtra` | ✅ COMPLETE | 4 / 4 | 0 · 0 · 0 | 9,504 | 4 | monthly refresh |
| `-state-pwd-wb` (WB PHED) | ✅ COMPLETE | 2 / 2 | 0 · 0 · 0 | 26 lists | 2 | monthly; OCR later |
| `-state-pwd-uttarakhand` | ✅ COMPLETE | 8 / 8 | 0 · 0 · 0 | 36,409 | 36,409 | monthly refresh |
| `-state-pwd-tripura` | ⏳ RUNNING | 0 / 2 | 2 · 0 · 0 | 1,488 | 1,488 | 5 Nov, after the daily setup resets the items |
| `-state-pwd-arunachal` | ✅ COMPLETE | 5 / 8 | 3 · 0 · 0 | 1,324 | 1,324 | monthly refresh (the 3 failed items have done twins) |
| `-state-pwd-haryana` | ✅ COMPLETE | 2 / 2 | 0 · 0 · 0 | 297 | 297 | monthly refresh |
| `-state-pwd-odisha` | ✅ COMPLETE | 4 / 4 | 0 · 0 · 0 | 76 | 76 | monthly refresh |

| State | Department | What is public | Status |
|---|---|---|---|
| Gujarat | Roads & Buildings | civil and electrical registers, PDF | ✅ stored |
| Maharashtra | PWD | civil and electrical registers in the RTI manual, PDF (old) | ✅ stored |
| West Bengal | PHED | approved vendor lists, 26 scanned PDFs | ✅ stored (OCR later) |
| Uttarakhand | PWD | online register of every application, classes A–D, HTML report | ✅ stored |
| Tripura | PWD (R&B) | enlisted contractors per class, HTML tables + certificate PDFs | ⏳ 1,488 of 1,539 |
| Arunachal Pradesh | PWD | valid enlisted contractors, classes IAA–III, PDF; cancellation orders | ✅ stored |
| Haryana | PWD (B&R) | Class-1 enlisted list 2014–2020, PDF (the search form needs a full name) | ✅ stored |
| Odisha | Works | contractor ledger (Super / Special / A / B, electrical MV / HT) | ✅ stored |
| Rajasthan | PWD | nothing open; registration via SSO login | ⛔ login only |
| Kerala | PWD | contractors' portal (`contractors.kerala.gov.in`): login only | ⛔ login only |
| Himachal Pradesh | PWD | online enlistment (`online.hppwd.gov.in/enlistment`): login only | ⛔ login only |
| Karnataka | PWD | registration portal on a bare IP (`/crp/`): HTTP 502 on 2 and 4 Nov | ⚠️ down |
| Tamil Nadu | Highways | site answers (4 Nov) but has no contractor list | 🔍 nothing found |
| Meghalaya, Delhi, Goa | PWD | tenders only / nothing found | 🔍 nothing found |
| UP, Bihar, MP, Punjab, AP, Telangana, WB PWD, Chhattisgarh, Jharkhand, Assam, J&K, Manipur, Nagaland, Sikkim, Puducherry, Haryana (old host) | PWD / RCD | sites don't answer through any of the hub's proxies (4 Nov) | ⚠️ unreachable |

## 3. Pick up here
- **Repo:** `~/contractor-registration` · **Run tests:** `~/.venvs/cr/bin/python -m pytest -q tests` (50 pass) · **Try one list:**
  `myproxy run ~/.venvs/cr/bin/python crawl.py --local statepwd '{"uk_class": "B"}'`, or without a proxy
  `~/.venvs/cr/bin/python crawl.py --local statepwd '{"columns": "arunachal-pwd-class-ii"}'`
- **Next action:** none. The daily setup resets the two failed Tripura items.
- **History:** the first attempts (4 Nov 10:09–12:08 CET) failed with `KeyError: 'list'`. Two runner jobs had checked out `main`
  at 08:54, before the merge, and used all 40 attempts. The setup re-run at 15:10 CET reset the items; new jobs stored them.
  Tripura's first try then failed on a hub error (502 on `upload-urls`), and its second try used up the runner's time budget.
- **Waiting on:** the daily setup (5 Nov 02:30 CET).

## 4. What stands out
1. **Uttarakhand publishes PANs.** The registration number of every granted application is `<class><office><category><month-year>:<PAN>`
   (for example `B1006RD0822:` followed by the PAN). Of 33,874 granted registrations, 33,782 carry a valid PAN (15,151 different firms). *So what:* this is the
   one state register that joins exactly to PMGSY ([C06](report-C06.md)) and to other PAN-keyed data: 183 firms match.
2. **Uttarakhand's register is mostly small contractors.** Class D holds 29,777 of 36,409 applications; class A has 1,945. About 6,000
   class-D registrations run out in 2026.
3. **One Uttarakhand application, many offices.** An application sent to several circles appears once per office (one class-D
   application is listed under 6 offices). Records keep one row per application with all its offices.
4. **Arunachal publishes its cancellations.** The page links 21 office orders cancelling a contractor's registration (2021–2025) and
   8 orders extending one; most are scans. *So what:* a small state-level debarment list, beside CPWD's ([C01](report-C01.md)).
5. **Tripura states each class's tender limit** ("Any amount" for class I, "up to ₹6 crore" for class II, ₹1–1.5 crore for class IV),
   and 789 of its 1,539 rows are class V (services), mostly valid only until 2020.
6. **Tripura's certificate links point to the wrong files.** 806 rows link a certificate, but only 287 different files are linked.
   For example, the row for enlistment 00852 links the file 00851.pdf, and 26 rows link that same file. *So what:* do not use a
   Tripura certificate as proof for its row without a check of the number printed on it (after OCR).
7. **Maharashtra's published register is old.** The PDFs went up in March 2025, but the validity dates are mostly 2013–2017.

## 5. The source
- **Uttarakhand:** `registrationpwd.uk.gov.in` (ASP.NET). `Report/Contractor_Information.aspx?contractor=A|B|C|D` returns the whole
  class as one table with no sign-in. The server needs TLS legacy renegotiation, which OpenSSL 3 refuses by default (handled in code).
- **Tripura:** `pwd.tripura.gov.in/enlistment-of-contractors-2/` (WordPress / Elementor): one accordion section per class, each a
  table; certificates under `/wp-content/uploads/enlistment_uploads/`.
- **Arunachal:** `arunachalpwd.org/contractors.php` links the lists (`pdf/06102026/Class-…-ason-30092026.pdf`, text layer) and the orders.
- **Haryana:** `haryanapwd.gov.in/home/docs/Contractor List.pdf` (10 pages, numbered entries). **Odisha:** `works.odisha.gov.in/en/more/contractor-ledger/civil|electrical` (Drupal view, filter per class).
- **Gujarat, Maharashtra, West Bengal PHED:** as in the previous report (PDFs on `rnb.gujarat.gov.in`, `cdnbbsr.s3waas.gov.in`, `wbphed.gov.in`).
- All `.gov.in` hosts here answer Indian addresses only; `arunachalpwd.org` and the S3WaaS CDN answer from anywhere.

### 5.1 Site map

| What | URL | Notes |
|---|---|---|
| Uttarakhand register | `registrationpwd.uk.gov.in/Report/Contractor_Information.aspx?contractor=D` | 91 MB for class D; dashboard counts on `/Dashboard.aspx` |
| Uttarakhand certificate | `…/Certificate.aspx?appl_no=<n>` | per contractor; not fetched (36k requests) |
| Tripura enlisted | `pwd.tripura.gov.in/enlistment-of-contractors-2/` | 2 MB page, 11 tables |
| Arunachal lists | `arunachalpwd.org/pdf/06102026/Class-IAA-I-A_I-ason-30092026.pdf`, `…Class-II-…`, `…Class-III-…` | 27 / 55 / 85 pages |
| Arunachal class IV, V lists | `arunachalpwd.org/pdf/16102023/list_registered_contractors-classIV.pdf` etc. | scans: stored, OCR later |
| Haryana Class-1 list | `haryanapwd.gov.in/home/docs/Contractor%20List.pdf` | 302 entries |
| Haryana search | `haryanapwd.gov.in/enlistment/search_contracter` | needs a full contractor name |
| Odisha ledger | `works.odisha.gov.in/en/more/contractor-ledger/civil?field_civil_contractor_value=1..4` | 20 rows a page |
| WB PHED vendors | `wbphed.gov.in/en/approved-vendor-list` | 26 scanned PDFs |

## 6. How it is collected
- **Code:** `adapters/statepwd.py`, one mode per kind of source: `parse_list` / `parse_mh` (PDF tables by word position: Gujarat,
  Maharashtra), `parse_uk` (Uttarakhand report), `parse_accordion_tables` (Tripura), `parse_columns` (Arunachal: column edges from
  each page's header words, rows from serial numbers, carried over page breaks), `parse_numbered` (Haryana), `parse_ledger` (Odisha),
  `parse_doc_table` / `parse_pdf_links` (documents to store: WB PHED, Arunachal orders). `adapters/common.py` speaks legacy TLS to Uttarakhand.
- **Queue:** one item per list, class or page, plus a monthly copy (`<item>-<YYYY>m<MM>`). Documents are fetched once (`seen/` markers).
- **Decision (Claude, 4 Nov 2026):** Uttarakhand records are keyed by application number, with offices merged; other lists without
  ids use content hashes (class, enlistment number, firm).
- **Decision (Claude, 4 Nov 2026):** Uttarakhand's per-contractor certificate pages are not fetched (one request each, 36k); the
  report already carries the registration number and validity.

## 7. The data
- Record ids: `gujarat-rnb-civil-<hash>`, `maharashtra-pwd-civil-<hash>`, `uttarakhand-pwd-<application no>`, `tripura-pwd-enlisted-<hash>`,
  `arunachal-pwd-class-ii-<hash>`, `haryana-pwd-class1-<hash>`, `odisha-works-civil-<hash>`; documents `wb-phed-approved-vendors-<hash>`,
  `arunachal-pwd-documents-<hash>`. Every record has `state`, `list`, `url`, `source`.
- **Uttarakhand:** `application_no`, `applied_date`, `offices[]`, `company`, `address`, `class`, `category` (Road, Building, Bridge,
  Electrical, Mechanical, …), `status`, `timeline`, `registration_no`, `pan`, `valid_upto`.
- **Tripura:** `section`, `enlistment_no`, `contractor`, `father_or_partner`, `address`, `valid_from`, `valid_upto`, `qualified_upto`, `certificate`.
- **Arunachal:** `class`, `company`, `address`, `enlistment_no`, `enlistment_date`, `valid_upto`, `remarks`, `list_as_on`.
- Names, fathers' names, phones, e-mails and addresses of proprietors are personal data: keep them out of published examples.

| Uttarakhand class | Applications | Granted |
|---|---:|---:|
| A | 1,944 | 1,681 |
| B | 816 | 678 |
| C | 3,870 | 3,481 |
| D | 29,770 | 28,018 |

```sql
-- Uttarakhand registrations granted, by class and category
select data->>'class', data->>'category', count(*) from public.records
where project = 'contractor-registration-state-pwd-uttarakhand' and data->>'status' = 'Registration Granted' group by 1, 2 order by 1, 3 desc;
-- Uttarakhand firms that are also PMGSY contractors (the PMGSY scores give the full PAN; 183 firms on 4 Nov)
select u.data->>'company', p.data->>'company', p.data->>'state' from public.records u
join public.records p on p.project = 'contractor-registration-pmgsy-contractors' and p.data->>'kind' = 'contractor_kpi'
 and p.data->>'pan' = u.data->>'pan'
where u.project = 'contractor-registration-state-pwd-uttarakhand' and u.data->>'pan' ~ '^[A-Z]{5}[0-9]{4}[A-Z]$';
```

## 8. Verification
- Tests: 50 passed, with fixtures for every format (hand-made names in the new ones).
- Pool runs (4 Nov, after 15:10 CET): Uttarakhand 36,409 (per class 1,945 / 816 / 3,871 / 29,777), Arunachal 1,276 + 48, Haryana
  297 ids from 302 rows (the PDF lists serials 11/63, 28/48, 141/147, 202/219 and 233/246 with the same text), Odisha 76, Tripura 1,488.
- scrape-check through an Indian proxy: Uttarakhand class A, 1,944 records, the same ids on rerun.
- Local runs (4 Nov): Uttarakhand B 816, Odisha 45 + 31, Arunachal class II 410 and 48 documents (9 links dead), Haryana 302 (serials
  1–302 contiguous), Tripura 1,539 rows.
- Cross-checks: Uttarakhand granted counts per class equal the site's dashboard (1,681 / 678 / 3,481 / 28,018 in the morning;
  28,034 in class D in the afternoon); Arunachal serials run
  without gaps in each class (I: 1–8, 1–8, 1–179; II: 1–410; III: 1–671), and every row has an enlistment date and validity.
- **Not checked:** Tripura's class V rows against anything (their validity dates are mostly 2020); Maharashtra beyond the first pages.

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | **States without an open list** (at the source) | ~20 states | Login portals or no answer from India; recheck the unreachable ones monthly. |
| 2 | **Scans not read** (by decision, OCR later) | 26 WB lists, 12 Arunachal files, 236 Tripura certificates | In the bucket; queued in `queues/ocr.json.gz` for the OCR project. |
| 3 | Maharashtra list is old (at the source) | 9,504 rows | Historical; the current one is behind e-registration. |
| 4 | Haryana list ends in 2020 and gives one text per entry (at the source) | 302 | Firm and address are not split. |
| 5 | Uttarakhand granted rows without a PAN (at the source) | 92 | Registration number kept as is. |
| 7 | **Tripura certificate links point to other rows' files** (at the source) | 806 links, 287 files | Check the number on the certificate after OCR. |
| 8 | Tripura certificates carry an unreadable scanner text layer (at the source) | 664 of 714 records | Now detected (`common.readable`) and queued for OCR. |
| 9 | Tripura rows not stored yet (runner time budget) | 51 of 1,539 | The daily setup resets the items. |
| 6 | Arunachal links that are dead (at the source) | 9 of 48 | 404; listed as download failures. |

## 10. Risks and open decisions
- **Risks:** Uttarakhand class D is one 91 MB answer; if the site starts timing out, the item fails rather than storing part of it.
  The PDF parsers fail an item (`hub.failure("parse", …)`) on a new layout rather than shift columns.
- **To decide (trideep):** whether to fetch Uttarakhand's 36k certificate pages (one per contractor; adds little beyond the report).

## 11. Next steps
**To do now:** 1. Check on 5 Nov that Tripura has 1,539 records.
**Later:** 2. OCR the WB PHED, Arunachal and Tripura scans (the `contractor-registration-ocr` project, when OCR is turned on). 3. Recheck Karnataka `/crp/` and the 16 unreachable
states monthly. 4. WRD / RWD / PHED registers in the states that answer. 5. Join state registers to PMGSY ([C06](report-C06.md)) by PAN
(Uttarakhand) and by name and district (the rest).
**Housekeeping:** none.
