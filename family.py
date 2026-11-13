"""What this family scrapes. Change this file first.

FAMILY must equal the repo name (s1d-labs/<FAMILY>) and the family the hub owner added on scrape.s1d.me/runners.
Each project is one queue of work on one site; `target` is the host it hits (the hub caps workers per target).
One project per site (or per kind of work on a site); `env.ADAPTER` picks adapters/<name>.py in crawl.py.
These are government contractor, consultant and vendor registers and the notices around them (empanelment calls, ratings,
debarment orders). Public pages only: sections behind a login are listed in DISCOVERY.md, not scraped.
"""
import gzip
import json
from datetime import datetime, timezone
from math import ceil
from pathlib import Path

HERE = Path(__file__).parent
FAMILY = json.loads((HERE / "scrape.json").read_text())["family"]

# Refresh items: the setup workflow runs every day (schedule in .github/workflows/setup.yml) and adds items keyed by the day or the
# ISO week, so the live NHAI tenders are read daily and MoRTH / NHAI pages / MES weekly. Documents stored before and unchanged on
# the site are not fetched again (marker files, adapters/common.py).
TODAY = datetime.now(timezone.utc).date()
DAY = TODAY.strftime("%Y%m%d")
WEEK = "{0}w{1:02d}".format(*TODAY.isocalendar())
MONTH = TODAY.strftime("%Ym%m")
LIVE_PAGES = 8        # tenderlist pages of 50 read every day (242 live tenders on 2026-10-29); empty pages finish with 0 records

MORTH_FILES = "."     # MoRTH documents whose files are downloaded ("." = all); every document gets a record either way
DOCS_PER_ITEM = 100   # MoRTH documents per queue item, so no item runs for hours

NHAI_ARCHIVE = {      # archive endpoint -> tenders in it (calendar year of publication); the site's own endpoint names
    "tenderarchive": 1667,       # 2018
    "tenderarchivenin": 1388,    # 2019
    "tenderarchivetwe": 1632,    # 2020
    "tenderarchivetweone": 1766,  # 2021
    "tenderarchivetwetwo": 1845,  # 2022
    "tenderarchivetwethree": 1426,  # 2023
    "tenderarchivetwefour": 771,  # 2024
    "tenderarchivetwefive": 429 + 50,  # 2025 (still gets late additions)
}
NHAI_PAGES = [        # rest_api route slugs: the CMS pages that carry registers, ratings and standard documents
    "publication-rating-dpr-consultants",                       # DPR / AE-IE consultant and contractor ratings (PDFs)
    "individualsagencies-debarredblacklisted-morthnhidclpwds",  # debarment orders: date, order no, subject, PDF
    "contract-management-circulars",
    "standard-document",                                        # RFP / RFQ / concession model documents
    "procurement-manual-nhai",
    "tentative-and-clearance-status-projects",
    "nhai-web-applications-dept-division-wise-categorization",  # NHAI's own application catalogue (links, incl. logins)
]
MORTH_PAGES = {       # backend/api slug -> documents on it
    "orders-and-notices": 2177, "gazettes-notifications": 908, "guidelines": 428, "public-notices": 677,
    "comprehensive-compendium-circular": 2490, "reports": 264, "acts-and-rules": 22, "policies-and-regulations": 6,
}
MES_WORKS = {         # mes.gov.in table pages -> pages in the pager (0-based ?page=N)
    "works/product-approval": 27,                   # product approval letters + the consolidated list of approved products
    "works/consultancy-miscellaneous": 1,           # consolidated lists of approved / enlisted consultants
    "works-policies-data/contracts": 1,             # contract policy letters (incl. the enlistment policy for consultants)
    "works-directorate-technical-information": 1,
}
PMGSY_STATES = {1: "Andaman And Nicobar (UT)", 2: "Andhra Pradesh", 3: "Arunachal Pradesh", 4: "Assam", 5: "Bihar",
                6: "Chandigarh (UT)", 7: "Chhattisgarh", 8: "Dadra And Nagar Haveli (UT)", 9: "Daman And Diu (UT)", 10: "Delhi (UT)",
                11: "Goa", 12: "Gujarat", 13: "Haryana", 14: "Himachal Pradesh", 15: "Jammu And Kashmir", 16: "Jharkhand",
                17: "Karnataka", 18: "Keralam", 19: "Lakshadweep (UT)", 20: "Madhya Pradesh", 21: "Maharashtra", 22: "Manipur",
                23: "Meghalaya", 24: "Mizoram", 25: "Nagaland", 26: "Odisha", 27: "Puducherry (UT)", 28: "Punjab", 29: "Rajasthan",
                30: "Sikkim", 31: "Tamil Nadu", 32: "Tripura", 33: "Uttar Pradesh", 34: "Uttarakhand", 35: "West Bengal",
                36: "Telangana", 37: "Ladakh (UT)"}   # the site's state codes (its State list)
# the site's districts per state (DistrictDetails, 2026-11-13): [state code, district code, name]; 792 districts
PMGSY_DISTRICTS = [tuple(x) for x in json.loads(gzip.decompress((HERE / "queues" / "pmgsy_districts.json.gz").read_bytes()))]
FY = TODAY.year if TODAY.month >= 4 else TODAY.year - 1     # PMGSY financial years start in April (2026 = 2026-27)
CPWD_PAGES = 55     # pages of 200 in CPWD's contractor list (9,736 on 2026-11-01)
STATE_LISTS = ["gujarat-rnb-civil", "gujarat-rnb-electrical"]   # adapters/statepwd.py LISTS: state contractor registers (PDF)
MH_LISTS = ["maharashtra-pwd-civil", "maharashtra-pwd-electrical"]   # on the S3WaaS CDN: answers from anywhere, no proxy
# MES tenders are not queued: the gepnic family already holds them from defproc.gov.in under the same CPPP ids


# OCR is off for now, to keep the load down: scans are stored under ocr-needed/ for later. OCR = True (then the setup workflow)
# reads new scans as they are stored and puts the -ocr project, which reads the stored ones (queues/ocr.json.gz), in the pool.
OCR = False

# The hub owner's pause on Indian proxies and Indian servers (2 Nov 2026, ~24 hours, while 40 more proxies are added): projects
# with proxy="IN" are taken out of the pool (set_pool(pool=False)); their queues are kept. Set back to False, then run setup.
HOLD_PROXIED = False


def _env(adapter, site, ocr=True):
    """OCR=1: scans are read with tesseract as they are stored (adapters/ocr.py)."""
    return {"ADAPTER": adapter, "SITE": site, **({"OCR": "1"} if ocr and OCR else {})}


def _queue(name):
    """Items built from what is already stored (tools/build_queues.py, run on a team box); [] before the first build."""
    path = HERE / "queues" / name
    return json.loads(gzip.decompress(path.read_bytes())) if path.exists() else []


PROJECTS = [
    {
        "name": f"{FAMILY}-nhai-tenders",
        "title": "NHAI current tenders and empanelment calls",
        "task": "crawl", "target": "nhai.gov.in", "env": _env("nhai", "https://nhai.gov.in"),
        "unit_label": "page", "record_label": "tender",
        # the first snapshot (2026-10-29), then every day's live list with details and documents
        "items": [{"key": f"tenders-p{k}", "payload": {"kind": "tenders", "endpoint": "tenderlist", "page": k, "detail": True,
                                                       "files": True, "section": "tenders", "expected": 50}} for k in range(6)]
                 + [{"key": f"tenders-{DAY}-p{k}", "payload": {"kind": "tenders", "endpoint": "tenderlist", "page": k, "detail": True,
                                                              "files": True, "section": "tenders", "expected": 50 if k < 5 else 0}}
                    for k in range(LIVE_PAGES)],
    },
    {
        "name": f"{FAMILY}-nhai-tender-archive",
        "title": "NHAI tender archive 2018-2025",
        "task": "crawl", "target": "nhai.gov.in", "env": _env("nhai", "https://nhai.gov.in", ocr=False),
        "max_workers": 5,     # of the 8 per target: leaves room for the live tenders and the ratings / debarment pages
        "unit_label": "page", "record_label": "tender",
        # details and documents for every tender (~5 MB a tender, ~50 GB in all)
        "items": [{"key": f"{ep}-p{k}", "payload": {"kind": "tenders", "endpoint": ep, "page": k, "detail": True, "files": True,
                                                    "section": f"tenders-archive/{ep}", "expected": 50}}
                  for ep, total in NHAI_ARCHIVE.items() for k in range(ceil(total / 50))]
                 # documents the first pass stored empty (the site answered 200 with no body), fetched again
                 + _queue("nhai_refetch.json.gz"),
    },
    {
        "name": f"{FAMILY}-nhai-pages",
        "title": "NHAI ratings, debarment orders and standard documents",
        "task": "crawl", "target": "nhai.gov.in", "env": _env("nhai", "https://nhai.gov.in"),
        "unit_label": "page", "record_label": "row / document",
        "items": [{"key": f"page-{nid}{sfx}"[:200], "payload": {"kind": "page", "nid": nid, "files": True}}
                  for sfx in ("", f"-{WEEK}") for nid in NHAI_PAGES]
                 + [{"key": f"common-blacklisted-debarred-firms{sfx}", "payload": {"kind": "commontype", "tid": "blacklisted-debarred-firms"}}
                    for sfx in ("", f"-{WEEK}")],
    },
    {
        "name": f"{FAMILY}-morth-documents",
        "title": "MoRTH orders, notices, guidelines, circulars and gazettes",
        "task": "crawl", "target": "morth.gov.in", "env": _env("morth", "https://morth.gov.in"),
        "unit_label": "page", "record_label": "document",
        "items": [{"key": f"{slug}-part{k}" if n > DOCS_PER_ITEM else slug,
                   "payload": {"slug": slug, "part": k, "parts": ceil(n / DOCS_PER_ITEM), "files_re": MORTH_FILES,
                               "expected": ceil(n / ceil(n / DOCS_PER_ITEM))}}
                  for slug, n in MORTH_PAGES.items() for k in range(ceil(n / DOCS_PER_ITEM))]
                 # weekly: the whole page in one item, only the documents not collected before
                 + [{"key": f"{slug}-{WEEK}", "payload": {"slug": slug, "part": 0, "parts": 1, "files_re": MORTH_FILES, "new_only": True}}
                    for slug in MORTH_PAGES],
    },
    {
        # mes.gov.in answers Indian addresses only: GitHub workers each borrow one of the hub's Mumbai proxies (proxy="IN")
        "name": f"{FAMILY}-mes-works",
        "title": "MES approved products, approved consultants and works policy letters",
        "task": "crawl", "target": "mes.gov.in", "env": _env("mes", "https://mes.gov.in"),
        "proxy": "IN", "max_workers": 2,
        "proxy_only": ["91.124.42."],   # mes.gov.in refuses the 191.219.x and 95.134.119.x proxies (2-3 Nov 2026)
        "unit_label": "page", "record_label": "row",
        "items": [{"key": f"{path.replace('/', '-')}-p{k}", "payload": {"path": path, "page": k, "files": True}}
                  for path, pages in MES_WORKS.items() for k in range(pages)]
                 + [{"key": f"{path.replace('/', '-')}-{WEEK}-p0", "payload": {"path": path, "page": 0, "files": True}}
                    for path in MES_WORKS],
    },
    {
        # pmgsy.dord.gov.in (OMMAS citizen reports) answers Indian addresses only: through the hub's Mumbai proxies
        "name": f"{FAMILY}-pmgsy-contractors",
        "title": "PMGSY (OMMAS) contractor master per state: active, inactive, blacklisted, expired",
        "task": "crawl", "target": "pmgsy.dord.gov.in", "env": _env("pmgsy", "https://pmgsy.dord.gov.in", ocr=False),
        "proxy": "IN", "max_workers": 2,
        "unit_label": "state x status", "record_label": "contractor",
        # once, then every month (the master changes slowly)
        "items": [{"key": f"{code:02d}-{status}{sfx}", "payload": {"state": code, "state_name": name, "status": status}}
                  for sfx in ("", f"-{MONTH}") for code, name in PMGSY_STATES.items() for status in "ABEI"]
                 # the dashboard's performance score per contractor (construction, mobilisation, quality; 7,008 on 3 Nov 2026)
                 + [{"key": f"kpi-{code:02d}{sfx}", "payload": {"report": "kpi", "state": code, "state_name": name}}
                    for sfx in ("", f"-{MONTH}") for code, name in PMGSY_STATES.items()],
    },
    {
        # erp.cpwd.gov.in (CPWD's new portal; cpwd.gov.in does not answer) answers Indian addresses only: through the Mumbai proxies
        "name": f"{FAMILY}-cpwd-contractors",
        "title": "CPWD enlisted contractors (class, category, validity, debarment, suspension) and debarment / suspension lists",
        "task": "crawl", "target": "erp.cpwd.gov.in", "env": _env("cpwd", "https://erp.cpwd.gov.in"),
        "proxy": "IN", "max_workers": 2,
        "unit_label": "page", "record_label": "contractor",
        # 9,736 contractors on 2026-11-01, 200 a page; spare pages finish with 0 records. Again every month. The orders (PDFs)
        # need a CPWD login, so the records keep their links only (files: false).
        "items": [{"key": f"contractors-p{k}{sfx}", "payload": {"list": "contractors", "cur": k, "delta": 200, "files": False,
                                                              "expected": 200 if k < 49 else 0}}
                  for sfx in ("", f"-{MONTH}") for k in range(1, CPWD_PAGES + 1)]
                 + [{"key": f"{name}{sfx}", "payload": {"list": name, "cur": 1, "delta": 200, "files": False}}
                    for sfx in ("", f"-{MONTH}") for name in ("debarred", "suspended")],
    },
    {
        # the same OMMAS citizen reports: Work Awarded -> Agreement Details, drilled through to every work of a state
        "name": f"{FAMILY}-pmgsy-agreements",
        "title": "PMGSY works awarded per state: package, road, sanctioned and awarded cost; works awarded and terminated",
        "task": "crawl", "target": "pmgsy.dord.gov.in", "env": _env("pmgsy", "https://pmgsy.dord.gov.in", ocr=False),
        "proxy": "IN", "max_workers": 2,
        "unit_label": "state", "record_label": "work",
        # 37 states (Sikkim 1,263 works, Uttar Pradesh 21,140), again every month
        "items": [{"key": f"agreements-{code:02d}{sfx}", "payload": {"report": "agreements", "state": code, "state_name": name}}
                  for sfx in ("", f"-{MONTH}") for code, name in PMGSY_STATES.items()],
    },
    {
        # the PMGSY road register (OMMAS citizen reports, adapters/pmgsyreg.py): Core Network -> Road-wise Core Network, each
        # district's blocks drilled through to their roads (road number L031 / T05, name, route, chainage, length, from, to,
        # habitations served). The core network changes slowly: one pass (2026-11-13: 792 districts in 37 states).
        "name": f"{FAMILY}-pmgsy-corenetwork",
        "title": "PMGSY core network road register per district: road number, name, route, length, from, to, habitations",
        "task": "crawl", "target": "pmgsy.dord.gov.in", "env": _env("pmgsy", "https://pmgsy.dord.gov.in", ocr=False),
        # 14 Nov 2026: the proxies were all lent to other families for hours; the India servers had spare workers
        "proxy": "IN", "geo": "IN", "max_workers": 2,
        "unit_label": "district", "record_label": "road x habitation",
        "items": [{"key": f"cn-{state:02d}-{district}", "payload": {"report": "corenetwork", "state": state,
                                                                   "state_name": PMGSY_STATES[state], "district": district,
                                                                   "district_name": dname}}
                  for state, district, dname in PMGSY_DISTRICTS],
    },
    {
        # Proposals -> Completed Roads with Value of Work Done, per district: package, road, sanction year, sanctioned cost,
        # value of work done, payment made, completion month. Once, then every month.
        "name": f"{FAMILY}-pmgsy-completed",
        "title": "PMGSY completed roads per district: package, road, sanction year, cost, value of work done, completion month",
        "task": "crawl", "target": "pmgsy.dord.gov.in", "env": _env("pmgsy", "https://pmgsy.dord.gov.in", ocr=False),
        # 14 Nov 2026: the proxies were all lent to other families for hours; the India servers had spare workers
        "proxy": "IN", "geo": "IN", "max_workers": 1,
        "unit_label": "district", "record_label": "road",
        "items": [{"key": f"done-{state:02d}-{district}{sfx}", "payload": {"report": "completed", "state": state,
                                                                          "state_name": PMGSY_STATES[state], "district": district,
                                                                          "district_name": dname}}
                  for sfx in ("", f"-{MONTH}") for state, district, dname in PMGSY_DISTRICTS],
    },
    {
        # Expenditure on DLP Maintenance, per state and financial year (2000-01 to now): every road's maintenance cost, whether
        # it is in its liability period, and the year's and total maintenance spending. The current year again every month.
        "name": f"{FAMILY}-pmgsy-maintenance",
        "title": "PMGSY road maintenance per state and year: package, road, completion, maintenance cost and spending",
        "task": "crawl", "target": "pmgsy.dord.gov.in", "env": _env("pmgsy", "https://pmgsy.dord.gov.in", ocr=False),
        # 14 Nov 2026: the proxies were all lent to other families for hours; the India servers had spare workers
        "proxy": "IN", "geo": "IN", "max_workers": 1,
        "unit_label": "state x year", "record_label": "road",
        "items": [{"key": f"upkeep-{code:02d}-{year}", "payload": {"report": "maintenance", "state": code, "state_name": name, "year": year}}
                  for year in range(FY, 1999, -1) for code, name in PMGSY_STATES.items()]
                 + [{"key": f"upkeep-{code:02d}-{FY}-{MONTH}", "payload": {"report": "maintenance", "state": code, "state_name": name, "year": FY}}
                    for code, name in PMGSY_STATES.items()],
    },
    {
        # emarg.gov.in "Know Your Road": the public state / district / block / road lists of the roads under PMGSY maintenance
        # (adapters/emarg.py). The road details (contractor, maintenance dates, spending) need a captcha: not fetched.
        "name": f"{FAMILY}-emarg-roads",
        "title": "eMARG roads under maintenance per state, district and block (road id and name)",
        "task": "crawl", "target": "emarg.gov.in", "env": _env("emarg", "https://emarg.gov.in/application_main.htm", ocr=False),
        "proxy": "IN", "max_workers": 1,
        "unit_label": "state", "record_label": "road",
        "items": [{"key": f"roads-{code:02d}{sfx}", "payload": {"state": code, "state_name": name}}
                  for sfx in ("", f"-{MONTH}") for code, name in PMGSY_STATES.items()],
    },
    {
        # state PWD / R&B registers published as PDF lists; rnb.gujarat.gov.in answers Indian addresses only
        "name": f"{FAMILY}-state-pwd",
        "title": "State PWD / R&B registered contractors (Gujarat R&B civil and electrical lists)",
        "task": "crawl", "target": "rnb.gujarat.gov.in", "env": _env("statepwd", "https://rnb.gujarat.gov.in", ocr=False),
        "proxy": "IN", "max_workers": 1,
        "unit_label": "list", "record_label": "contractor",
        "items": [{"key": f"{name}{sfx}", "payload": {"list": name}} for sfx in ("", f"-{MONTH}") for name in STATE_LISTS],
    },
    {
        # Maharashtra PWD publishes its registers in the RTI manual (no. 13), as PDFs on the S3WaaS CDN (8,966 civil, 632
        # electrical rows; registrations mostly valid up to 2013-2017). Checked again every month in case a new list goes up.
        "name": f"{FAMILY}-state-pwd-maharashtra",
        "title": "Maharashtra PWD registered civil and electrical contractors (RTI manual no. 13)",
        "task": "crawl", "target": "cdnbbsr.s3waas.gov.in", "env": _env("statepwd", "https://cdnbbsr.s3waas.gov.in", ocr=False),
        "max_workers": 1,
        "unit_label": "list", "record_label": "contractor",
        "items": [{"key": f"{name}{sfx}", "payload": {"list": name}} for sfx in ("", f"-{MONTH}") for name in MH_LISTS],
    },
    {
        # West Bengal PHED's approved vendor lists (civil and electro-mechanical items): scanned PDFs, stored for OCR later
        "name": f"{FAMILY}-state-pwd-wb",
        "title": "West Bengal PHED approved vendors (civil and electro-mechanical items), scanned lists",
        "task": "crawl", "target": "wbphed.gov.in", "env": _env("statepwd", "https://wbphed.gov.in", ocr=False),
        "proxy": "IN", "max_workers": 1,
        "unit_label": "page", "record_label": "list",
        "items": [{"key": f"wb-phed-approved-vendors{sfx}", "payload": {"doc_page": "wb-phed-approved-vendors"}} for sfx in ("", f"-{MONTH}")],
    },
    {
        # PWD Uttarakhand's online registration: every application per class with status, registration number (ending in the
        # firm's PAN) and validity; 36,405 applications on 4 Nov 2026 (A 1,944, B 816, C 3,870, D 29,775). One GET per class.
        "name": f"{FAMILY}-state-pwd-uttarakhand",
        "title": "PWD Uttarakhand registered contractors (online registration, classes A to D)",
        "task": "crawl", "target": "registrationpwd.uk.gov.in", "env": _env("statepwd", "https://registrationpwd.uk.gov.in", ocr=False),
        "proxy": "IN", "max_workers": 1,
        "unit_label": "class", "record_label": "application",
        "items": [{"key": f"uttarakhand-pwd-{c}{sfx}", "payload": {"uk_class": c, "expected": n}}
                  for sfx in ("", f"-{MONTH}") for c, n in (("A", 1944), ("B", 816), ("C", 3870), ("D", 29770))],
    },
    {
        # Odisha Works Department's contractor ledger: Super / Special / A / B class civil and MV / HT electrical contractors
        "name": f"{FAMILY}-state-pwd-odisha",
        "title": "Odisha Works Department contractor ledger (civil and electrical)",
        "task": "crawl", "target": "works.odisha.gov.in", "env": _env("statepwd", "https://works.odisha.gov.in", ocr=False),
        "proxy": "IN", "max_workers": 1,
        "unit_label": "ledger", "record_label": "contractor",
        "items": [{"key": f"{name}{sfx}", "payload": {"ledger": name}}
                  for sfx in ("", f"-{MONTH}") for name in ("odisha-works-civil", "odisha-works-electrical")],
    },
    {
        # PWD (R&B) Tripura: enlisted contractors per class on one page (1,539 on 4 Nov 2026) and each one's certificate PDF
        "name": f"{FAMILY}-state-pwd-tripura",
        "title": "PWD (R&B) Tripura enlisted contractors (classes I to V, electrical) with enlistment certificates",
        "task": "crawl", "target": "pwd.tripura.gov.in", "env": _env("statepwd", "https://pwd.tripura.gov.in", ocr=False),
        "proxy": "IN", "max_workers": 1,
        "unit_label": "page", "record_label": "contractor",
        "items": [{"key": f"tripura-pwd-enlisted{sfx}", "payload": {"tables": "tripura-pwd-enlisted", "expected": 1539}}
                  for sfx in ("", f"-{MONTH}")],
    },
    {
        # PWD Arunachal Pradesh: valid enlisted civil contractors (classes IAA / IA / I, II, III as on 30-09-2026: 1,276) and the
        # cancellation / extension orders and older lists the page links to. arunachalpwd.org answers from anywhere.
        "name": f"{FAMILY}-state-pwd-arunachal",
        "title": "PWD Arunachal Pradesh enlisted contractors (classes I to III) and cancellation orders",
        "task": "crawl", "target": "arunachalpwd.org", "env": _env("statepwd", "https://arunachalpwd.org", ocr=False),
        "max_workers": 1,
        "unit_label": "list", "record_label": "contractor",
        "items": [{"key": f"{name}{sfx}", "payload": {"columns": name}}
                  for sfx in ("", f"-{MONTH}") for name in ("arunachal-pwd-class-i", "arunachal-pwd-class-ii", "arunachal-pwd-class-iii")]
                 + [{"key": f"arunachal-pwd-documents{sfx}", "payload": {"links": "arunachal-pwd-documents"}} for sfx in ("", f"-{MONTH}")],
    },
    {
        # PWD (B&R) Haryana: the published list of Class-1 enlisted contractors (1.4.2014 to 16.12.2020, 302 firms). The
        # department's "search approved contractor" form only answers a full name, so it is not a list.
        "name": f"{FAMILY}-state-pwd-haryana",
        "title": "PWD (B&R) Haryana Class-1 enlisted contractors (2014-2020 list)",
        "task": "crawl", "target": "haryanapwd.gov.in", "env": _env("statepwd", "https://haryanapwd.gov.in", ocr=False),
        "proxy": "IN", "max_workers": 1,
        "unit_label": "list", "record_label": "contractor",
        "items": [{"key": f"haryana-pwd-class1{sfx}", "payload": {"numbered": "haryana-pwd-class1", "expected": 302}}
                  for sfx in ("", f"-{MONTH}")],
    },
    {
        # the vendor directory is on IREPS behind a mobile-OTP sign-in; RDSO's own page lists the items with few sources
        "name": f"{FAMILY}-rdso-items",
        "title": "RDSO items with fewer than three / five approved sources, or no Indian source",
        "task": "crawl", "target": "rdso.indianrailways.gov.in", "env": _env("rdso", "https://rdso.indianrailways.gov.in", ocr=False),
        # 4 Nov 2026: pool runs got connection errors through every proxy while the same proxy answered from a team box;
        # the hub's India servers take the work too
        "proxy": "IN", "geo": "IN", "max_workers": 1,
        "unit_label": "page", "record_label": "item",
        "items": [{"key": f"few-sources{sfx}", "payload": {"section": "0,5,6634"}} for sfx in ("", f"-{MONTH}")],
    },
    {
        # Planned sources D03 and D04: firms that public sector undertakings ban, debar or put "on holiday", and suppliers that
        # state medical services corporations blacklist (TNMSC, RMSC, GMSCL) (adapters/banlists.py). Each
        # list is a page on the organisation's site (a table, or a link to the current PDF); a new version every few weeks,
        # so every list is read again each week. These sites answer from anywhere.
        "name": f"{FAMILY}-banlists",
        "title": "Firms banned, debarred or put on holiday by PSUs (BHEL, Oil India, OPaL, NHPC, NDDB) and state medical corporations",
        "task": "crawl", "target": "banlists", "env": _env("banlists", "https://www.bhel.com", ocr=False),
        "max_workers": 1,
        "unit_label": "list", "record_label": "firm",
        "items": [{"key": f"{name}{sfx}", "payload": {"list": name}}
                  for sfx in ("", f"-{WEEK}") for name in ("bhel-debarred", "bhel-banned", "oil-india", "opal", "nddb", "nhpc",
                                                           "tnmsc", "rmsc-company", "rmsc-product", "gmscl")],
    },
    {
        # BPCL's holiday list, its list of vendors served a show-cause notice (holiday listing proposed), and HPCL's holiday list:
        # bharatpetroleum.in and hindustanpetroleum.com answer 403 outside India.
        "name": f"{FAMILY}-banlists-in",
        "title": "Vendors on BPCL's and HPCL's holiday lists, and vendors BPCL served a show-cause notice",
        "task": "crawl", "target": "www.bharatpetroleum.in", "env": _env("banlists", "https://www.bharatpetroleum.in", ocr=False),
        "proxy": "IN", "max_workers": 1,
        "unit_label": "list", "record_label": "firm",
        "items": [{"key": f"{name}{sfx}", "payload": {"list": name}}
                  for sfx in ("", f"-{WEEK}") for name in ("bpcl-holiday", "bpcl-show-cause", "hpcl-holiday")],
    },
] + ([{
    # reads the scans stored above (ocr-needed/) back from the bucket and stores their text; no site is contacted
    "name": f"{FAMILY}-ocr",
    "title": "OCR text of the scanned documents",
    "task": "crawl", "target": "ocr.s1d-labs-trideep", "env": {"ADAPTER": "ocr"},
    "max_workers": 8,
    "unit_label": "batch", "record_label": "document",
    "items": _queue("ocr.json.gz"),
}] if OCR else [])

# Health checks, shown on scrape.s1d.me. No project names them (probe=""): the hub checks from its own server, which these sites
# have not answered since 2026-10-30, and a failing probe would hold the work that GitHub runners and the proxies can still do.
PROBES = [
    {"name": f"{FAMILY}:nhai.gov.in", "url": "https://nhai.gov.in/", "expect": "National Highways Authority of India"},
    {"name": f"{FAMILY}:morth.gov.in", "url": "https://morth.gov.in/", "expect": "Ministry of Road Transport"},
]
