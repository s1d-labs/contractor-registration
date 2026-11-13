# First pass (1 Nov 2026)

Moved here from DATA.md on 14 Nov 2026. The numbers are from 1 Nov 2026; the current state of each planned source is in the reports (`report-C01.md` … `report-C06.md`, `report-D03.md`).

## Report

The first pass finished on 2026-10-30 01:20 UTC (about 9 hours): every queue item done but one MoRTH item (below).

| Project | Records | Documents in the bucket | Scans (no text layer) | Size |
|---|---|---|---|---|
| `nhai-tender-archive` | 10,648 tenders (2018-2025) | 41,836 cited, 13,437 of them scans | 13,749 | 40.4 GB |
| `morth-documents` | 6,841 documents | ~7,000 | 2,673 | 9.5 GB |
| `nhai-tenders` | 246 live tenders (snapshot 2026-10-29) | 1,122 objects | 208 | 1.1 GB |
| `nhai-pages` | 243 (100 debarment orders, 49 standard documents, 12 rating documents, ...) | 312 objects | 124 | 0.6 GB |
| bucket | | 63,686 objects | | 48.0 GiB of 500 |

Added 2026-11-01 (running in the pool after setup): `cpwd-contractors` (114 items: 55 pages and 2 lists, now and every
month), `mes-works` (34 items), `pmgsy-contractors` (296 items: 37 states x 4
statuses, now and every month), and, when switched on, `ocr` (485 batches ready: 16,081 scans, 111,705 pages; ~45 runner-hours,
about 6 hours with 8 workers). From the box, through a proxy: Uttar Pradesh alone has 4,897 active PMGSY contractors (4,782 with a masked PAN), Sikkim
519, Assam 15 blacklisted.

## What it shows

1. **NHAI's own site is the only source for most NHAI tenders.** Matching reference numbers against the NHAI tenders the team
   has from CPPP (`gepnic-etenders`): **2,303 of 10,648 (22%)** archive tenders are there; 25-30% for 2018-2020, 10-12% for
   2024-2025. Toll and user-fee collection contracts are the largest group.
2. **Empanelment happens in plain tenders.** **314** archive tenders (and 9 of the 246 live ones) are empanelment calls, RFEs or
   EOIs: toll-plaza operators and amenities, advocates, chartered and cost accountants, advertising agencies, GNSS free-flow
   tolling, expansion joints and bearings manufacturers. There is no separate register; these tenders and their result
   documents are the record of who gets empanelled.
3. **Debarment is published as orders, not as a list.** MoRTH's "Related to Debarment and Blacklisting" group has **38 orders**
   (March 2023 to October 2026) naming firms and their associates; NHAI's page lists **100** NHIDCL / MoRTH / NHAI / PWD orders
   (date, order number, subject naming the person or firm), each with its PDF. Many are scans, waiting for the OCR pass.
   PMGSY is the only source with a **blacklisted status per contractor** (Assam 15; most states list none).
4. **The PMGSY contractor master is the closest thing to a public register**: per state, every contractor registered for rural
   road works with the state registration number, address, phones and a masked PAN (first five and last character: enough to
   tell firms with the same name apart and to match a PAN seen elsewhere). CPWD's enlisted contractors (CEMS), MES's enlistment
   (CCEP) and the railway approved-vendor directory (IREPS UVAM) are behind logins.
5. **About 30-40% of the documents are scans**: 13,749 of the NHAI archive's files and 2,673 of MoRTH's. Until their OCR is
   done, their records have titles and dates but no text.
6. **MoRTH's tenders are already covered** (eProcure, 24,695 since 2016); what this family adds from MoRTH is the paper trail:
   950 of 6,841 documents are contractor-related (debarment, model concession / EPC / HAM / BOT agreements, consultancy,
   ratings), alongside circulars, gazette notifications and public notices.

