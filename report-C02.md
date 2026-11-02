# C02: State PWD / R&B registered contractors (Gujarat, Maharashtra; other states)

**Status:** ⏳ RUNNING. Gujarat is done (**9,421** contractors). Maharashtra is built and waiting for PR #7 (9,598 rows, mostly old
registrations). Rajasthan and Karnataka have no open list. The other states haven't been looked at.
**Updated:** 2 Nov 2026 10:32 CET · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@685c82a` (`main`);
Maharashtra on branch `proxy-check-nhai-refetch` @ `5d02ff5` (PR #7, open)
**Projects:** `contractor-registration-state-pwd` (adapter `statepwd`, target `rnb.gujarat.gov.in`, `proxy="IN"`, 1 worker);
`contractor-registration-state-pwd-maharashtra` (same adapter, target `cdnbbsr.s3waas.gov.in`, no proxy; after PR #7)
**Data:** `select … from public.records where project = 'contractor-registration-state-pwd'` · bucket `contractor-registration-state-pwd/pdf/<list>/`
**Previous report:** first report

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **Gujarat R&B: 9,421 records.** 8,087 civil contractors (the list as on 14-09-2026: 8,113 rows, of which 26 are exact repeats) and 1,334 electrical
  contractors (as on 31-07-2026). Each record has division, firm, address, class, type of firm, registration date and validity.
- **Maharashtra PWD:** the RTI manual (no. 13) publishes civil (893 pages, **8,966** rows) and electrical (112 pages, **632** rows) lists
  by district and class. The parser and project are done in PR #7. Most registrations listed were valid only up to **2013–2017**.
- **Rajasthan:** no public list; contractor registration runs through the state's SSO login. **Karnataka:** the contractor
  registration portal (`103.241.144.46:8089/crp/`) answers 502.
- **Next:** merge PR #7, then the remaining large states one at a time ([11](#11-next-steps)).

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-state-pwd` (Gujarat) | ✅ COMPLETE | 4 / 4 | 0 · 0 · 0 | 9,421 | 4 | monthly refresh |
| `-state-pwd-maharashtra` | 🛠 BUILDING | 0 / 4 (not on the hub yet) | — | — | — | the day PR #7 is merged |
| Other states | 🔍 EXPLORING | — | — | — | — | one discovery each |

- The Gujarat run took one proxy (`95.134.119.254`) and finished 4 items with 0 errors (2 Nov 09:04–09:07 CET).

| State | Department | What is public | Status |
|---|---|---|---|
| Gujarat | Roads & Buildings | civil (AA to E-2) and electrical (A to E-2) registers, PDF | ✅ collected |
| Maharashtra | PWD | civil and electrical registers in the RTI manual, PDF | 🛠 PR #7 |
| Rajasthan | PWD | nothing: sectoral portal app; registration via SSO login | ⛔ login only |
| Karnataka | PWD | "Contractor Registration" link to a portal on a bare IP (`/crp/`): HTTP 502 | ⚠️ down, retry |
| Uttar Pradesh, Bihar, Himachal, Madhya Pradesh | PWD | sites did not answer even from India (28 Oct) | ⚠️ retry |
| others | PWD / WRD / RWD / PHED | not looked at | 🔍 |

## 3. Pick up here
- **Repo:** `~/contractor-registration` · **Run tests:** `~/.venvs/cr/bin/python -m pytest -q tests` · **Try one list:**
  `~/.venvs/cr/bin/python crawl.py --local statepwd '{"list": "maharashtra-pwd-electrical"}'` (no proxy needed)
- **Next action:** merge PR #7 (adds `-state-pwd-maharashtra`). The next daily setup seeds it, or run Actions → setup.
- **Waiting on:** trideep (merge PR #7, and choose which states come next).

## 4. What stands out
1. **Maharashtra's published register is old.** The PDFs were uploaded in March 2025, but the "Registration Valid Upto" dates
   are mostly 2013–2017. *So what:* treat it as a historical register, and look for a current one (e-registration runs on a login portal).
2. **Gujarat lists renewals beside the old registration.** The same firm can appear with a 2024 and a 2026 registration
   (*M/s JNP Infrastructure*, Surat, AA). One Vadodara firm appears 4 times. Records keep each registration apart: 8,113 rows give 8,087 records.
3. **Gujarat: few lapsed entries.** 144 civil and 5 electrical registrations are past their validity, against
   1,010 of 9,736 for CPWD ([C01](report-C01.md)). Gujarat seems to prune its list.
4. **Maharashtra's biggest class is "Unemployed Engineers".** 3,486 of the 8,966 civil rows are class "Unemployed Engineers (VI class)",
   a reserved category for small works. 427 rows in Pune, Gondia and other districts have no firm name at all.
5. **Maharashtra lists have typos in their serial numbers** (a block numbered 3526–3537 in place of 3426–3437, and a jump of
   100 at 6450). Rows are read by position, so no row is lost.

## 5. The source
- **Gujarat:** `rnb.gujarat.gov.in` (home page 5.8 MB) links two PDFs printed from a spreadsheet, with a text layer. It answers
  Indian addresses only, including GitHub runners' (CI, 1 Nov), so the project uses `proxy="IN"`.
- **Maharashtra:** `pwd.maharashtra.gov.in` (S3WaaS WordPress) → *RTI manual no. 13: particulars of recipients of permits*. The files
  sit on `cdnbbsr.s3waas.gov.in`, a CDN that answers from anywhere (including the team box). Each PDF is uploaded twice under two names; we read one.

### 5.1 Site map

| What | URL | Notes |
|---|---|---|
| Gujarat civil list | `rnb.gujarat.gov.in/otherfile/Contractor Registration Final Data.pdf` | 236 pages, "as On 14-09-2026", stated total 8,113 |
| Gujarat electrical list | `rnb.gujarat.gov.in/otherfile/Aayog Electrical Contractor Registration Data.pdf` | 87 pages, "as on 31-07-2026" |
| Gujarat registration | `rnbcontractor.com` | contractor login |
| Maharashtra civil list | `cdnbbsr.s3waas.gov.in/s3ea80421fc06a2ed5c7adc1018e0026df/uploads/2025/03/202503152104805692.pdf` | 893 pages |
| Maharashtra electrical list | `…/uploads/2025/03/20250315163259010.pdf` | 112 pages |
| Maharashtra e-registration | `pwd.maharashtra.gov.in/en/service/e-registration-of-contractors/` | login portal |
| Karnataka registration | `http://103.241.144.46:8089/crp/` | 502 on 2 Nov |

## 6. How it is collected
- **Code:** `adapters/statepwd.py`. `page_words` reads each word with its position (pdfium, baseline y). `parse_list` handles Gujarat:
  columns come from where cells start, and rows from serial numbers. `parse_mh` handles Maharashtra: "District : X Class : Y" lines
  group the rows, the district count and serial number are paired per line, and phone, dates and EMD are recognised by shape and position.
- **Queue:** one item per list, plus a monthly copy (`<list>-<YYYY>m<MM>`). One request per item.
- **Decision (Claude, 2 Nov 2026):** record ids are content hashes, because the lists have no ids. Gujarat hashes firm, address,
  division, class and both dates; Maharashtra hashes district, class, contractor number, firm and validity.

## 7. The data
- Record ids: `gujarat-rnb-civil-<hash>`, `maharashtra-pwd-civil-<hash>`, etc. Each record also carries `state`, `list`, `pdf_path`, `url`, `source`.
- **Gujarat fields:** `division`, `company`, `address`, `class`, `nature_of_firm`, `registration_date`, `valid_upto` (`DD-MM-YYYY`), `list_as_on`.
- **Maharashtra fields:** `district`, `class`, `district_sr`, `contractor_number` (raw, e.g. `6993 dt 5/8/2009`), `registration_no`,
  `registered_on`, `company`, `address`, `phone`, `valid_upto`, `exempted_upto` (`D/M/YYYY`), `emd_exempted` (`Y`/`N`).
  **`phone` belongs to proprietors**: keep it out of published examples.

| Gujarat class | Civil | Electrical |
|---|---:|---:|
| AA | 689 | — |
| A | 643 | 310 |
| B | 580 | 125 |
| C | 1,266 | 81 |
| D | 878 | 156 |
| E-1 | 2,817 | 450 |
| E-2 | 1,214 | 212 |

```sql
select data->>'list', data->>'class', count(*) from public.records where project = 'contractor-registration-state-pwd' group by 1, 2 order by 1, 2;
select data->>'company', data->>'class', data->>'valid_upto' from public.records where project = 'contractor-registration-state-pwd'
  and to_date(nullif(data->>'valid_upto', ''), 'DD-MM-YYYY') < current_date;
```

## 8. Verification
- Tests: 42 passed, using one-page fixtures of each Gujarat PDF and two-page fixtures of each Maharashtra PDF.
- Cross-checks: Gujarat civil rows 1–8,113 contiguous and equal to the PDF's stated total. Maharashtra civil: 8,966 rows against a
  last serial of 9,065, explained by the two numbering slips in [4](#4-what-stands-out). Maharashtra electrical: 632 rows,
  from `scrape-check` with 629 distinct ids and the same ids on rerun.
- **Not checked:** Maharashtra rows against the PDF by eye beyond the first pages; whether a newer Maharashtra list exists elsewhere on the site.

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | **Most states not covered** (missed by us, so far) | ~30 states | One discovery each; see [11](#11-next-steps). |
| 2 | **Maharashtra list is old** (at the source) | 9,598 rows | Historical; look for the current register. |
| 3 | Maharashtra rows without a firm name (at the source) | 427 civil, 1 electrical | Kept; the address and number are still there. |
| 4 | Gujarat blank cells (at the source) | 587 no firm type, 45 no registration date, 28 no validity | Kept as blanks. |
| 5 | Exact repeats collapse (at the source) | 26 Gujarat civil, 3 Maharashtra electrical | One record each. |

## 10. Risks and open decisions
- **Risks:** both parsers depend on the PDF layout. A re-laid-out list yields 0 rows and fails the item (`hub.failure("parse", …)`)
  rather than storing shifted columns.
- **To decide (trideep):** the next states. Recommendation: Tamil Nadu, Andhra Pradesh, Telangana and West Bengal PWD next (large
  road budgets, and these states often publish lists). Retry UP / Bihar / MP once their sites answer.

## 11. Next steps
**To do now:** 1. Merge PR #7. 2. Retry Karnataka's `/crp/` portal and the UP / Bihar / MP PWD sites through a proxy.
**To decide:** 3. Which states next (above).
**Later:** 4. WRD / RWD / PHED departments, which keep separate registers in several states. 5. Join firms across Gujarat,
Maharashtra, CPWD ([C01](report-C01.md)) and PMGSY ([C06](report-C06.md)).
**Housekeeping:** none.
