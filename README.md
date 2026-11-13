# contractor-registration

Government contractor, consultant and vendor registers for the s1d-labs scrape pool: who may bid for public works in India,
under which class and limit, and who is banned. The family covers the planned sources C01–C06 (contractor registration) and
D03 (PSU ban and holiday lists) of india.s1d.me. The sites run on different platforms, so the family has one worker loop
(`crawl.py`) and one adapter per site (`adapters/<site>.py`); each project's `env.ADAPTER` picks it.

## Layout

| Path | What |
|---|---|
| `family.py` | every project: target, network (`proxy` / `geo`), queue items, refresh items (daily / weekly / monthly) |
| `setup_family.py`, `scrape.json` | applies `family.py` to the hub (the **setup** workflow, every day at 07:00 IST) |
| `crawl.py` | the task: claims items and runs the project's adapter; `--local` runs one item without the hub |
| `adapters/` | one module per site, with pure `parse_*` functions; `common.py`: counted requests, document storage, PDF text |
| `tests/`, `tests/pages/` | parser tests on saved (or hand-made) pages; `python -m pytest -q tests` |
| `tools/` | box-side tools: `build_queues.py` (OCR queue, MoRTH baseline), `ireps_vendors.py` (human sign-in, on hold) |
| `queues/` | queue items built from what is stored (OCR batches, PMGSY districts, NHAI re-fetch) |
| `report-C01.md` … `report-C06.md`, `report-D03.md` | one report per planned source, for readers (published on pub.s1d.me) |
| `DATA.md` | where the records and files are, record ids, data quality notes |
| `DISCOVERY.md` | internal notes: what each site offers, logins, dead ends, decisions |
| `docs/` | older material (the first pass of 1 Nov 2026) |
| `CLAUDE.md` | the pool contract (runner env, hub client, metrics, proxies), for people and for Claude Code |

## Adapters and projects

| Adapter | Site | Projects (prefix `contractor-registration`) | Source |
|---|---|---|---|
| `cpwd` | erp.cpwd.gov.in (proxy) | `-cpwd-contractors` (monthly) | C01 |
| `statepwd` | state PWD / R&B / Works / PHED lists: PDF, HTML tables, an ASP.NET register | `-state-pwd` (Gujarat), `-state-pwd-maharashtra`, `-wb`, `-uttarakhand`, `-odisha`, `-tripura`, `-arunachal`, `-haryana` (monthly) | C02 |
| `mes` | mes.gov.in (proxy, `91.124.42.x` only) | `-mes-works` (weekly) | C03 |
| `rdso` | rdso.indianrailways.gov.in (proxy + India servers) | `-rdso-items` (monthly) | C04 |
| `nhai`, `morth` | nhai.gov.in, morth.gov.in (JSON APIs) | `-nhai-tenders` (daily), `-nhai-tender-archive`, `-nhai-pages`, `-morth-documents` (weekly) | C05 |
| `pmgsy` (+ `pmgsyreg`), `emarg` | pmgsy.dord.gov.in (SSRS reports, drill-through), emarg.gov.in (proxy) | `-pmgsy-contractors`, `-pmgsy-agreements`, `-pmgsy-corenetwork`, `-pmgsy-completed`, `-pmgsy-maintenance`, `-emarg-roads` | C06 |
| `banlists` | PSU ban / holiday lists: BHEL, Oil India, OPaL, NHPC, NDDB; BPCL and HPCL (proxy) | `-banlists`, `-banlists-in` (weekly) | D03 |
| `ocr` | the family's own bucket: scans read back with tesseract | `-ocr` (off: `OCR = False` in `family.py`) | all |

Documents go to the bucket under `<project>/pdf/` (with the text beside each as `.pdf.txt`), `ocr-needed/` (scans, for a later
OCR pass) and `docs/`. A document stored before and unchanged on the site is not fetched again (`seen/<sha1>.json` markers).

## Run and change

- One item without the hub: `python crawl.py --local banlists '{"list": "nddb"}'`. India-only sites from a team box:
  `myproxy run python crawl.py --local …`.
- Against a local stand-in hub: `scrape-check --project contractor-registration-banlists --items 2`.
- Add a site: `adapters/<site>.py` with `run(ctx, payload)` and pure `parse_*` functions, a test in `tests/`, a project in
  `family.py`, and a light `scrape-check` step in `.github/workflows/check.yml`. Merge to `main`, then run **Actions → setup**.
- The pool contract, the hub client and the proxy rules: [CLAUDE.md](CLAUDE.md).
