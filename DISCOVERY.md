# Discovery notes (2026-10-28, updated 2026-10-29)

Checked through an Indian exit (Delhi VPS, SOCKS tunnel). The team box's own IP (Contabo, France) is dropped at TCP level by all of these hosts.

## Reachability

| Host | From France (team box) | From Delhi VPS |
|---|---|---|
| morth.gov.in, nhai.gov.in, mes.gov.in, rdso.indianrailways.gov.in, eprocure.gov.in | blocked | OK |
| cems.cpwd.gov.in, ireps.gov.in, egov.mes.gov.in | blocked | OK |
| cpwd.gov.in | blocked | **blocked** (HTTP 302 on :80, TLS reset on :443; real Chrome too) |
| pmgsy.nic.in | blocked | **blocked** (SOCKS/TCP times out) |
| omms.nic.in, ommas.nic.in | no DNS | no DNS (real OMMAS hostname unknown) |

GitHub Actions runners **reach nhai.gov.in and morth.gov.in** (check workflow, 2026-10-28: scrape-check all PASS on a GitHub runner;
the pool has been collecting from both since 2026-10-29 16:20 UTC), and so do the hub's health checks (MoRTH 23/23, NHAI 22/23 in
the first 30 minutes). **mes.gov.in does not answer GitHub runners** (2026-10-29: every request a connection error), so MES is not in the pool; `adapters/mes.py` is ready for an Indian runner.
CPWD and PMGSY from runners are not tested yet.

## Family verdict

| Pair | Verdict | Why |
|---|---|---|
| MoRTH + NHAI | **Same look, not the same platform** | Both are Angular hash-route SPAs, but different builds and backends. NHAI: older Angular (webpack), Drupal backend, `POST https://nhai.gov.in/nhai/api/<endpoint>` with multipart form fields. MoRTH: Angular 17+ (esbuild), Laravel backend, `GET https://morth.gov.in/backend/api/<page-slug>?page=&per_page=` returning JSON. Two adapters, one shared "SPA + JSON" helper at most. |
| MES + CPWD | **Not a family** | mes.gov.in is Drupal 11 (server-rendered tables, `?page=N`, PDFs). CPWD enlistment is CEMS, ASP.NET WebForms (`__VIEWSTATE` postbacks). Different platforms. |
| RDSO | Own thing | Legacy JSP CMS (`view_section.jsp?id=0,5,...`); the vendor data lives on IREPS (Struts). |

No pair shares a platform, so the "family = one platform" rule does not hold for these four. The practical choice is to keep this repo as a topical multi-adapter family (one project per site, a `parse_*` module per site) or split per platform later.

## Scopes found

1. **CPWD enlistment lists**: no public list of enlisted contractors found. CEMS (`cems.cpwd.gov.in`) exposes rule books 2020-2026 (PDFs on cpwd.gov.in, blocked), circulars (ASP.NET postbacks), the category/class matrix (Buildings & Roads: Special, I Super, I AAA, I AA, I A, I-V; Horticulture: I A, I-IV), and an eligibility calculator (`CheckEligibility.aspx`, ddlCategory/ddlClass). The contractor list is behind login. cpwd.gov.in itself is unreachable.
2. **State PWD / WRD / RWD / PHED**: not on any of these four sites; each state needs its own discovery.
3. **MES**: mes.gov.in has `/tenders` (~535 pages x 10, title/start/end/PDF), `/works/product-approval` (~26 pages of approval letters + "list of approved products as on 15 Oct 2026" PDF: firm, product, approval letter, valid-up-to; it has a text layer), `/works/consultancy-miscellaneous` (consolidated list of approved consultants, PDF, Aug 2025; renewal letters; enlistment policy Feb 2025). The enlistment portal CCEP (`egov.mes.gov.in/CCEP/login`) and Product Approval Portal (`/PAP/login`) are login-only.
4. **RDSO / railway vendors**: RDSO's UVAM link goes to IREPS `cvapApprovalofVendorAnony.jsp`. The vendor directory (`vndrDirectoryAnon.do`) and item master (`viewItemMasterAnon.do`) need a guest mobile number + OTP, so they are not scrapeable without sign-in. Open: `itemVendorCountReport.do` (item/vendor counts per directorate, no names). Not yet checked: RDSO "list of items with few sources" (`view_section.jsp?lang=1&id=0,5,6634`).
5. **NHAI / MoRTH**:
   - NHAI `tenderlist` (242 live, fields: id, title, publish_date, tender_no, bid end/opening dates); `get_category` (vid=tenderdepartment/tendercategory); `commontype` (tid=blacklisted-debarred-firms: a Power BI embed + the internal page "individuals/agencies debarred by MoRTH/NHAI/NHIDCL/PWDs"); `rest_api` (nid=publication-rating-dpr-consultants: DPR/AE/IE consultant and contractor ratings); contract-management circulars.
   - MoRTH `orders-and-notices`: 2,177 documents, including a 38-document "Related to Debarment and Blacklisting" group and suspension/speaking orders naming firms. MoRTH tenders link out to eprocure / World Bank portals; no empanelment table.
6. **PMGSY OMMAS**: unreachable (pmgsy.nic.in blocked, omms.nic.in no DNS). A web search found no public contractor/PAN report; a parliamentary reply says no central blacklist is kept (states hold them).

## What the family scrapes now (family.py)

| Project | Site | Queue | Records | Files |
|---|---|---|---|---|
| `contractor-registration-nhai-tenders` | nhai.gov.in | 6 pages of `tenderlist` (242 live) | one per tender with `tenderdetail` (dates, tender no, documents) and an `is_empanelment` flag | all tender documents |
| `contractor-registration-nhai-tender-archive` | nhai.gov.in | 223 pages over 8 archive endpoints (2018-2025, ~10,900 tenders); at most 5 of the 8 nhai.gov.in workers | as above | all tender documents (~3.5 MB a tender) |
| `contractor-registration-nhai-pages` | nhai.gov.in | 7 CMS pages + `commontype` blacklisted-debarred-firms | ratings documents (DPR, AE/IE, contractor), debarment orders (date, order no, subject), standard RFP/RFQ documents, procurement manual, NHAI web-application catalogue (links) | all linked documents |
| `contractor-registration-morth-documents` | morth.gov.in | 74 items (8 document pages, ~100 documents an item) | one per document: group, title, dates, wing, circular no, URL, `contractor_related` flag | every document (~7,000) |

Files are stored in the family bucket under `<project>/`:

```
pdf/<section>/<hash8>-<name>.pdf          PDFs with a text layer
pdf/<section>/<hash8>-<name>.pdf.txt      their whole extracted text (the record keeps the first 20,000 characters)
ocr-needed/<section>/<hash8>-<name>.pdf   scanned PDFs: no text layer, kept for a later OCR pass
docs/<section>/<hash8>-<name>.<ext>       doc, docx, xls, xlsx, zip, ...
```

The record of each stored file has `path`, `sha256`, `bytes`, `pages`, `needs_ocr`, `text_path`, `text_chars` and `text`.
What has been collected, how to query it and what it shows: [DATA.md](DATA.md).

## Status (2026-10-29)

- Registered on the hub (setup, 16:18 UTC): 4 projects, 311 queue items, 2 health checks. Bucket `s1d-labs-trideep`.
- First hour: 6,611 MoRTH documents and 3,829 NHAI archive tenders; 29,918 files (21.4 GiB) in the bucket.
- NHAI tender numbers are mostly not on CPPP: 846 of 3,824 archive tenders match `gepnic-etenders` (22%).
- Fixes waiting in PR #4: NUL characters in PDF text made the hub refuse record batches (6 MoRTH items retrying); runs no longer
  start an item in their last 15 minutes; the archive is capped at 5 workers so the live tenders and the ratings / debarment
  pages start.

## Login-only sections (links only, not scraped)

| Site | What is behind it | Link |
|---|---|---|
| CPWD CEMS | contractor enlistment applications and enlisted list | https://cems.cpwd.gov.in/ContractorLogin.aspx, https://cems.cpwd.gov.in/OfficerLogin.aspx |
| MES CCEP | contractor & consultant enlistment portal | https://egov.mes.gov.in/CCEP/login |
| MES PAP | product approval portal | https://egov.mes.gov.in/PAP/login |
| MES e-governance | budget, e-cashbook, e-measurement book, project monitoring, estimates, assets | https://mes.bisag-n.gov.in/ (BMP, ECB, EMB, WBPMP, WEA, DWAP/login) |
| MES department | site admin / department login | https://mes.gov.in/user/login, https://hrmciv.mes.gov.in/Common/Login.aspx |
| IREPS UVAM (RDSO vendors) | approved vendor directory and item master (guest login with mobile OTP) | https://ireps.gov.in/epsn/cvap/admintab/vndrDirectoryAnon.do?activity=displayFirst&approvAgencyCode=-2, https://ireps.gov.in/epsn/cvap/admintab/viewItemMasterAnon.do |
| IREPS | vendor / officer login | https://ireps.gov.in/epsn/jsp/admin/home/logon.jsp |
| NHAI | complaint registration | https://complaint.nhai.org/complaintsregistration/loginpage.aspx |

## Next scopes

- MES tenders: not queued, `gepnic-defproc` already has them (7 of 7 sampled CPPP ids, 552,817 MES records). The `mes` adapter reads
  `tenders` pages too (`{"path": "tenders", "page": N}`) if they are ever needed.

- IREPS open report: item/vendor counts per directorate (`itemVendorCountReport.do`).
- RDSO "list of items with few sources" (`view_section.jsp?lang=1&id=0,5,6634`).
- NHAI Power BI report of debarred contractors (public embed; no table behind the API).
- State PWD / WRD / RWD / PHED registers: one discovery per state.

## Open questions

- Do GitHub Actions runners reach cpwd.gov.in and pmgsy.nic.in?
- Real OMMAS public hostname.
- An Indian runner (e.g. a self-hosted GitHub Actions runner on an Indian VPS) would open mes.gov.in, and possibly cpwd.gov.in and
  pmgsy.nic.in, to the pool: does the hub accept runs from self-hosted runners?
