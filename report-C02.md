# C02: State PWD / R&B / PHED registered contractors (8 states)

**Status:** ⏳ RUNNING. **Gujarat** (9,421 contractors), **Maharashtra** (9,504) and **West Bengal PHED** (26 scanned vendor lists) are stored.
Five more states are merged (PR #9) and queued; the pool's runner jobs that started before the merge ran old code, so they fill
after those jobs end (setup re-run ~15:00 CET, or the daily setup at 02:30 CET): **Uttarakhand** (36,400 applications, 33,858 registered, firm PAN on each),
**Tripura** (1,539), **Arunachal Pradesh** (1,276 plus 48 orders), **Haryana** (302) and **Odisha** (76). About 20 other states publish
no list, keep it behind a login, or don't answer from India.
**Updated:** 4 Nov 2026 09:50 CET · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@51547a2` (`main`);
new states `24d7efa` (PR #9, merged 4 Nov 10:01 CET)
**Projects:** `contractor-registration-state-pwd` (Gujarat), `-state-pwd-maharashtra`, `-state-pwd-wb`, `-state-pwd-uttarakhand`,
`-state-pwd-tripura`, `-state-pwd-arunachal`, `-state-pwd-haryana`, `-state-pwd-odisha`. All use adapter `statepwd`, 1 worker each;
`proxy="IN"` except Maharashtra (CDN) and Arunachal, which answer from anywhere.
**Data:** `select … from public.records where project like 'contractor-registration-state-pwd%'` · bucket `contractor-registration-state-pwd*/`
**Previous report:** 2 Nov 2026 10:32 CET (Gujarat stored, Maharashtra built)

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **Stored (hub, 4 Nov):** Gujarat R&B **9,421**, Maharashtra PWD **9,504** (8,875 civil + 629 electrical, mostly registrations from
  2013–2017), West Bengal PHED **26** approved-vendor lists (scans, saved in the bucket for OCR later).
- **Built, tested and queued (PR #9 merged; about 39,600 more records):**
  - **Uttarakhand PWD** runs an open online register: **36,400 applications** in classes A–D, with office, firm, address, category,
    status, registration number and validity. **33,858 have registration granted**, and their registration number ends in the
    **firm's full PAN**.
  - **Tripura PWD (R&B):** 1,539 enlisted contractors in classes I–V and electrical, with tender limits; 806 rows link an
    enlistment certificate PDF, all stored.
  - **Arunachal Pradesh PWD:** 1,276 valid enlisted civil contractors (as on 30-09-2026), plus 48 linked documents, among them
    **21 orders cancelling registrations**.
  - **Haryana PWD:** 302 Class-1 contractors (list for 2014–2020). **Odisha Works:** 76 (45 civil in Super, Special, A and B
    classes; 31 electrical).
- **No usable list:** Kerala, Himachal Pradesh and Rajasthan keep registration behind a contractor login; Karnataka's portal
  answers 502. PWD sites of 16 states (UP, Bihar, MP, Punjab, AP, Telangana, WB PWD and others) don't answer through any of the
  hub's Indian proxies.
- **Next:** nothing to do: the items retry. If any is still failed tomorrow morning, check `last_error` in `public.queue`.

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-state-pwd` (Gujarat) | ✅ COMPLETE | 4 / 4 | 0 · 0 · 0 | 9,421 | 0 | monthly refresh |
| `-state-pwd-maharashtra` | ✅ COMPLETE | 4 / 4 | 0 · 0 · 0 | 9,504 | 4 | monthly refresh |
| `-state-pwd-wb` (WB PHED) | ✅ COMPLETE | 2 / 2 | 0 · 0 · 0 | 26 lists | 2 | monthly; OCR later |
| `-state-pwd-uttarakhand` | 🛠 BUILDING | 0 / 8 | 0 · 8 · 0 | — | — | after the stale runner jobs (class D is one 91 MB page) |
| `-state-pwd-tripura` | 🛠 BUILDING | 0 / 2 | 2 failed (old code), retried | — | — | after the stale runner jobs |
| `-state-pwd-arunachal` | 🛠 BUILDING | 0 / 8 | 8 failed (old code), retried | — | — | after the stale runner jobs |
| `-state-pwd-haryana` | 🛠 BUILDING | 0 / 2 | 2 failed (old code), retried | — | — | after the stale runner jobs |
| `-state-pwd-odisha` | 🛠 BUILDING | 0 / 4 | 4 failed (old code), retried | — | — | after the stale runner jobs |

| State | Department | What is public | Status |
|---|---|---|---|
| Gujarat | Roads & Buildings | civil and electrical registers, PDF | ✅ stored |
| Maharashtra | PWD | civil and electrical registers in the RTI manual, PDF (old) | ✅ stored |
| West Bengal | PHED | approved vendor lists, 26 scanned PDFs | ✅ stored (OCR later) |
| Uttarakhand | PWD | online register of every application, classes A–D, HTML report | 🛠 PR #9 |
| Tripura | PWD (R&B) | enlisted contractors per class, HTML tables + certificate PDFs | 🛠 PR #9 |
| Arunachal Pradesh | PWD | valid enlisted contractors, classes IAA–III, PDF; cancellation orders | 🛠 PR #9 |
| Haryana | PWD (B&R) | Class-1 enlisted list 2014–2020, PDF (the search form needs a full name) | 🛠 PR #9 |
| Odisha | Works | contractor ledger (Super / Special / A / B, electrical MV / HT) | 🛠 PR #9 |
| Rajasthan | PWD | nothing open; registration via SSO login | ⛔ login only |
| Kerala | PWD | contractors' portal (`contractors.kerala.gov.in`): login only | ⛔ login only |
| Himachal Pradesh | PWD | online enlistment (`online.hppwd.gov.in/enlistment`): login only | ⛔ login only |
| Karnataka | PWD | registration portal on a bare IP (`/crp/`): HTTP 502 on 2 and 4 Nov | ⚠️ down |
| Tamil Nadu | Highways | site answers (4 Nov) but has no contractor list | 🔍 nothing found |
| Meghalaya, Delhi, Goa | PWD | tenders only / nothing found | 🔍 nothing found |
| UP, Bihar, MP, Punjab, AP, Telangana, WB PWD, Chhattisgarh, Jharkhand, Assam, J&K, Manipur, Nagaland, Sikkim, Puducherry, Haryana (old host) | PWD / RCD | sites don't answer through any of the hub's proxies (4 Nov) | ⚠️ unreachable |

## 3. Pick up here
- **Repo:** `~/contractor-registration` · **Run tests:** `~/.venvs/cr/bin/python -m pytest -q tests` (49 pass) · **Try one list:**
  `myproxy run ~/.venvs/cr/bin/python crawl.py --local statepwd '{"uk_class": "B"}'`, or without a proxy
  `~/.venvs/cr/bin/python crawl.py --local statepwd '{"columns": "arunachal-pwd-class-ii"}'`
- **Next action:** none. First attempts (10:09–10:50 CET) failed with `KeyError: 'list'`: two runner jobs had checked out `main`
  at 08:54, before the merge. New jobs check out the new code.
- **Waiting on:** the pool's next runner jobs.

## 4. What stands out
1. **Uttarakhand publishes PANs.** The registration number of every granted application is `<class><office><category><month-year>:<PAN>`
   (for example `B1006RD0822:` followed by the PAN). Of 33,858 granted registrations, 33,768 carry a PAN. *So what:* this is the
   one state register that joins exactly to PMGSY ([C06](report-C06.md)) and to other PAN-keyed data.
2. **Uttarakhand's register is mostly small contractors.** Class D holds 29,770 of 36,400 applications; class A has 1,944. About 6,000
   class-D registrations run out in 2026.
3. **One Uttarakhand application, many offices.** An application sent to several circles appears once per office (one class-D
   application is listed under 6 offices). Records keep one row per application with all its offices.
4. **Arunachal publishes its cancellations.** The page links 21 office orders cancelling a contractor's registration (2021–2025) and
   8 orders extending one; most are scans. *So what:* a small state-level debarment list, beside CPWD's ([C01](report-C01.md)).
5. **Tripura states each class's tender limit** ("Any amount" for class I, "up to ₹6 crore" for class II, ₹1–1.5 crore for class IV),
   and 790 of its 1,539 rows are class V (services), mostly valid only until 2020.
6. **Maharashtra's published register is old.** The PDFs went up in March 2025, but the validity dates are mostly 2013–2017.

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
-- Uttarakhand firms that are also PMGSY contractors (PMGSY masks the PAN: first five and last character)
select u.data->>'company', p.data->>'company', p.data->>'state' from public.records u
join public.records p on p.project = 'contractor-registration-pmgsy-contractors' and p.data->>'kind' = 'contractor_kpi'
 and p.data->>'pan' = u.data->>'pan'
where u.project = 'contractor-registration-state-pwd-uttarakhand' and u.data->>'pan' <> '';
```

## 8. Verification
- Tests: 49 passed, with fixtures for every format (hand-made names in the new ones).
- scrape-check through an Indian proxy: Uttarakhand class A, 1,944 records, the same ids on rerun.
- Local runs (4 Nov): Uttarakhand B 816, Odisha 45 + 31, Arunachal class II 410 and 48 documents (9 links dead), Haryana 302 (serials
  1–302 contiguous), Tripura 1,539 rows.
- Cross-checks: Uttarakhand granted counts per class equal the site's dashboard (1,681 / 678 / 3,481 / 28,018); Arunachal serials run
  without gaps in each class (I: 1–8, 1–8, 1–179; II: 1–410; III: 1–671), and every row has an enlistment date and validity.
- **Not checked:** Tripura's class V rows against anything (their validity dates are mostly 2020); Maharashtra beyond the first pages.

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | **States without an open list** (at the source) | ~20 states | Login portals or no answer from India; recheck the unreachable ones monthly. |
| 2 | **Scans not read** (by decision, OCR later) | 26 WB lists, ~40 Arunachal orders / old lists | Stored in the bucket under `ocr-needed/`. |
| 3 | Maharashtra list is old (at the source) | 9,504 rows | Historical; the current one is behind e-registration. |
| 4 | Haryana list ends in 2020 and gives one text per entry (at the source) | 302 | Firm and address are not split. |
| 5 | Uttarakhand granted rows without a PAN (at the source) | 90 | Registration number kept as is. |
| 6 | Arunachal links that are dead (at the source) | 9 of 48 | 404; listed as download failures. |

## 10. Risks and open decisions
- **Risks:** Uttarakhand class D is one 91 MB answer; if the site starts timing out, the item fails rather than storing part of it.
  The PDF parsers fail an item (`hub.failure("parse", …)`) on a new layout rather than shift columns.
- **To decide (trideep):** whether to fetch Uttarakhand's 36k certificate pages (one per contractor; adds little beyond the report).

## 11. Next steps
**To do now:** 1. Check the five new projects' counts tomorrow against [2](#2-where-things-stand).
**Later:** 2. OCR the WB PHED and Arunachal scans (with the family's OCR switch). 3. Recheck Karnataka `/crp/` and the 16 unreachable
states monthly. 4. WRD / RWD / PHED registers in the states that answer. 5. Join state registers to PMGSY ([C06](report-C06.md)) by PAN
(Uttarakhand) and by name and district (the rest).
**Housekeeping:** none.
