# Data: how it works, where it is, how to use it, what it shows

The family `contractor-registration` collects what nhai.gov.in and morth.gov.in publish about the firms that build and
supervise India's national highways: tenders and empanelment calls, consultant and contractor ratings, debarment orders,
model contracts and circulars. Site discovery and login-only sections: [DISCOVERY.md](DISCOVERY.md).

## How it works

```
family.py ──(Actions → setup)──▶ scrape-hub: projects, queue items, health checks
                                     │  every few minutes, while there is work and the sites are up
                                     ▼
                     members' GitHub Actions runners (s1d-labs/runner, 60-minute runs)
                       check out this repo at main → crawl.py → adapters/<site>.py
                       claim an item ─▶ fetch pages / API ─▶ download documents
                                     │                              │
                         records (JSON, upserts)        files via the hub's signed upload links
                                     ▼                              ▼
                 Postgres scrape_hub.public.records       B2 bucket s1d-labs-trideep/<project>/...
```

- **Queue items** are pages of work (50 tenders, ~100 documents, one CMS page). An item is done once; a failed one is retried
  after 3 minutes (up to 40 times), and an item claimed by a run that goes silent is handed to another run after 5 minutes.
- **Speed**: at most 8 workers per site; the archive takes at most 5 so live tenders and pages get the rest. Every request is
  counted (`n_http`, `t_http_s`, `http_<code>`) and the hub slows the family down if a site struggles. Health checks run every
  minute; while a site fails, its work is held.
- **Code changes** reach the pool through `main` only: merge a PR and the next runs use it. A change to `family.py` (new
  projects or items) also needs **Actions → setup**. Re-running setup is safe: existing items keep their state.

## Where the data is

| What | Where | How |
|---|---|---|
| Records | Postgres `scrape_hub`, table `public.records` (`project`, `record_id`, `data` jsonb, `scraped_at`) | `psql scrape_hub` on your box; Metabase → "Team data (scrape_hub)" |
| Queue, runs, failures | `public.queue`, `public.runs`, `public.failures` (filter `project like 'contractor-registration-%'`) | same; also https://scrape.s1d.me |
| Files | bucket `s1d-labs-trideep`, one folder per project | `mybucket ls`, `mybucket get`, `mybucket du`; bulk: `eval "$(mybucket env)"` then `aws s3` / `rclone` / boto3 |

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
  contractor-registration-nhai-tender-archive/   same, with sections tenders-archive/<endpoint>/
  contractor-registration-nhai-tenders/          same, section tenders/
  contractor-registration-nhai-pages/            same, one section per page (ratings, debarment orders, ...)
```

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

Record fields:

- **NHAI tender**: `id`, `title`, `tender_no`, `publish_date`, `bid_submission_end_date`, `bid_opening_date`, `is_empanelment`,
  `endpoint` (archive year), `detail.basic`, `detail.dates`, `documents[]` (`url`, `description`, `size`, `stored`), `url`.
- **NHAI page row** (debarment orders): `columns` (`Date`, `Order Number`, `Subject`, `Document`), `urls`, `files[]`.
- **NHAI page document** (ratings, standard documents): `text`, `heading` (e.g. "AE/IE Consultant Rating"), `size`, `url`, `file`.
- **MoRTH document**: `slug`, `group` (e.g. "Related to Debarment and Blacklisting"), `title`, `published_date`,
  `wings_division`, `circular_number`, `url`, `contractor_related`, `file`.

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

-- search the text of every stored document for a firm
select project, record_id, data->>'title' from public.records
where project like 'contractor-registration-%' and data::text ilike '%S&P Infrastructure%';

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

**OCR the scans** (on your box; `sudo apt install ocrmypdf tesseract-ocr-hin`): sync `ocr-needed/` down, run
`ocrmypdf -l eng+hin in.pdf out.pdf` per file, keep the results in your own database (`ws_trideep`) or files; the bucket is
written only through the pool.

## Report (snapshot 2026-10-29 17:26 UTC, about an hour after the first runs)

| Project | Queue done | Records | Documents stored | Need OCR | Size |
|---|---|---|---|---|---|
| `morth-documents` | 68 / 74 | 6,611 | 6,563 | 2,292 (35%) | 8.2 GB |
| `nhai-tender-archive` | 67 / 223 | 3,829 tenders | 14,137 of 15,045 (94%) | 5,537 (39%) | 13.3 GB |
| `nhai-pages` | 0 / 8 | not started (waiting for NHAI workers, see PR #4) | | | |
| `nhai-tenders` | 0 / 6 | not started (same) | | | |
| bucket | | | 29,918 objects | | 21.4 GiB |

At this pace the archive finishes in about 2-3 hours (~38 GB at 3.5 MB a tender) and MoRTH as soon as the NUL fix (PR #4) is
on `main`.

### What it shows

1. **NHAI's own site is the only source for most NHAI tenders.** Matching reference numbers against the 28,475 NHAI tenders the
   team already has from CPPP (`gepnic-etenders`): only **846 of 3,824 (22%)** archive tenders are there. Toll and user-fee
   collection contracts (1,419) are the largest group and only 21% of them are on CPPP; construction (EPC / HAM / BOT, 558) and
   consultancy (AE / IE / DPR, 337) are 37% on CPPP; office services, vehicles and quotations (1,510) 14%.
2. **Empanelment happens in plain tenders.** 109 of 3,829 archive tenders so far are empanelment calls or EOIs: operators for
   toll-plaza amenities, advocates, chartered and cost accountants, advertising agencies, GNSS free-flow tolling, expansion
   joints and bearings manufacturers. There is no separate register; these tenders and their result documents are the record of
   who gets empanelled.
3. **Debarment is published as orders, not as a list.** MoRTH's "Related to Debarment and Blacklisting" group has 37 orders
   (2023: 9, 2024: 7, 2025: 9, 2026: 12) that name firms and their associates (S&P Infrastructure Developers, Deep Jyoti Company,
   Bhimji Velji Sorathia Construction, R. G. Buildwell Engineers, MP PWD contractor debarments). NHAI's page lists 105
   NHIDCL / MoRTH / NHAI / PWD orders (date, order number, subject naming the person or firm), each with its order as a 3-4 MB PDF.
4. **About 40% of the documents are scans.** 35% of MoRTH's and 39% of NHAI's tender PDFs have no text layer. Until they are
   OCR'd, their records have titles and dates but no text; `ocr-needed/` holds exactly those files.
5. **MoRTH's tenders are already covered** (eProcure, 24,695 since 2016); what this family adds from MoRTH is the paper trail:
   947 of 6,611 documents are contractor-related (debarment, model concession / EPC / HAM / BOT agreements, consultancy,
   ratings), alongside ~5,600 circulars, gazette notifications and public notices.
6. **The registers themselves are behind logins**: CPWD's enlisted contractors (CEMS), MES's contractor and consultant enlistment
   (CCEP) and the railway approved-vendor directory (IREPS UVAM). What is public is everything around them, which is what this
   family collects. MES's approval registers (approved products with validity, approved consultants) are public but mes.gov.in
   does not answer GitHub runners.

### Data quality notes

- **Missing on the site**: ~6% of NHAI tender documents answer 404 on nhai.gov.in itself (old files with generic names such as
  `2_RFP.pdf` that were overwritten or removed). They are listed in the record (`documents[].url`) without `stored`.
- **MoRTH title text**: in 26 titles the site's backend dropped the letters "exec" ("being uted by", "utive Engineer"); the PDF
  text is intact.
- **NUL characters**: a few PDFs (e.g. MoRTH annual reports) yield `\u0000` in their text, which Postgres cannot store; the
  hub then refused the whole batch and 6 MoRTH items kept retrying. Fixed in PR #4 (NULs are stripped before records are sent).
- **Time budget**: runs last 60 minutes and an archive item ~10-15; items started late timed out and were retried. PR #4 stops
  runs from starting an item in their last 15 minutes.
- **Live tenders change**: `nhai-tenders` is a snapshot of the 242 live tenders when it runs; new tenders need new queue items
  (for example keys with a date, seeded by setup).
