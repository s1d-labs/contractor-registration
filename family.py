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

# MoRTH documents whose files are downloaded; every other document still gets a metadata record (see adapters/morth.py)
MORTH_FILES = r"debar|blacklist|suspen|empanel|enlist|rating|contractor|concession|consultan|rfp\b|rfq\b|prequalif"

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
        # details for every tender; documents only for empanelment calls (the rest of the files can be fetched later)
        "items": [{"key": f"{ep}-p{k}", "payload": {"kind": "tenders", "endpoint": ep, "page": k, "detail": True, "files": False,
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
        "items": [{"key": slug, "payload": {"slug": slug, "files_re": MORTH_FILES, "expected": n}} for slug, n in MORTH_PAGES.items()],
    },
]

# health checks the hub runs every minute; work for a project holds while its probe fails
PROBES = [
    {"name": f"{FAMILY}:nhai.gov.in", "url": "https://nhai.gov.in/", "expect": "National Highways Authority of India"},
    {"name": f"{FAMILY}:morth.gov.in", "url": "https://morth.gov.in/", "expect": "Ministry of Road Transport"},
]
