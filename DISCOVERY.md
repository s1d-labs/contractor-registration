# Discovery notes: contractor, vendor and empanelment registers (internal)

Internal, consolidated notes for the whole family: sites, reachability, logins, decisions. **The reports to publish are one per
planned source:** [C01 CPWD](report-C01.md) · [C02 State PWD](report-C02.md) · [C03 MES](report-C03.md) · [C04 RDSO / IREPS](report-C04.md)
· [C05 NHAI / MoRTH](report-C05.md) · [C06 PMGSY](report-C06.md) (updated 4 Nov 2026). The snapshot below is from 1 Nov 2026; the
reports are newer.

**14 Nov 2026 (latest):**
- Box moved to dev-vps-3 (8 CPU, 12 GB RAM, 80 GB disk; 12 GB used). Bucket 142.9 GiB of 500 GB. `~/.venvs/cr` works; 55 tests pass.
- The **setup** workflow was `disabled_manually` (scheduled runs stopped after 9 Nov; last change 13 Nov 16:53 IST, the time of
  Sarthak's manual run after PR #13). Enabled again and run on 14 Nov (trideep's instruction). The other 37 family repos had theirs on.
- PR #12 (Sarthak: actions v6, .gitignore) merged. PR #13 (Sarthak: PMGSY road register, eMARG) was merged on 13 Nov.
- **Tripura complete:** 1,518 ids from 1,539 rows (21 rows repeat). All five new C02 states are complete.
- **PMGSY road register:** corenetwork 473 / 792 districts (563,510 rows), completed 480 / 1,584 (43,874), emarg 74 / 74 (86,463),
  maintenance 0 / 1,036 (waits: the family borrows at most 4 proxies, and the other three projects hold them).
- **Fix:** `pmgsyreg` raised `ValueError` ("reached report None") when OMMAS answered its error page. Rajasthan / Banswara's
  completed-roads list gives that page for every block row. Now a `site` failure and a retry. An error page at an upper level
  failed silently before (item done, 0 rows); now the item fails.
- **New scope, D03 (PSU ban and holiday lists):** no family covered it. Adapter `banlists` (pdfplumber tables, HTML tables), projects
  `-banlists` (BHEL debarred 19 and banned 131, Oil India 92, OPaL 11, NHPC 11, NDDB 6; these answer from Germany) and
  `-banlists-in` (proxy: BPCL holiday list 121, show-cause list 53, HPCL holiday list 12 from `purchase-procurement`). Weekly refresh.
  Left out: MIDHANI (a new PDF each month with no fixed page; it repeats MoD's bans), BDL (newest list 2022), Mazagon Dock (no
  list on its page), ONGC, GAIL, NTPC, POWERGRID,
  Coal India, SAIL, HAL, EIL, NMDC (nothing found on their home pages), MoD (the page moved).
- **D04 (state medical corporations' blacklists), same adapter:** TNMSC `blacklisted/blacklisted.php` (11: drugs and equipment),
  RMSC company-wise 8 and product-wise 101, GMSCL `black-list-firm.htm` 10; all answer from Germany. KMSCL, BMSICL, MPPHSCL,
  TSMSIDC, CGMSC, OSMC: no list found on the home page (or no answer).
- **C02 recheck (14 Nov, through a proxy):** MP PWD answers again (4 Nov: no answer), but shows no public list (registration
  is a login system). UP, Punjab, WB PWD, Assam and Maharashtra WRD still time out. Karnataka's home page answers.

**4 Nov 2026:**
- PR #8 squash-merged (`51547a2`) and setup run: proxied projects back in the pool, MES on `proxy_only=["91.124.42."]`.
- **MES complete** (38/38, 290 rows). **PMGSY KPI stored:** 7,087 contractor scores with full PAN (6,978 match the master by state +
  masked PAN). **WB PHED:** 26 scanned lists stored (OCR later). **NHAI re-fetch:** all 1,551 links still empty at NHAI (gap at source).
- **C02, five more states (PR #9 merged; stored 4 Nov after 15:10 CET):** Uttarakhand online register **36,409** (33,874 granted;
  PAN in the registration number on 33,824 records, 15,157 different PANs; **183 match the PMGSY scores** by full PAN; site needs TLS
  legacy renegotiation, handled in `common.legacy_tls`), Tripura **1,488 of 1,539** (rest after the daily setup), Arunachal **1,276
  + 48 documents** incl. 21 cancellation orders (answers without a proxy), Haryana Class-1 **297** (302 rows; 5 repeated in the PDF),
  Odisha Works **76**.
- **Stale runner jobs:** pool jobs that started before a merge run the old code until they end. On 4 Nov they used all 40 attempts
  of the new items (`KeyError: 'list'`) in two hours; a setup run (`reset_failed`) put them back. Ask Sarthak if a job can refetch
  `main` between assignments.
- **Tripura certificates (at the source):** 806 "View PDF" links lead to only 287 files (row 00852 links 00851.pdf; one file is
  linked from 26 rows). Their text layer is the scanner's failed OCR (unreadable on 664 of 714 records), not real text.
  `common.needs_ocr` now also flags a text layer with few word-like tokens (`common.readable` < 0.35), and `tools/build_queues.py`
  checks the state lists' files again: 236 Tripura, 26 WB PHED and 12 Arunachal files added to `queues/ocr.json.gz`.
- **C02 dead ends (4 Nov, through proxy 91.124.42.191):** login only: Kerala (`contractors.kerala.gov.in`), Himachal
  (`online.hppwd.gov.in/enlistment`), Rajasthan (SSO). Karnataka `/crp/` 502. Haryana's search form needs a full name. TN Highways
  answers but has no list. No answer: UP, Bihar (rcd), MP, Punjab, AP, Telangana, WB PWD, Chhattisgarh, Jharkhand, Assam, J&K, Manipur,
  Nagaland, Sikkim, Puducherry, `pwdharyana.gov.in`, `pwd.arunachal.gov.in`. Mizoram 403.
- **RDSO items:** pool runs get connection errors through all 10 proxies (4 Nov 08:58–09:37 CET), while the same proxy works from the
  box (scrape-check PASS, 133). PR #9 adds `geo="IN"`. If the India servers fail too, ask Sarthak about the runners' proxy path.
- **data.gov.in (OGD) catalogue, checked with trideep's key** (`/lists?filters[title]=…`, 27 keywords; the API answers through a proxy
  in ~1 s with curl, while Python requests hung): **no contractor, vendor or empanelment register.** Only Rajya Sabha answer tables
  (aggregates), e.g. "action taken against defaulting contractors/concessionaires" after bridge collapses (`bbc56ef3-…`), JJM
  complaints against contractors (`eaf326ff-…`), contract-labour licences to contractors (`7d6f9a62-…`). Not worth a project. The key
  stays in `~/.config/s1d/ogd.env` only.
- IREPS UVAM pull **on hold** (trideep, 3 Nov). Commits and PRs are written as trideep's (no Claude trailer) from 4 Nov.

Since 1 Nov: PR #6 merged and seeded (PMGSY works 207,187 records, Gujarat 9,421); MES answers only the `91.124.42.x` proxies
(PR #7 makes runs give back refused proxies); Maharashtra PWD lists parsed (PR #7); Rajasthan PWD has no public list (SSO login),
Karnataka's registration portal answers 502; `tools/ireps_vendors.py` signs in to IREPS with a person at the keyboard (PR #7);
PMGSY awarded cost repeats the package amount on each work in 24,629 packages (flagged in PR #7).

**Status (1 Nov):** ⏳ RUNNING. 5 of the 6 planned sources have their open data collected or ready; C04 (RDSO vendors) is ⛔ BLOCKED behind
an IREPS mobile-OTP sign-in, and MES (C03) stopped answering the proxies tonight.
**Updated:** 1 Nov 2026 21:28 CET · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@4de2805`
(branch `agreements-gujarat-rdso`, pushed, PR open; `main` = `79de30a`, PR #5)
**Projects:** `-nhai-tenders`, `-nhai-tender-archive`, `-nhai-pages`, `-morth-documents` (GitHub runners, direct);
`-mes-works`, `-cpwd-contractors`, `-pmgsy-contractors` (proxy `IN`); new on the branch, not on the hub yet: `-pmgsy-agreements`,
`-state-pwd`, `-rdso-items` (proxy `IN`). All names start with `contractor-registration`.
**Data:** `select … from public.records where project = 'contractor-registration-<…>'` · Metabase "Team data (scrape_hub)" ·
bucket `s1d-labs-trideep`, `contractor-registration-<…>/` · query guide: [DATA.md](DATA.md)
**Previous report:** first report in this format (the earlier discovery notes are folded into [5](#5-the-sources)).

---

## Contents
1. [TL;DR](#1-tldr)
2. [Where things stand](#2-where-things-stand) · [2.1 Per planned source](#21-per-planned-source-c01c06)
3. [Pick up here](#3-pick-up-here)
4. [What stands out](#4-what-stands-out)
5. [The sources](#5-the-sources) · [5.1 Reachability](#51-reachability) · [5.2 Site map](#52-site-map)
   · [5.3 Behind a login, OTP or key](#53-behind-a-login-otp-or-key)
6. [How it is collected](#6-how-it-is-collected)
7. [The data](#7-the-data)
8. [Verification](#8-verification)
9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues)
10. [Risks and open decisions](#10-risks-and-open-decisions)
11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **Collected (hub, 1 Nov 21:28 CET): 87,684 records** in 6 projects: PMGSY contractor master **59,843** (all 296 items done),
  CPWD enlisted contractors **9,736** + 9 debarred + 20 suspended, NHAI tenders **10,648** + 251 live, MoRTH documents **6,934**,
  NHAI pages 243.
- **Ready on the branch, tested end to end through an Indian proxy:** PMGSY works awarded (Sikkim 1,263, Uttar Pradesh 21,140
  works), Gujarat R&B registers (**8,113** civil + **1,334** electrical contractors), RDSO items with few sources (133 items).
- **Biggest problem:** `-mes-works` 0 / 34. Since about 20:54 CET mes.gov.in drops the TLS handshake from the hub's proxies
  (`site did not answer`, 340 connection errors). It answered the same proxies earlier today.
- **No captcha stands in the way of any open data here.** What is left is behind accounts: an IREPS guest login with mobile OTP
  (RDSO vendor names), CPWD and MES portal logins. See [5.3](#53-behind-a-login-otp-or-key).
- **Next:** trideep merges the PR, then runs Actions → setup (the three new projects go into the pool).

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-pmgsy-contractors` | ✅ COMPLETE | 296 / 296 | 0 · 0 · 0 | 59,843 | 296 | monthly refresh |
| `-cpwd-contractors` | ✅ COMPLETE | 114 / 114 | 0 · 0 · 0 | 9,765 | 114 | monthly refresh |
| `-nhai-tender-archive` | ✅ COMPLETE | 223 / 223 | 0 · 0 · 0 | 10,648 | 0 | done 30 Oct |
| `-nhai-tenders` | ✅ COMPLETE | 14 / 14 | 0 · 0 · 0 | 251 | 8 | daily refresh |
| `-nhai-pages` | ✅ COMPLETE | 16 / 16 | 0 · 0 · 0 | 243 | 8 | weekly refresh |
| `-morth-documents` | ✅ COMPLETE | 82 / 82 | 0 · 0 · 0 | 6,934 | 9 | weekly refresh |
| `-mes-works` | ⚠️ STALLED | 0 / 34 | 32 · 0 · 2 | 0 | 0 | none: site refuses the proxies |
| `-pmgsy-agreements` | 🛠 BUILDING | 0 / 74 (not seeded) | — | — | — | ~37 × 30 s after setup |
| `-state-pwd` | 🛠 BUILDING | 0 / 4 (not seeded) | — | — | — | minutes after setup |
| `-rdso-items` | 🛠 BUILDING | 0 / 2 (not seeded) | — | — | — | minutes after setup |

- `queue.fetched` vs stored: PMGSY 119,459 vs 59,843 and CPWD 21,162 vs 9,765, because the first pass and the monthly items both ran
  today and re-sent the same ids (upserts). Stored = the true count.
- The hub's health checks for nhai.gov.in and morth.gov.in fail (ConnectTimeout from the hub's own server, since 30 Oct). No project
  names a probe, so work is not held. Bucket: 63,686 objects / 48.0 GiB on 1 Nov (from the [DATA.md](DATA.md) report, not re-measured).

### 2.1 Per planned source (C01–C06)

| ID | Planned source | Done | What we have | Not done, and why |
|---|---|---|---|---|
| **C01** | CPWD enlistment lists (cpwd.gov.in) | ✅ | The register moved to **erp.cpwd.gov.in** (open): 9,736 enlisted contractors (name, address, state, category, class, enlistment date, valid up to, debarment / suspension dates, status), 9 debarred, 20 suspended for EMD declaration violations. Monthly refresh. | The order PDFs behind each row and the "non-CPWD debarred" list need a CPWD login. cpwd.gov.in itself resets every connection, Indian or not, so the DSR / manuals on it are out of reach. |
| **C02** | State PWD / WRD / RWD / PHED registrations | 🟡 1 state | **Gujarat R&B:** registered civil contractors, classes AA to E-2 (8,113, as on 14-09-2026) and electrical contractors (1,334, as on 31-07-2026): division, firm, address, class, type of firm, registration and validity dates. On the branch. | Every other state: one discovery each. UP, Bihar, HP and MP PWD did not answer even through Indian exits (28 Oct). Gujarat's online registration (`rnbcontractor.com`) is a login portal. |
| **C03** | MES enlistment (mes.gov.in) | 🟡 | Code done: approved products list and letters, consolidated approved consultants, enlistment policy, contract policy letters (34 table pages + weekly). | **0 stored:** mes.gov.in refuses the hub's proxies since 1 Nov ~20:54 CET. The contractor enlistment itself (CCEP) is login-only. MES tenders are already in `gepnic-defproc`. |
| **C04** | RDSO / railway approved vendor directories | ⛔ | RDSO's own lists of items with **fewer than 3** (25) / **fewer than 5** (107) approved sources and with **no Indian source** (1), as on 03.06.2024: item id, item, sub-item, vendor count. On the branch. | **Vendor names:** the directory is IREPS UVAM (`vndrDirectoryAnon.do`), which needs a guest sign-in with a mobile number and OTP. The open item / vendor count report (`itemVendorCountReport.do`) now redirects to the login too. |
| **C05** | NHAI / MoRTH empanelment | ✅ | NHAI tenders 2018-2026 (10,648 archive + 251 live, daily), consultant and contractor rating documents, NHAI debarment orders, MoRTH's 6,934 documents including the "debarment and blacklisting" group. 314 empanelment calls, 100 NHAI debarment rows and 38 MoRTH debarment orders per the [DATA.md](DATA.md) report. No captcha met: the JSON APIs are open. | NHAI's Power BI report of debarred firms (no table behind it). Scanned orders wait for OCR (16,081 scans in `ocr-needed/`, OCR off on purpose). |
| **C06** | PMGSY OMMAS contractor master | ✅ | Moved to **pmgsy.dord.gov.in** (citizen reports). Contractor master of all 37 states × 4 statuses: **59,843** contractors (59,319 active, 329 inactive, 164 expired, **31 blacklisted**), PAN on 56,988 (masked by the site: first five and last character). Monthly. **New on the branch:** every work awarded per state (package, road, sanction date, sanctioned and awarded cost) and works awarded then terminated. | omms.nic.in is dead. The public reports never name the contractor of a work, so works and contractors cannot be joined from public data. The officials' OMMAS (`pmgsygov.dord.gov.in`) is login-only. |

## 3. Pick up here
- **Repo:** `~/contractor-registration` (branch `agreements-gujarat-rdso`, clean) · **Run tests:** `~/.venvs/cr/bin/python -m pytest -q tests`
  (37 pass) · **Try one item:** `myproxy run ~/.venvs/cr/bin/python crawl.py --local statepwd '{"list": "gujarat-rnb-electrical"}'`
- **Next action:** merge the PR for `agreements-gujarat-rdso`, then Actions → setup (or `gh workflow run setup.yml --ref main`).
- **Waiting on:** trideep (merge); Sarthak, the hub owner (health checks through a proxy; the family's proxy cap, 4, is below
  what its 6 proxied projects ask for); whether to sign in to IREPS for C04 ([10](#10-risks-and-open-decisions)).

## 4. What stands out
1. **PMGSY blacklists are concentrated.** 31 blacklisted contractors in all of India: 15 in Assam, 13 in Jharkhand, 2 in Arunachal
   Pradesh, 1 in Uttarakhand. Madhya Pradesh (6,169 contractors) and Bihar (5,553) list none.
   *So what:* the blacklist reflects which states use the status field, not where contractors misbehave.
2. **CPWD: 1,010 of 9,736 enlistments have lapsed** ("Enlistment Valid Upto" before today) but stay on the list. 30 rows carry a
   debarment date, though CPWD's own debarred list has 9. 379 rows have no status (the rest "Current").
3. **Gujarat lists renewals beside the old registration.** The same firm can appear with a 2024 and a 2026 registration (e.g.
   *M/s JNP Infrastructure*, Surat, class AA). One Vadodara firm appears 4 times. 26 civil rows are exact repeats and collapse to
   one record each: **8,087 distinct records from 8,113 rows**.
4. **One package, two bridges with the same name.** In Sikkim, package `SK03P7P11R` holds two 20 m bridges both called
   *Ramitey Khola* (₹201.19 and ₹190.47 lakh sanctioned). Work ids therefore include cost and length.
5. **RDSO: items with no alternative source.** Sub-items like the *Spring Auto tensioning device for 2400 kgf* (OHE) and the
   *25 W VHF digital radio set* have **0** approved vendors; the CCC copper wire rod (22.5–26 mm) has a single foreign source and
   no Indian one. The lists are dated 03.06.2024 and have not been updated since.
6. **The sites moved:** CPWD to erp.cpwd.gov.in, OMMAS to pmgsy.dord.gov.in. The planned-sources page still names the old hosts,
   which is why it shows C01 and C06 as unreachable.

## 5. The sources
- No source needs an API key. None showed a captcha on the parts collected. Every one except nhai / morth answers **Indian
  addresses only**. Rates seen: no 429s; NHAI answered 54 × 503 during the archive pass (29–30 Oct).

### 5.1 Reachability

| Host | Team box (DE) | Indian proxy | GitHub runners |
|---|---|---|---|
| nhai.gov.in, morth.gov.in | blocked | OK | OK |
| erp.cpwd.gov.in, pmgsy.dord.gov.in | blocked | OK | blocked: pool uses `proxy="IN"` |
| mes.gov.in | blocked | **refuses since 1 Nov ~20:54 CET** (TLS dropped after the client hello; OK earlier that day) | blocked |
| rnb.gujarat.gov.in, rdso.indianrailways.gov.in | blocked | OK | blocked (CI, 1 Nov): pool uses `proxy="IN"` |
| cpwd.gov.in | blocked | blocked (TLS reset, real Chrome too) | — |
| omms.nic.in, ommas.nic.in / pmgsy.nic.in, omms.dord.gov.in | no DNS / blocked | no DNS / blocked | — |

### 5.2 Site map

| Source | What | URL / form | Notes |
|---|---|---|---|
| C01 | Enlisted / debarred / suspended contractors | `erp.cpwd.gov.in/web/cpwd/list-of-cpwd-enlisted-debarred-contractors`, `…/list-of-suspended-contractors-due-to-violation-of-emd-declaration` | Liferay portlets, `_<portlet>_cur` / `_delta` (≤ 200) |
| C01 | Category / class matrix, eligibility | `cems.cpwd.gov.in/CheckEligibility.aspx` | open; the enlisted list on CEMS is login-only |
| C02 | Gujarat R&B civil / electrical lists | `rnb.gujarat.gov.in/otherfile/Contractor Registration Final Data.pdf`, `…/Aayog Electrical Contractor Registration Data.pdf` | PDFs with a text layer, re-published every few months |
| C03 | Approved products, consultants, policies | `mes.gov.in/works/product-approval?page=N`, `/works/consultancy-miscellaneous`, `/works-policies-data/contracts` | Drupal tables + PDFs |
| C04 | Items with few sources | `rdso.indianrailways.gov.in/view_section.jsp?lang=0&id=0,5,6634` | 3 PDFs (`/uploads/D_13403_…`) |
| C05 | NHAI tenders, pages | `POST nhai.gov.in/nhai/api/tenderlist`, `tenderdetail`, `tenderarchive*`, `rest_api`, `commontype` | multipart form fields |
| C05 | MoRTH documents | `GET morth.gov.in/backend/api/<slug>?page=&per_page=` | JSON |
| C06 | Contractor master | `pmgsy.dord.gov.in/MasterArea/Master/ContractorInformationLayout` → SSRS → CSV export | 4 requests per state × status |
| C06 | Works awarded / terminated | `…/WorkAwardedArea/WorkAwarded/TendAgrDetailsLayout` → state summary → drill-through on the Total row (`249iT0:0` awarded, `293iT0:0` terminated) → CSV | report viewer postback |
| C06 | Also open, not scraped | KPI contractors' performance (`/dbweb`), quality-monitor grading abstracts, Final Bill Payment (needs an agency choice) | aggregates |

### 5.3 Behind a login, OTP or key

What would open with an account, and what that account is. Nothing here is scraped. Signing in to automate collection needs the
account owner's go-ahead and should be checked against the site's terms first. Officer logins are for government staff and are out.

| Site | Gate | Who can get it | What it would add | Worth it? |
|---|---|---|---|---|
| **IREPS UVAM** (RDSO vendors, C04): `ireps.gov.in/epsn/cvap/admintab/vndrDirectoryAnon.do?activity=displayFirst&approvAgencyCode=-2`, `viewItemMasterAnon.do` | **guest sign-in: any mobile number + OTP** (no account) | anyone with an Indian mobile number | the approved vendor directory (vendor names per item and approving agency) and the item master: **the core of C04** | **Yes, the only route to C04 vendor names.** Each session needs a fresh OTP from the phone's owner (a manual step); the OTP itself cannot and should not be automated |
| IREPS vendor / officer login | user id + password (+ digital signature for bidding) | registered railway vendors / officials | the firm's own tenders and bids | No: own-firm data only |
| **CPWD ERP** (C01): order PDFs behind each row, "non-CPWD debarred" list | CPWD portal login | CPWD users (staff; registered contractors for their own records) | the debarment / suspension orders as documents | Low: the rows themselves are already open |
| CPWD CEMS: `cems.cpwd.gov.in/ContractorLogin.aspx`, `/OfficerLogin.aspx` | contractor or officer login | enlisted contractors (own application) / CPWD officers | own enlistment file; officers see all | No (own data / officers only) |
| **MES CCEP**: `egov.mes.gov.in/CCEP/login` | contractor / consultant account | firms applying for MES enlistment | the firm's own enlistment | No: no public enlisted list behind it |
| MES PAP: `egov.mes.gov.in/PAP/login` | firm account | product-approval applicants | own applications (the approved list is already open) | No |
| MES e-governance: `mes.bisag-n.gov.in/` (BMP, ECB, EMB, WBPMP, WEA, DWAP), `hrmciv.mes.gov.in` | department login | MES staff | internal budgets, measurement books | Out (officials) |
| PMGSY OMMAS (officials): `pmgsygov.dord.gov.in` | department login | PIU / SRRDA / NRIDA staff | works ↔ contractor link, payments | Out (officials) |
| Gujarat R&B registration: `rnbcontractor.com` | contractor account | firms registering with R&B | own registration | No: the register is already in the PDFs |
| **data.gov.in (OGD) API** | free API key (sign-up with e-mail) | anyone | checked 4 Nov with trideep's key (in `~/.config/s1d/ogd.env`): no contractor registers, only aggregate tables | No |
| NHAI complaints: `complaint.nhai.org/complaintsregistration/loginpage.aspx` | citizen login | anyone | own complaints | No |

**Captchas:** none of C01–C06's open data sits behind one. The planned-sources page marks NHAI as "captcha wall", but the
JSON API used here answers without one. The login portals above have captchas on their sign-in forms; those belong to the
login and are not to be solved automatically.

## 6. How it is collected
- **Code:** `crawl.py` (one task; `ADAPTER` env picks `adapters/<name>.py`); `adapters/common.py` (counted requests, document
  storage with `seen/<sha1>.json` markers so unchanged documents are not fetched twice, refuses empty files and login pages);
  `nhai.py`, `morth.py`, `mes.py`, `cpwd.py`, `pmgsy.py` (contractor master + works awarded), `statepwd.py` (state PDF registers,
  read by word position), `rdso.py`, `ocr.py` (off).
- **Queue:** one item = one page / list / state (× status). Keys carry the refresh period: `tenders-<YYYYMMDD>-p<k>` daily,
  `-<YYYYwNN>` weekly, `-<YYYYmMM>` monthly. Setup runs daily at 07:00 IST (`setup.yml` cron) and adds them.
- **Pace:** 0.5 s minimum between requests per worker, `max_workers` 2 per proxied project (1 for state-pwd and rdso). The family
  may borrow 4 proxies at once; its 6 proxied projects ask for up to 10, so they take turns.
- **Decision (trideep, 1 Nov 2026):** OCR stays off for now (load); scans wait in `ocr-needed/`.
- **Decision (Claude, 1 Nov 2026):** no project names a health check while the hub's prober cannot reach Indian sites.

## 7. The data
Record ids and fields per project: [DATA.md → Projects and record ids](DATA.md#projects-and-record-ids). Example (PMGSY work):
`30-awarded-…` → `{"state": "Sikkim", "district": "South", "block": "Namchi", "package": "SK03P7P11R", "work_type": "LSB",
"work_name": "Bhalkhara Khola", "bridge_length_m": "20.000", "sanction_cost_lakh": "195.17", "awarded_cost_lakh": "193.25"}`

| CPWD class | Contractors | | PMGSY state | Contractors |
|---|---:|---|---|---:|
| IV | 3,201 | | Madhya Pradesh | 6,169 |
| V | 2,281 | | Bihar | 5,553 |
| III | 2,015 | | Odisha | 5,348 |
| II | 976 | | West Bengal | 4,978 |
| I | 615 | | Assam | 2,954 |
| I(A) / I(AA) / I(AAA) / I(Super) | 229 / 198 / 96 / 106 | | Uttarakhand | 2,720 |

```sql
select data->'columns'->>'Class', count(*) from public.records
where project = 'contractor-registration-cpwd-contractors' and data->>'list' = 'contractors' group by 1 order by 2 desc;
select data->>'state', data->>'company', data->>'registration_no' from public.records
where project = 'contractor-registration-pmgsy-contractors' and data->>'contractor_status' = 'Blacklisted';
```
More queries: [DATA.md → How to work with it](DATA.md#how-to-work-with-it).

## 8. Verification
- **Tests:** 37 passed (`pytest tests`, offline, saved pages and PDFs). **CI:** `check` green on PR #6 (1 Nov 20:32 UTC); its
  reachability steps for pmgsy agreements, statepwd and rdso fail as expected (`site did not answer` from GitHub runners). **setup:** green, 1 Nov 19:52 UTC.
- **scrape-check through an Indian proxy (1 Nov, box):** `pmgsy` agreements (Sikkim, 1,263 records), `statepwd` (Gujarat
  electrical, 1,334), `rdso` (133): all PASS, and a rerun keeps the same ids.
- **Cross-checks:** Gujarat civil rows 1–8,113 contiguous and equal to the PDF's own "Total Registered Civil Contractor: 8113";
  RDSO 25 / 107 / 1 rows equal the lists' stated counts; CPWD 9,736 equals the portal's total; Sikkim's 1,215 awarded works equal
  the Agreement Details summary.
- **Not checked:** the PMGSY works totals against the summary for other states; the bucket size today.

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | **MES refuses the proxies (missed by us, for now)** | 34 items | Retried by the hub up to 40 times, 3 min apart. If it persists, ask Sarthak whether the proxy IPs were banned. |
| 2 | **Empty NHAI archive files** stored in the first pass (missed by us) | 2,794 files | Guard added; re-fetch those tenders' documents with a refresh item. |
| 3 | Documents that did not load (NHAI archive 552, MoRTH 20) or were over 80 MB (17) | 589 | Listed on the dashboard; most are 404s at the source. |
| 4 | No contractor ↔ work link in PMGSY public data (missing at the source) | all works | Only the officials' OMMAS has it. |
| 5 | PAN masked by PMGSY (missing at the source) | 56,988 | First five and last character only; enough to cross-check, not to identify. |
| 6 | Gujarat rows with blank cells (missing at the source) | 587 no firm type, 45 no registration date, 28 no validity | Kept as blanks. |
| 7 | OCR not run | 16,081 scans, 111,705 pages | Off by decision; `OCR = True` + setup turns it on. |

## 10. Risks and open decisions
- **Risks:** the proxied projects compete for 4 proxies. A long PMGSY works item (Uttar Pradesh, 21k works in one CSV) holds one
  for under a minute, which is fine. The Gujarat and RDSO parsers find columns by position; a re-laid-out PDF fails loudly
  (`hub.failure("parse", …)`) rather than storing wrong columns.
- **To decide (trideep):**
  1. **C04 vendor names via an IREPS guest login (mobile OTP).** Options: (a) skip; (b) a manual monthly pull: someone signs in with
     their phone and a script exports the directory in that session. Recommend (b) only if the vendor names are needed and the
     IREPS terms allow it.
  2. **C02 next states.** Recommend Maharashtra PWD, Rajasthan PWD, Karnataka PWD next (large states); one discovery each.
  3. **OCR** of the 16,081 scans: when there is room for the load.

## 11. Next steps
**To do now**
1. Merge the PR for branch `agreements-gujarat-rdso`, then Actions → setup (`gh workflow run setup.yml --ref main`).
2. Watch `-pmgsy-agreements`, `-state-pwd`, `-rdso-items` on scrape.s1d.me → Runs; first results within an hour.
3. Re-test MES tomorrow: `myproxy curl https://mes.gov.in/` (the TLS handshake should complete).

**To decide**
4. IREPS guest login for C04 (above). 5. Next C02 states. 6. OCR.

**Later**
7. PMGSY KPI contractors' performance (`/dbweb`) and quality-monitor grading abstracts.
8. pmgsytenders.gov.in (GePNIC) for the `gepnic` family: who won PMGSY tenders, the missing contractor ↔ work link.
9. Re-fetch the 2,794 empty NHAI archive files.

**Housekeeping**
10. Sarthak: health checks for India-only sites through a proxy; raise the family's proxy cap from 4 to 6.
11. **Rotate the Delhi VPS root password**: it was pasted in chat twice. It is not stored anywhere and is no longer needed.
