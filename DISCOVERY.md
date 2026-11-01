# Discovery notes (2026-10-28, updated 2026-11-01)

Checked through an Indian exit: a Delhi VPS (SOCKS tunnel) on 2026-10-28, the hub's Mumbai proxies (`myproxy`) on 2026-11-01.
The team box (Germany) is dropped at TCP level by all of these hosts.

## Reachability

| Host | Team box | Delhi VPS / Mumbai proxy | GitHub runners |
|---|---|---|---|
| morth.gov.in, nhai.gov.in | blocked | OK | OK (pool, 2026-10-29) |
| mes.gov.in | blocked | OK | **blocked**: the pool uses `proxy="IN"` |
| pmgsy.dord.gov.in (OMMAS citizen reports, the old omms.nic.in) | blocked | OK | not tested: the pool uses `proxy="IN"` |
| rdso.indianrailways.gov.in, eprocure.gov.in, cems.cpwd.gov.in, ireps.gov.in, egov.mes.gov.in, emarg.gov.in, pmgsytenders.gov.in | blocked | OK | not tested |
| cpwd.gov.in | blocked | **blocked** (TLS reset; real Chrome too) | not tested |
| pmgsy.nic.in, omms.dord.gov.in, geosadak-pmgsy.nic.in | blocked | **blocked** (times out / proxy 502) | not tested |
| omms.nic.in, ommas.nic.in | no DNS | no DNS | |

**The hub's health checks** run from the hub's own server, which these sites have not answered since 2026-10-30 02:00 CET (every
India-only target on scrape.s1d.me fails, other families' too). A failing probe holds a project's work, so this family's projects
name no probe; the checks stay registered for the dashboard. The hub owner can fix it by checking India-only targets through a proxy.


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
6. **PMGSY OMMAS**: the citizen reports moved to **pmgsy.dord.gov.in** (`/Home/CitizenPage`). Proposals → *Contractor
   Information* is the **contractor master** per state, filterable by contractor status (Active / Inactive / **Blacklisted** /
   Expired): company, contact person, state registration number, address, phones, e-mail and PAN (masked by the site: first five
   and last character). It is an SSRS report with a CSV export (four requests a state and status; `adapters/pmgsy.py`). Sizes:
   Uttar Pradesh 4,897 active, Sikkim 519; Assam lists 15 blacklisted, Bihar / MP / Rajasthan / Odisha / Maharashtra none.
   Same site, not yet scraped: Work Awarded → *Agreement Details* (works with their contractor and agreement value; filters
   state / district / year / batch / scheme), the dashboard's *KPI Based Contractors' Performance* (`/dbweb`), quality-monitor
   grading abstracts. The officials' OMMAS is login-only (`pmgsygov.dord.gov.in`).

## What the family scrapes now (family.py)

| Project | Site | Queue | Records | Files |
|---|---|---|---|---|
| `contractor-registration-nhai-tenders` | nhai.gov.in | 6 pages of `tenderlist` (242 live) | one per tender with `tenderdetail` (dates, tender no, documents) and an `is_empanelment` flag | all tender documents |
| `contractor-registration-nhai-tender-archive` | nhai.gov.in | 223 pages over 8 archive endpoints (2018-2025, ~10,900 tenders); at most 5 of the 8 nhai.gov.in workers | as above | all tender documents (~3.5 MB a tender) |
| `contractor-registration-nhai-pages` | nhai.gov.in | 7 CMS pages + `commontype` blacklisted-debarred-firms | ratings documents (DPR, AE/IE, contractor), debarment orders (date, order no, subject), standard RFP/RFQ documents, procurement manual, NHAI web-application catalogue (links) | all linked documents |
| `contractor-registration-morth-documents` | morth.gov.in | 74 items (8 document pages, ~100 documents an item); weekly: each page once, new documents only | one per document: group, title, dates, wing, circular no, URL, `contractor_related` flag | every document (~7,000) |
| `contractor-registration-mes-works` | mes.gov.in via Indian proxy | 30 table pages (product approval, consultancy, contract policy, technical information) + weekly first pages | one per table row with its columns | every attachment (approved products list, approved consultants, enlistment policy, approval letters) |
| `contractor-registration-pmgsy-contractors` | pmgsy.dord.gov.in via Indian proxy | 37 states x 4 statuses, again every month | one per contractor (company, person, registration no, address, phones, e-mail, masked PAN, status) | the CSV export per state and status |
| `contractor-registration-ocr` | the family bucket | 485 batches of ~250 pages (16,081 scans, 111,705 pages; `queues/ocr.json.gz`) | one per scan: source project and path, the records that cite it, OCR text | `<source project>/<path>.txt` |

The live NHAI tenders are read every day (`tenders-<YYYYMMDD>-p<k>`), the NHAI pages every week. Projects with `OCR=1` read
scans with tesseract as they store them.

Files are stored in the family bucket under `<project>/`:

```
pdf/<section>/<hash8>-<name>.pdf          PDFs with a text layer
pdf/<section>/<hash8>-<name>.pdf.txt      their whole extracted text (the record keeps the first 20,000 characters)
ocr-needed/<section>/<hash8>-<name>.pdf   scanned PDFs: no text layer, kept for a later OCR pass
docs/<section>/<hash8>-<name>.<ext>       doc, docx, xls, xlsx, zip, ...
```

The record of each stored file has `path`, `sha256`, `bytes`, `pages`, `needs_ocr`, `text_path`, `text_chars` and `text`.
What has been collected, how to query it and what it shows: [DATA.md](DATA.md).

## Status (2026-11-01)

- 2026-10-29/30: the first pass finished: all 311 queue items done but one MoRTH item (`public-notices-part5`, whose list request
  failed for three hours and used up its 40 tries; setup now resets such items). 17,978 records, 63,686 files (48 GiB) in the bucket.
- NHAI tender numbers are mostly not on CPPP: 846 of 3,824 archive tenders match `gepnic-etenders` (22%).
- 2026-11-01: MES back in the pool through the Indian proxies; PMGSY contractor master added; OCR of the 16,081 stored scans
  queued; daily / weekly / monthly refresh; documents unchanged on the site are not fetched again.

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

- PMGSY *Agreement Details* (contractor → road works awarded, agreement value) and *KPI Based Contractors' Performance*: same site
  and the same SSRS export as the contractor master.
- pmgsytenders.gov.in is a GePNIC portal that no family scrapes yet: a fit for the `gepnic` family (its owner adds the portal).
- MES tenders: not queued, `gepnic-defproc` already has them (7 of 7 sampled CPPP ids, 552,817 MES records). The `mes` adapter reads
  `tenders` pages too (`{"path": "tenders", "page": N}`) if they are ever needed.
- IREPS open report: item/vendor counts per directorate (`itemVendorCountReport.do`).
- RDSO "list of items with few sources" (`view_section.jsp?lang=1&id=0,5,6634`).
- NHAI Power BI report of debarred contractors (public embed; no table behind the API).
- State PWD / WRD / RWD / PHED registers: one discovery per state.

## Open questions

- cpwd.gov.in resets connections from every Indian exit tried (Delhi VPS, Mumbai proxies, real Chrome): down, or blocking more than
  foreign IPs. Its rule books and enlistment notices would be worth a project once it answers.
- Answered: the OMMAS public reports are on pmgsy.dord.gov.in; India-only sites run in the pool through `proxy="IN"` (no
  self-hosted runner needed).
