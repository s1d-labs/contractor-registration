# contractor-registration

Government contractor, consultant and vendor registers for the s1d-labs pool: empanelment calls, ratings, debarment orders and
the tenders and circulars around them. The sites run on different platforms, so this family is one worker loop (`crawl.py`) with
one adapter per site (`adapters/<site>.py`); each project's `env.ADAPTER` picks it.

| Adapter | Site | Projects (family.py) |
|---|---|---|
| `nhai` | nhai.gov.in (Angular + Drupal JSON API) | `-nhai-tenders`, `-nhai-tender-archive`, `-nhai-pages` |
| `morth` | morth.gov.in (Angular + Laravel JSON API) | `-morth-documents` |
| `mes` | mes.gov.in (Drupal 11 tables) | none yet: mes.gov.in does not answer GitHub runners |

Documents go to the family bucket as `pdf/` (with the extracted text beside each as `.pdf.txt`), `ocr-needed/` (scans without a
text layer) and `docs/`. Where the records and files end up and what they show: [DATA.md](DATA.md). What each site offers, what is
behind a login, and what comes next: [DISCOVERY.md](DISCOVERY.md).

The sites drop some foreign hosting addresses (the team box among them); GitHub's runners get through. To run locally from the box,
send the requests through an Indian exit: `ALL_PROXY=socks5h://127.0.0.1:1080 NO_PROXY=127.0.0.1,localhost` (and `pip install pysocks`).

Run one queue item without the hub: `python crawl.py --local nhai '{"kind": "page", "nid": "publication-rating-dpr-consultants"}'`.
Add a site: write `adapters/<site>.py` with `run(ctx, payload)` and pure `parse_*` functions, saved responses in `tests/pages/`, a
project in `family.py`, and a light `scrape-check --project contractor-registration-ci-<site>` step in `.github/workflows/check.yml`.

The rest of this README is the template's guide.

## Make your family

1. Ask the hub owner to **add the family** on [scrape.s1d.me/runners](https://scrape.s1d.me/runners) (name, what it scrapes, owner).
   The hub creates `s1d-labs/<family>` from this template, names the family in `scrape.json`, and makes the owner admin
   (with the GitHub account they added on home.s1d.me).
2. Clone it: `gh repo clone s1d-labs/<family>`.
3. In your repo:
   - `scrape.json`: set `"family"` to the family name; list your tasks (one command each) and setup steps.
   - `family.py`: your projects (one queue of work per site), their target hosts, the env your command needs, the queue items,
     and the health checks.
   - `crawl.py` (or whatever your tasks run): the scraper.
4. **Check it**: `scrape-check` in the repo (needs `pip install "scrape-hub-client @ git+https://github.com/s1d-labs/runner@main#subdirectory=sdk"`).
   It runs your setup and task against a local stand-in hub on 3 real items and says what works. The **check** workflow runs it
   (and `tests/`) on every push.
5. Run the **setup** workflow (Actions → setup → Run workflow). It registers the projects, puts them in the pool and registers
   the health checks.
6. The hub starts runs in members' accounts when the pool is on and there is work. Watch it on scrape.s1d.me.

## What your code gets

The pool worker ([s1d-labs/runner](https://github.com/s1d-labs/runner)) checks out this repo at `main`, runs the `setup` steps from
`scrape.json`, and for each assignment runs the task's command here with:

| Variable | What |
|---|---|
| `SCRAPE_POOL_PROJECT` | the project to work on |
| `SCRAPE_JOB_INDEX`, `SCRAPE_TOTAL_JOBS` | this worker's slice |
| `SCRAPE_MAX_HOURS` | how long the command may run |
| `SCRAPE_HUB_URL` | the hub |
| your project's `env` | e.g. `SITE` |

Use `scrape_hub_client` (`HubClient`) to claim queue items, store records, upload files and report counters. Exit when there is
nothing left; the worker then asks the hub for the next assignment.

## Rules (the full contract is in CLAUDE.md, written for people and for Claude Code)

- **Be polite.** Use `hub.settings["threads"]` and `delay_ms`, idle while `hub.settings["paused"]`, and report `n_http` and
  `t_http_s` for every request and `http_<code>` / `http_error` for failures: the hub throttles you from these.
- **Files go through the hub** (`hub.upload_many`): it signs each upload into the family's bucket (500 GB per member) and stops at
  the cap. Never put storage keys in this repo.
- **Public data only**; read the site's terms first. See the team docs on home.s1d.me (Scraping rules).
