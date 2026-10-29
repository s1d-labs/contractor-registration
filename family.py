"""What this family scrapes. Change this file first.

FAMILY must equal the repo name (s1d-labs/<FAMILY>) and the family the hub owner added on scrape.s1d.me/runners.
Each project is one queue of work on one site; `target` is the host it hits (the hub caps workers per target).
One project per site (or per kind of work on a site); `env.ADAPTER` picks adapters/<name>.py in crawl.py.
These are government contractor, consultant and vendor registers and the notices around them (empanelment calls, ratings,
debarment orders). Public pages only: sections behind a login are listed in DISCOVERY.md, not scraped.
"""
import json
from math import ceil
from pathlib import Path

FAMILY = json.loads((Path(__file__).parent / "scrape.json").read_text())["family"]

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
# MES tenders are not queued: the gepnic family already holds them from defproc.gov.in under the same CPPP ids


def _env(adapter, site):
    return {"ADAPTER": adapter, "SITE": site}


PROJECTS = [
    {
        "name": f"{FAMILY}-nhai-tenders",
        "title": "NHAI current tenders and empanelment calls",
        "task": "crawl", "target": "nhai.gov.in", "env": _env("nhai", "https://nhai.gov.in"),
        "probe": f"{FAMILY}:nhai.gov.in",
        "unit_label": "page", "record_label": "tender",
        # 242 live tenders, 50 a page; empty trailing pages finish with 0 records
        "items": [{"key": f"tenders-p{k}", "payload": {"kind": "tenders", "endpoint": "tenderlist", "page": k, "detail": True,
                                                       "files": True, "section": "tenders", "expected": 50}} for k in range(6)],
    },
    {
        "name": f"{FAMILY}-nhai-tender-archive",
        "title": "NHAI tender archive 2018-2025",
        "task": "crawl", "target": "nhai.gov.in", "env": _env("nhai", "https://nhai.gov.in"),
        "probe": f"{FAMILY}:nhai.gov.in",
        "unit_label": "page", "record_label": "tender",
        # details and documents for every tender (~5 MB a tender, ~50 GB in all)
        "items": [{"key": f"{ep}-p{k}", "payload": {"kind": "tenders", "endpoint": ep, "page": k, "detail": True, "files": True,
                                                    "section": f"tenders-archive/{ep}", "expected": 50}}
                  for ep, total in NHAI_ARCHIVE.items() for k in range(ceil(total / 50))],
    },
    {
        "name": f"{FAMILY}-nhai-pages",
        "title": "NHAI ratings, debarment orders and standard documents",
        "task": "crawl", "target": "nhai.gov.in", "env": _env("nhai", "https://nhai.gov.in"),
        "probe": f"{FAMILY}:nhai.gov.in",
        "unit_label": "page", "record_label": "row / document",
        "items": [{"key": f"page-{nid}"[:200], "payload": {"kind": "page", "nid": nid, "files": True}} for nid in NHAI_PAGES]
                 + [{"key": "common-blacklisted-debarred-firms", "payload": {"kind": "commontype", "tid": "blacklisted-debarred-firms"}}],
    },
    {
        "name": f"{FAMILY}-morth-documents",
        "title": "MoRTH orders, notices, guidelines, circulars and gazettes",
        "task": "crawl", "target": "morth.gov.in", "env": _env("morth", "https://morth.gov.in"),
        "probe": f"{FAMILY}:morth.gov.in",
        "unit_label": "page", "record_label": "document",
        "items": [{"key": f"{slug}-part{k}" if n > DOCS_PER_ITEM else slug,
                   "payload": {"slug": slug, "part": k, "parts": ceil(n / DOCS_PER_ITEM), "files_re": MORTH_FILES,
                               "expected": ceil(n / ceil(n / DOCS_PER_ITEM))}}
                  for slug, n in MORTH_PAGES.items() for k in range(ceil(n / DOCS_PER_ITEM))],
    },
    # MES (adapters/mes.py) is not queued: mes.gov.in does not answer GitHub runners (check workflow, 2026-10-29).
]

# health checks the hub runs every minute; work for a project holds while its probe fails
PROBES = [
    {"name": f"{FAMILY}:nhai.gov.in", "url": "https://nhai.gov.in/", "expect": "National Highways Authority of India"},
    {"name": f"{FAMILY}:morth.gov.in", "url": "https://morth.gov.in/", "expect": "Ministry of Road Transport"},
]
