"""MoRTH (morth.gov.in): an Angular app on a Laravel JSON API, `GET https://morth.gov.in/backend/api/<slug>`.

Every document page (orders-and-notices, guidelines, gazettes-notifications, ...) answers with the same shape:
page.files = groups [{name, files_data: [{title, file, published_date, ...}]}], so one handler serves them all.

Queue item payload: {"slug": "orders-and-notices", "part": 0, "parts": 22, "files_re": ".", "new_only": false}
An item handles the documents whose id falls in its part (doc_id % parts), so a page of 2,500 documents is spread over many
items. Every document gets a record; its file is downloaded when `files_re` matches "<group> <title>" ("." = every file).
`new_only` (the weekly refresh items) skips the documents collected before (queues/morth_known.txt.gz).
`contractor_related` marks debarment, empanelment, rating and contract documents for analysis.
"""
import gzip
import re
from pathlib import Path
from urllib.parse import quote

from adapters.common import clean, sha1

KNOWN = Path(__file__).parent.parent / "queues" / "morth_known.txt.gz"
SITE = "https://morth.gov.in"
API = SITE + "/backend/api"
HEADERS = {"Referer": SITE + "/", "Accept": "application/json"}
RELEVANT = re.compile(r"debar|blacklist|suspen|empanel|enlist|rating|contractor|concession|consultan|\brfp\b|\brfq\b|prequalif|"
                      r"model (contract|concession)|\bEPC\b|\bHAM\b|\bBOT\b|bidder|tender", re.I)


def file_url(file):
    """Absolute URL of a stored file, or None for the broken `/tmp/php...` upload paths the site sometimes returns."""
    file = (file or "").strip()
    if not file or "/tmp/" in file or file.startswith("tmp/"):
        return None
    if file.startswith("http"):
        return file
    return f"{SITE}/backend/" + quote(file.lstrip("/"), safe="/%()&,=+@")


def parse_documents(js, slug):
    """[dict] one per document in every group of a page response. Pure: test it on a saved response."""
    page = (js or {}).get("page") or {}
    out = []
    for group in page.get("files") or []:
        for f in group.get("files_data") or []:
            url = file_url(f.get("file"))
            key = f.get("file") or f.get("link") or f.get("title") or ""
            out.append({
                "slug": slug, "group": clean(group.get("name")), "title": clean(f.get("title")), "url": url,
                "external_link": f.get("link") or None, "published_date": f.get("published_date"), "last_date": f.get("last_date"),
                "wings_division": f.get("wings_division"), "code": f.get("code"), "circular_number": f.get("circular_guideline_number"),
                "state_id": f.get("state_id"), "is_archived": bool(f.get("is_archived")), "size": f.get("file_size"),
                "broken_file": bool(f.get("file")) and url is None, "doc_id": sha1(slug, group.get("name"), key)[:14],
            })
    return out


def known_ids(path=KNOWN):
    """Record ids collected before (queues/morth_known.txt.gz, made by tools/build_queues.py): a refresh item skips them."""
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except OSError:
        return set()


def run(ctx, payload):
    slug = payload["slug"]
    js = ctx.get_json("GET", f"{API}/{slug}", params={"page": 1, "per_page": 500, "wings": "", "order_by": "desc", "search": ""},
                      headers=HEADERS, timeout=120)
    if js is None:
        return None
    part, parts = payload.get("part", 0), max(1, payload.get("parts", 1))
    docs = [d for d in parse_documents(js, slug) if int(d["doc_id"], 16) % parts == part]
    if payload.get("new_only"):
        known = known_ids()
        docs = [d for d in docs if f"{slug}-{d['doc_id']}" not in known]
    fetch = re.compile(payload.get("files_re") or "$^", re.I)
    for d in docs:
        data = {**d, "contractor_related": bool(RELEVANT.search(f"{d['group']} {d['title']}"))}
        if d["url"] and fetch.search(f"{d['group']} {d['title']}"):
            data["file"] = ctx.download(d["url"], f"{slug}/{re.sub(r'[^a-z0-9]+', '-', d['group'].lower()).strip('-')[:50] or 'ungrouped'}", HEADERS)
        ctx.record(f"{slug}-{d['doc_id']}", data)
    return len(docs)
