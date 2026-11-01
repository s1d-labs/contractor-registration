# Data: how it works, where it is, how to use it, what it shows

The family `contractor-registration` collects what nhai.gov.in and morth.gov.in publish about the firms that build and
supervise India's national highways (tenders and empanelment calls, consultant and contractor ratings, debarment orders, model
contracts and circulars), MES's approved products and consultants, and the PMGSY contractor master of rural road works (every
state's registered contractors with registration number, contacts, masked PAN and status, blacklisted included). Scanned
documents are stored for a later OCR pass (the OCR code is ready, switched off for now). Site discovery and login-only sections: [DISCOVERY.md](DISCOVERY.md).

## How it works

```
family.py ──(Actions → setup)──▶ scrape-hub: projects, queue items, health checks
                                     │  every few minutes, while there is work and the sites are up
                                     ▼
                     members' GitHub Actions runners (s1d-labs/runner, 60-minute runs)
                       check out this repo at main → crawl.py → adapters/<site>.py
                       claim an item ─▶ fetch pages / API ─▶ download documents (scans: OCR with tesseract)
                       (mes, pmgsy: through one of the hub's Mumbai proxies)        │
                                     │                              │
                         records (JSON, upserts)        files via the hub's signed upload links
                                     ▼                              ▼
                 Postgres scrape_hub.public.records       B2 bucket s1d-labs-trideep/<project>/...
                                                                    │
                       project -ocr: reads stored scans back ◀──────┘ and stores their text beside them
```

- **Refresh**: the setup workflow runs every day at 07:00 IST and adds dated items: the live NHAI tenders every day
  (`tenders-<YYYYMMDD>-p<k>`), MoRTH (new documents only), NHAI pages and MES every ISO week (`…-<YYYY>w<WW>`), PMGSY every month
  (`…-<YYYY>m<MM>`). A document stored before is fetched again only if the site's copy changed (a HEAD request compares
  Content-Length / Last-Modified with the `seen/<sha1 of url>.json` marker stored with it).

- **Queue items** are pages of work (50 tenders, ~100 documents, one CMS page). An item is done once; a failed one is retried
  after 3 minutes (up to 40 times), and an item claimed by a run that goes silent is handed to another run after 5 minutes.
- **Speed**: at most 8 workers per site; the archive takes at most 5 so live tenders and pages get the rest; MES and PMGSY 2 each
  (one proxy each, the family may hold 4); OCR 8 when it is on. Every request is counted (`n_http`, `t_http_s`, `http_<code>`) and the hub
  slows the family down if a site struggles. The health checks are registered but no project waits on them: the hub checks
  from a server these sites do not answer (since 2026-10-30).
- **Code changes** reach the pool through `main` only: merge a PR and the next runs use it. A change to `family.py` (new
  projects or items) also needs **Actions → setup**. Re-running setup is safe: existing items keep their state.

## Where the data is

| What | Where | How |
|---|---|---|
| Records | Postgres `scrape_hub`, table `public.records` (`project`, `record_id`, `data` jsonb, `scraped_at`) | `psql scrape_hub` on your box; Metabase → "Team data (scrape_hub)" |
| Queue, runs, failures | `public.queue`, `public.runs`, `public.failures` (filter `project like 'contractor-registration-%'`) | same; also https://scrape.s1d.me |
| Files | bucket `s1d-labs-trideep`, one folder per project | `mybucket ls`, `mybucket get`; bulk: `eval "$(mybucket env)"` then `aws s3` / `rclone` / boto3 |
| OCR text of scans | records of `contractor-registration-ocr` (`data->>'path'` = the scan's path, `data->'records'` = the records citing it); files `contractor-registration-ocr/<source project>/<path>.txt` | same |

The bucket is written only by pool runs (signed links); the key on your box is read-only. Nothing needs to be copied there by
hand: every document a run downloads is stored there with its text.

### Bucket layout

```
s1d-labs-trideep/
  contractor-registration-morth-documents/
    pdf/<page>/<group>/<hash8>-<name>.pdf        PDFs with a text layer
    pdf/<page>/<group>/<hash8>-<name>.pdf.txt    the whole extracted text
    ocr-needed/<page>/<group>/<hash8>-<name>.pdf scans (no text layer): input for an OCR pass
    docs/<page>/<group>/...                      doc, docx, xls, zip, ...
    seen/<sha1 of url>.json                      marker: what a download stored (lets a refresh skip unchanged documents)
  contractor-registration-nhai-tender-archive/   same, with sections tenders-archive/<endpoint>/
  contractor-registration-nhai-tenders/          same, section tenders/
  contractor-registration-nhai-pages/            same, one section per page (ratings, debarment orders, ...)
  contractor-registration-mes-works/             same, one section per MES page (works-product-approval, ...)
  contractor-registration-pmgsy-contractors/
    docs/contractor-information/<state>-<status>-<YYYYMMDD>.csv   the site's CSV export, per state and status
  contractor-registration-ocr/
    <source project>/ocr-needed/.../<name>.pdf.txt                OCR text of that scan (pages separated by form feeds)
```

Scans read as they were stored (projects with `OCR=1`, from 2026-11-01) have their OCR text beside them as `<path>.txt` and
`"ocr": true` in the record; the scans stored before are read by the `-ocr` project.

`<hash8>` is the first 8 hex digits of the SHA-1 of the source URL, so a file keeps its path when it is fetched again. Each
record points to its files: `path`, `text_path`, `sha256`, `bytes`, `pages`, `needs_ocr`, `text_chars`, and the first 20,000
characters of `text`.

### Projects and record ids

| Project | Records | Record id |
|---|---|---|
| `contractor-registration-nhai-tenders` | live NHAI tenders (242) | `tender-<nhai id>` |
| `contractor-registration-nhai-tender-archive` | NHAI tenders 2018-2025 (~10,900) | `tender-<nhai id>` |
| `contractor-registration-nhai-pages` | rating documents, debarment orders, standard documents, procurement manual, app catalogue, blacklist entries | `page-<nid>`, `<nid>-row-…`, `<nid>-doc-…`, `<nid>-link-…`, `common-…` |
| `contractor-registration-morth-documents` | MoRTH orders, notices, circulars, gazettes, guidelines, reports (~6,980) | `<slug>-<doc id>` |
| `contractor-registration-mes-works` | MES product approvals, approved consultants, contract policy, technical information (table rows) | `<page>-<row hash>` |
| `contractor-registration-cpwd-contractors` | CPWD enlisted contractors (9,736), CPWD debarred (9), suspended for EMD declaration violations (20) | `contractors-<site id>`, `debarred-<row hash>`, `suspended-<row hash>` |
| `contractor-registration-pmgsy-contractors` | PMGSY contractors of every state, with status | `<state code>-<hash of company, reg no, person, PAN>` |
| `contractor-registration-ocr` | OCR text of every scan stored before 2026-11-01 (16,081 files) | `<source project minus family>-<hash of source, path>` |

Record fields:

- **NHAI tender**: `id`, `title`, `tender_no`, `publish_date`, `bid_submission_end_date`, `bid_opening_date`, `is_empanelment`,
  `endpoint` (archive year), `detail.basic`, `detail.dates`, `documents[]` (`url`, `description`, `size`, `stored`), `url`.
- **NHAI page row** (debarment orders): `columns` (`Date`, `Order Number`, `Subject`, `Document`), `urls`, `files[]`.
- **NHAI page document** (ratings, standard documents): `text`, `heading` (e.g. "AE/IE Consultant Rating"), `size`, `url`, `file`.
- **MoRTH document**: `slug`, `group` (e.g. "Related to Debarment and Blacklisting"), `title`, `published_date`,
  `wings_division`, `circular_number`, `url`, `contractor_related`, `file`.
- **MES row**: `path`, `page`, `columns` (e.g. `Subject`, `Date`, `Attachment`), `urls`, `tender_id`, `files[]`.
- **CPWD row**: `list` (contractors / debarred / suspended), `site_id`, `columns` (`Name of Contractor`, `Address`, `State`,
  `Category`, `Class`, `Date of Enlistment`, `Enlistment Valid Upto`, `Date of Debarred`, `Debarred Upto`, `Date of Suspension`,
  `Suspension Upto`, `Contractor Status`; the debarred / suspended lists: their dates), `files` (order links; they need a CPWD login).
- **PMGSY contractor**: `state`, `state_code`, `company`, `contact_person`, `registration_no`, `address`, `pincode`, `phone1`,
  `phone2`, `fax`, `email`, `pan` (as the site shows it, e.g. `AHBTSXXXXC`), `contractor_status` (Active / Inactive /
  Blacklisted / Expired), `csv_path`.
- **OCR**: `source_project`, `path`, `records` (up to 5 record ids citing the scan), `pages`, `pages_read` (at most 300),
  `lang` (`eng+hin`), `text_path`, `text_chars`, `text` (first 20,000 characters).

## How to work with it

**Look around** (psql on your box, or the same SQL in Metabase):

```sql
-- what is in, per project
select project, count(*), max(scraped_at) from public.records where project like 'contractor-registration-%' group by 1;

-- progress of the queues
select project, status, count(*) from public.queue where project like 'contractor-registration-%' group by 1, 2 order by 1, 2;

-- empanelment calls (RFE / EOI / enlistment) in NHAI tenders
select data->>'publish_date' published, data->>'tender_no' tender_no, data->>'title' title
from public.records where project in ('contractor-registration-nhai-tenders', 'contractor-registration-nhai-tender-archive')
  and (data->>'is_empanelment')::boolean order by 1 desc;

-- MoRTH debarment and blacklisting orders with the start of their text
select data->>'published_date', data->>'title', left(data->'file'->>'text', 400)
from public.records where project = 'contractor-registration-morth-documents'
  and data->>'group' = 'Related to Debarment and Blacklisting' order by 1 desc;

-- debarment orders on NHAI's page (NHIDCL / MoRTH / NHAI / PWD)
select data->'columns'->>'Date', data->'columns'->>'Order Number', data->'columns'->>'Subject'
from public.records where project = 'contractor-registration-nhai-pages' and data->>'kind' = 'table_row';

-- search the text of every stored document for a firm (OCR text included: project -ocr, joined back through data->'records')
select project, record_id, coalesce(data->>'title', data->>'path') from public.records
where project like 'contractor-registration-%' and data::text ilike '%S&P Infrastructure%';

-- OCR text of the MoRTH debarment orders that are scans
select m.data->>'published_date', m.data->>'title', left(o.data->>'text', 400)
from public.records m join public.records o
  on o.project = 'contractor-registration-ocr' and o.data->>'source_project' = m.project and o.data->>'path' = m.data->'file'->>'path'
where m.project = 'contractor-registration-morth-documents' and m.data->>'group' ilike '%debar%';

-- PMGSY: blacklisted contractors in every state, and active contractors per state
select data->>'state', data->>'company', data->>'registration_no', data->>'pan', data->>'address' from public.records
where project = 'contractor-registration-pmgsy-contractors' and data->>'contractor_status' = 'Blacklisted';
select data->>'state' state, data->>'contractor_status' status, count(*) from public.records
where project = 'contractor-registration-pmgsy-contractors' group by 1, 2 order by 1, 2;

-- NHAI tenders also on CPPP (gepnic-etenders), matched on the normalised reference number
with g as (select distinct upper(regexp_replace(data->'list'->>'reference_no', '[^A-Za-z0-9]', '', 'g')) ref
           from public.records where project = 'gepnic-etenders' and data->>'org_name' ilike 'national highways authority%')
select count(*) total, count(*) filter (where upper(regexp_replace(data->>'tender_no', '[^A-Za-z0-9]', '', 'g')) in (select ref from g)) on_cppp
from public.records where project = 'contractor-registration-nhai-tender-archive';
```

**Get files**:

```bash
mybucket ls contractor-registration-morth-documents/pdf/orders-and-notices/           # browse
mybucket get contractor-registration-morth-documents/pdf/orders-and-notices/<path>     # one file
eval "$(mybucket env)"                                                                 # bulk, with the read-only key
aws s3 sync "s3://$B2_BUCKET/contractor-registration-morth-documents/pdf/orders-and-notices/related-to-debarment-and-blacklisting/" ./debarment/
aws s3 sync "s3://$B2_BUCKET/contractor-registration-nhai-tender-archive/ocr-needed/" ./ocr-in/   # ~4 GB so far
```

**In Python** (records from Postgres, files from the bucket):

```python
import os, subprocess, boto3, psycopg                     # pip install psycopg[binary] boto3
env = dict(l.removeprefix("export ").split("=", 1) for l in subprocess.check_output(["mybucket", "env"], text=True).split("\n") if "=" in l)
s3 = boto3.client("s3", endpoint_url=env["B2_ENDPOINT"], region_name=env["B2_REGION"],
                  aws_access_key_id=env["AWS_ACCESS_KEY_ID"], aws_secret_access_key=env["AWS_SECRET_ACCESS_KEY"])
with psycopg.connect("dbname=scrape_hub host=127.0.0.1") as db:
    for rid, data in db.execute("select record_id, data from public.records where project = %s and data->>'group' ilike %s",
                                ("contractor-registration-morth-documents", "%debar%")):
        f = data.get("file") or {}
        if f.get("path"):
            body = s3.get_object(Bucket=env["B2_BUCKET"], Key=f"contractor-registration-morth-documents/{f['path']}")["Body"].read()
```

**OCR** (off for now, `OCR = False` in family.py; turn it on and run setup when the load is fine): in the pool (project `-ocr`, `adapters/ocr.py`: pypdfium2 renders each page at 200 dpi, tesseract reads English
and Hindi, ~6 CPU-seconds a page). New scans are read as they are stored. To queue the scans that are not read yet (e.g. after a
pool run failed on some), run `python tools/build_queues.py` on the box, commit `queues/`, run setup. To try it on the box:
`eval "$(mybucket env)"; python crawl.py --local ocr '<one payload from queues/ocr.json.gz>'`.

## Report (2026-11-01)

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

### What it shows

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

### Data quality notes

- **Empty files**: 2,794 NHAI archive document links answered HTTP 200 with an empty body; they were stored as empty files under
  `docs/` (ext `pdf`, `bytes` near 0). Treat them as missing. Downloads now refuse empty answers and web pages served in place
  of a document (e.g. a sign-in page).
- **Missing on the site**: ~6% of NHAI tender documents answer 404 on nhai.gov.in itself (old files with generic names such as
  `2_RFP.pdf` that were overwritten or removed). They are listed in the record (`documents[].url`) without `stored`.
- **MoRTH title text**: in 26 titles the site's backend dropped the letters "exec" ("being uted by", "utive Engineer"); the PDF
  text is intact.
- **NUL characters**: a few PDFs (e.g. MoRTH annual reports) yield `\u0000` in their text, which Postgres cannot store; the
  hub then refused the whole batch. Fixed (PR #4): NULs are stripped before records are sent.
- **One MoRTH item missing**: `public-notices-part5` (97 notices) failed for three hours on 2026-10-29 ("site did not answer" on
  the list request) and used up its 40 tries; the request works again. Setup now resets items that used up their tries, so it
  runs again, and the weekly MoRTH refresh would pick the notices up anyway.
- **Time budget**: runs last 60 minutes and an archive item ~10-15; runs no longer start an item in their last 15 minutes.
- **Live tenders**: read every day from 2026-11-01; a tender's record is rewritten with its latest details each day it is live.
- **PMGSY**: the site masks PANs itself (`AHBTSXXXXC`); some rows carry placeholders (`xyz54XXXX5`, phone `0 0`), cleaned to
  empty where they are only zeros and dashes. One state and status is one CSV export (Uttar Pradesh: 1.4 MB).
- **Health checks**: since 2026-10-30 02:00 CET the hub's own server gets no answer from nhai.gov.in, morth.gov.in or any other
  India-only site (every family's checks fail on scrape.s1d.me). The projects no longer wait on them.
