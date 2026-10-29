"""NHAI (nhai.gov.in): an Angular app on a Drupal JSON API, `POST https://nhai.gov.in/nhai/api/<endpoint>` with form fields.

Queue item payloads (the `kind` picks the handler):
  {"kind": "tenders",    "endpoint": "tenderlist" | "tenderarchive*", "page": 0, "detail": true, "files": false, "section": "tenders"}
  {"kind": "page",       "nid": "<route slug>"}            rest_api: a CMS page; its tables, document links and plain links
  {"kind": "commontype", "tid": "<type slug>"}            commontype: a typed list (e.g. blacklisted-debarred-firms)
Tenders that are empanelment calls (RFE / EOI / enlistment) always have their documents stored.
"""
import base64
import re
from urllib.parse import urljoin

from adapters.common import clean, sha1, url_ext, walk_page

SITE = "https://nhai.gov.in"
API = SITE + "/nhai/api"
PAGE_SIZE = 50                 # `totalrecord` per call; `index` is the 0-based page number
EMPANELMENT = re.compile(r"empanel|\bRFE\b|enlist|expression of interest|\bEOI\b|pre-?qualif", re.I)
HEADERS = {"Origin": SITE, "Referer": SITE + "/"}


def form(**fields):
    """requests sends these as multipart/form-data, which is what the site's own app sends."""
    return {k: (None, str(v)) for k, v in fields.items()}


def parse_tender_list(js):
    """(total_count, [tender dicts]) from tenderlist / tenderarchive*; ([]) when the site says no records."""
    js = js or {}
    rows = []
    for t in js.get("list") or []:
        rows.append({
            "id": str(t.get("id", "")), "title": clean(t.get("title")), "tender_no": clean(t.get("tender_no")),
            "publish_date": t.get("publish_date") or "", "bid_submission_end_date": t.get("bid_submission_end_date") or "",
            "bid_opening_date": t.get("bid_opening_date") or "",
            "tender_document_sales": t.get("tender_document_sales") or "", "tender_document_sales_end": t.get("tender_document_sales_end") or "",
        })
    return js.get("total_count") or 0, rows


def parse_tender_detail(js):
    """Flattened tenderdetail: only the fields that have a value, and the documents with absolute URLs."""
    d = (js or {}).get("detail") or {}
    first = lambda key: (d.get(key) or [{}])[0] or {}
    keep = lambda m: {k: clean(v) for k, v in m.items() if isinstance(v, str) and clean(v)}
    files = []
    for f in d.get("other_documents") or []:
        url = f.get("file") or f.get("path") or ""
        if url:
            files.append({"url": urljoin(SITE, url).replace("http://", "https://", 1), "description": clean(f.get("description")),
                          "size": f.get("filesize") or ""})
    return {"title": clean(d.get("title")), "basic": keep(first("basic_information")), "dates": keep(first("important_dates")),
            "documents": keep(first("documents")), "body": clean(re.sub(r"<[^>]+>", " ", d.get("body") or ""))[:5000], "files": files}


def parse_page(js, nid):
    """rest_api page -> {"title", "rows": [...], "docs": [...], "links": [...], "text"}.
    rows: table rows keyed by the header cells; docs: links to documents; links: every other link."""
    js = js or {}
    w = walk_page(js.get("body") or "")
    rows, in_rows = [], set()
    for t in w.tables:
        heads = t["headers"]
        for r in t["rows"]:
            cols = {(heads[i] if i < len(heads) and heads[i] else f"c{i}"): c for i, c in enumerate(r["cells"])}
            urls = [urljoin(SITE, l["href"]) for l in r["links"] if l["href"] and not l["href"].startswith(("#", "javascript", "mailto"))]
            in_rows.update(urls)
            rows.append({"columns": cols, "urls": urls})
    docs, links, seen = [], [], set()
    for l in w.links:
        href = l["href"]
        if not href or href.startswith(("#", "javascript", "javscript", "mailto", "tel:")):
            continue
        url = urljoin(SITE, href)
        if url in in_rows or url in seen:
            continue
        seen.add(url)
        item = {"url": url, "text": l["text"], "heading": l["heading"], "size": l["size"]}
        (docs if url_ext(url) else links).append(item)
    return {"title": clean(js.get("title")), "rows": rows, "docs": docs, "links": links, "text": clean("".join(w.text))[:3000]}


def run_tenders(ctx, p):
    js = ctx.get_json("POST", f"{API}/{p['endpoint']}", files=form(
        language="en", index=p["page"], totalrecord=PAGE_SIZE, tender_no="", title="", bid_from_date="", bid_to_date="",
        category_id="", department_id=""), headers=HEADERS)
    if js is None:
        return None
    total, tenders = parse_tender_list(js)
    section = p.get("section", "tenders")
    for t in tenders:
        data = {"kind": "tender", "endpoint": p["endpoint"], **t, "is_empanelment": bool(EMPANELMENT.search(t["title"])),
                "url": f"{SITE}/#/tender-detail/" + base64.b64encode(t["id"].encode()).decode().rstrip("=")}
        if p.get("detail", True):
            d = parse_tender_detail(ctx.get_json("POST", f"{API}/tenderdetail", files=form(language="en", nid=t["id"]), headers=HEADERS))
            data["detail"] = {k: v for k, v in d.items() if k != "files"}
            data["documents"] = d["files"]
            if p.get("files") or data["is_empanelment"]:
                for f in data["documents"]:
                    f["stored"] = ctx.download(f["url"], section, HEADERS)
        ctx.record(f"tender-{t['id']}", data)
    return len(tenders)


def run_page(ctx, p):
    nid = p["nid"]
    js = ctx.get_json("POST", f"{API}/rest_api", files=form(nid=nid, language="en"), headers=HEADERS)
    if js is None or not (js.get("body") or js.get("title")):
        return None
    page = parse_page(js, nid)
    section = p.get("section", re.sub(r"[^a-z0-9]+", "-", nid.lower()).strip("-")[:60])
    ctx.record(f"page-{nid}"[:200], {"kind": "page", "nid": nid, "url": f"{SITE}/#/{nid}", "title": page["title"], "text": page["text"],
                                      "n_rows": len(page["rows"]), "n_docs": len(page["docs"]), "n_links": len(page["links"])})
    n = 1
    for r in page["rows"]:
        stored = [ctx.download(u, section, HEADERS) for u in r["urls"] if url_ext(u)] if p.get("files", True) else []
        ctx.record(f"{nid}-row-{sha1(*r['columns'].values())[:12]}"[:200],
                   {"kind": "table_row", "nid": nid, "page_title": page["title"], **r, "files": stored})
        n += 1
    for d in page["docs"]:
        stored = ctx.download(d["url"], section, HEADERS) if p.get("files", True) else None
        ctx.record(f"{nid}-doc-{sha1(d['url'])[:12]}"[:200], {"kind": "document", "nid": nid, "page_title": page["title"], **d, "file": stored})
        n += 1
    for l in page["links"]:
        ctx.record(f"{nid}-link-{sha1(l['url'])[:12]}"[:200], {"kind": "link", "nid": nid, "page_title": page["title"], **l})
        n += 1
    return n


def run_commontype(ctx, p):
    tid = p["tid"]
    js = ctx.get_json("POST", f"{API}/commontype", files=form(tid=tid, language="en", index=0, totalrecord=100000, vid="common_type"),
                      headers=HEADERS)
    if js is None:
        return None
    n = 0
    for it in js.get("detail") or []:
        data = {"kind": "common", "tid": tid, "url": f"{SITE}/#/{tid}", **{k: v for k, v in it.items() if k != "upload_file"}}
        link = it.get("file") or it.get("link_uri") or it.get("external_link") or ""
        if link and url_ext(urljoin(SITE, link)) and p.get("files", True):
            data["file"] = ctx.download(urljoin(SITE, link), re.sub(r"[^a-z0-9]+", "-", tid.lower())[:60], HEADERS)
        ctx.record(f"common-{tid}-{it.get('id')}"[:200], data)
        n += 1
    return n


HANDLERS = {"tenders": run_tenders, "page": run_page, "commontype": run_commontype}


def run(ctx, payload):
    """Records stored for one queue item, or None if the site did not answer."""
    return HANDLERS[payload["kind"]](ctx, payload)
