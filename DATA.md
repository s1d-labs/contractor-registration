# Data: where it is, what it holds, what it shows

The family `contractor-registration` collects government contractor, consultant and vendor information that is public on
nhai.gov.in, morth.gov.in and mes.gov.in: empanelment calls, consultant and contractor ratings, debarment orders, approved
product and consultant lists, and the tenders and circulars around them. Site discovery and login-only sections: [DISCOVERY.md](DISCOVERY.md).

## Where to find it

| What | Where | How |
|---|---|---|
| Records (one JSON per tender / document / table row) | Postgres `scrape_hub`, table `public.records`, filtered by `project` | `psql scrape_hub` on your box; Metabase → "Team data (scrape_hub)" |
| Same records, one column per JSON key | `scrape_hub.projects.contractor_registration_<site>_<what>` (the hub's per-project views) | `select * from projects.contractor_registration_nhai_pages limit 10` |
| Files (PDFs, their text, other documents) | bucket `s1d-labs-trideep`, under `<project>/` | `mybucket ls -r contractor-registration-nhai-pages/`, `mybucket get <path>`, `mybucket du` |
| Progress, errors, failures, speed | https://scrape.s1d.me (Runs, the family's projects, Failures) | |

The bucket is written only by the pool, through the hub's signed upload links; the key on your box is read-only.

### Projects

| Project | Records | Record id | Files under `<project>/` |
|---|---|---|---|
| `contractor-registration-nhai-tenders` | 242 live NHAI tenders | `tender-<nhai id>` | `pdf|ocr-needed|docs/tenders/` |
| `contractor-registration-nhai-tender-archive` | ~10,900 NHAI tenders 2018-2025 | `tender-<nhai id>` | `pdf|ocr-needed|docs/tenders-archive/<endpoint>/` |
| `contractor-registration-nhai-pages` | rating documents, debarment orders, standard documents, procurement manual, NHAI app catalogue, blacklist entries | `page-<nid>`, `<nid>-row-…`, `<nid>-doc-…`, `<nid>-link-…`, `common-…` | `pdf|ocr-needed|docs/<nid>/` |
| `contractor-registration-morth-documents` | ~7,000 MoRTH orders, notices, guidelines, circulars, gazettes, reports | `<slug>-<doc id>` | `pdf|ocr-needed|docs/<slug>/<group>/` |
| `contractor-registration-mes-works` | MES product approval letters, approved-products list, approved / enlisted consultant lists, contract policies | `<path>-<row id>` | `pdf|ocr-needed|docs/<path>/` |

Folders: `pdf/` PDFs with a text layer, with the whole text beside each as `<name>.pdf.txt`; `ocr-needed/` scans with no text layer
(for a later OCR pass); `docs/` other formats. Every stored file in a record carries `path`, `sha256`, `bytes`, `pages`,
`needs_ocr`, `text_path`, `text_chars` and the first 20,000 characters of `text`.

### Record fields

- **NHAI tender**: `id`, `title`, `tender_no`, `publish_date`, `bid_submission_end_date`, `bid_opening_date`, `is_empanelment`,
  `detail.basic` (tender no, department, category, fee, EMD when given), `detail.dates`, `documents[]` (`url`, `description`, `size`,
  `stored`), `url`.
- **NHAI page row** (debarment orders): `columns` (`Date`, `Order Number`, `Subject`, `Document`), `urls`, `files[]`.
- **NHAI page document** (ratings, standard documents): `text`, `heading` (e.g. "AE/IE Consultant Rating"), `size`, `url`, `file`.
- **MoRTH document**: `slug`, `group` (e.g. "Related to Debarment and Blacklisting"), `title`, `published_date`, `wings_division`,
  `circular_number`, `url`, `contractor_related`, `file`.
- **MES row**: `path`, `columns` (subject, letter no & date, upload date, …), `urls`, `files[]`.

### Queries to start with

```sql
-- empanelment calls (RFE / EOI / enlistment) in NHAI tenders, live and archive
select data->>'publish_date' published, data->>'tender_no' tender_no, data->>'title' title
from public.records where project in ('contractor-registration-nhai-tenders', 'contractor-registration-nhai-tender-archive')
  and (data->>'is_empanelment')::boolean order by 1 desc;

-- debarment orders (NHAI page: NHIDCL / MoRTH / NHAI / PWD debarments)
select data->'columns'->>'Date' dated, data->'columns'->>'Order Number' order_no, data->'columns'->>'Subject' subject
from public.records where project = 'contractor-registration-nhai-pages' and data->>'kind' = 'table_row';

-- MoRTH debarment and blacklisting orders, with the text of each order
select data->>'published_date', data->>'title', left(data->'file'->>'text', 400)
from public.records where project = 'contractor-registration-morth-documents'
  and data->>'group' = 'Related to Debarment and Blacklisting' order by 1 desc;

-- full text search across every stored document
select project, record_id, data->>'title' from public.records
where project like 'contractor-registration-%' and data::text ilike '%blacklist%';
```

## What it shows (conclusions so far)

From the discovery, the test runs and the team database (2026-10-28/29):

1. **The registers themselves are behind logins.** CPWD's enlisted-contractor list (CEMS), MES's contractor and consultant
   enlistment (CCEP) and the railway approved-vendor directory (IREPS UVAM, mobile OTP) need an account. What is public is everything
   around them: who is invited to empanel, how firms are rated, who is debarred, which products and consultants are approved. This
   family collects that public part.
2. **NHAI's own site lists tenders that CPPP does not.** The team already has 28,475 NHAI tenders from etenders.gov.in
   (`gepnic-etenders`), but only 2 of 9 sampled tender numbers from nhai.gov.in are among them: quotations, disposals, consultancy
   RFPs and empanelment calls (RFE) appear only on nhai.gov.in. The archive (~10,900 tenders since 2018) is worth having in full.
3. **MES tenders are already in the team data.** All 7 sampled MES tender ids are in `gepnic-defproc` (552,817 MES records), so
   the family does not fetch them again. What MES adds is its approval registers: the consolidated list of approved products is a
   vendor register (firm, product, brand, approval letter, valid-up-to date), and the approved-consultant lists name the consultants
   MES works with.
4. **MoRTH's tenders are in eProcure** (24,695 since 2016); its own site adds the paper trail: 38 debarment and blacklisting orders,
   suspension and speaking orders naming firms, model concession and contract agreements (EPC, HAM, BOT), and ~7,000 circulars.
5. **Ratings and debarments are mostly PDFs.** NHAI publishes DPR / AE-IE consultant and contractor ratings only as PDFs, and the
   debarment list as a table that points to scanned orders. About 40% of the PDFs are scans: in test runs, 64 of 170 MoRTH PDFs
   and 46 of 117 NHAI tender PDFs had no text layer. `ocr-needed/` collects them for an OCR pass; until then their
   records have titles and dates but no text.
6. **These sites drop some foreign hosting addresses** (the team box, a French data centre) but GitHub's runners reach them, so
   the pool works without a proxy. CPWD (cpwd.gov.in) and PMGSY (pmgsy.nic.in) stayed unreachable even from an Indian VPS.

Volumes (test runs): an NHAI tender carries about 5 MB of documents (~50 GB for the archive), MoRTH documents about 1 MB each
(~7 GB). The bucket holds 500 GB.
