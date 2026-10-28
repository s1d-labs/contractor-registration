"""MoRTH (morth.gov.in): an Angular app on a Laravel JSON API, `GET https://morth.gov.in/backend/api/<slug>`.

Every document page (orders-and-notices, guidelines, gazettes-notifications, ...) answers with the same shape:
page.files = groups [{name, files_data: [{title, file, published_date, ...}]}], so one handler serves them all.

Queue item payload: {"slug": "orders-and-notices", "files_re": "debar|blacklist|..."}
Every document gets a record. A document's file is downloaded only when `files_re` matches "<group> <title>" (or `files_re` is "."),
which keeps a metadata crawl of ~7,000 PDFs cheap; widen the pattern in family.py to fetch more.
"""
import re
from urllib.parse import quote

from adapters.common import clean, sha1

SITE = "https://morth.gov.in"
API = SITE + "/backend/api"
HEADERS = {"Referer": SITE + "/", "Accept": "application/json"}


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


def run(ctx, payload):
    slug = payload["slug"]
    js = ctx.get_json("GET", f"{API}/{slug}", params={"page": 1, "per_page": 500, "wings": "", "order_by": "desc", "search": ""},
                      headers=HEADERS, timeout=120)
    if js is None:
        return None
    docs = parse_documents(js, slug)
    fetch = re.compile(payload.get("files_re") or "$^", re.I)
    for d in docs:
        data = dict(d)
        if d["url"] and fetch.search(f"{d['group']} {d['title']}"):
            data["file"] = ctx.download(d["url"], f"{slug}/{re.sub(r'[^a-z0-9]+', '-', d['group'].lower()).strip('-')[:50] or 'ungrouped'}", HEADERS)
        ctx.record(f"{slug}-{d['doc_id']}", data)
    return len(docs)
