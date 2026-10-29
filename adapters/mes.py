"""MES (mes.gov.in, Military Engineer Services): Drupal 11, server-rendered tables with a 0-based `?page=N` pager.

Queue item payload: {"path": "tenders", "page": 0, "files": true}
Each table row becomes a record keyed by its content (the serial-number column shifts as rows are added, so it is left out of
the id); the row's attachments are stored. Tender titles carry the CPPP id ("tender id_ 2026_MES_792606_1"), kept as tender_id.
The enlistment portal (CCEP) and product approval portal (PAP) need a login: DISCOVERY.md lists them; they are not scraped.
"""
import re
from urllib.parse import urljoin

from adapters.common import sha1, url_ext, walk_page

SITE = "https://mes.gov.in"
SERIAL = {"sn", "s.no", "s no", "sl no", "sr no", "s.no."}
TENDER_ID = re.compile(r"tender\s*id[\s_:.-]*(\d{4}_[A-Z]+_\d+_\d+)", re.I)


def parse_rows(page_html):
    """[{"columns": {header: cell}, "urls": [absolute attachment urls]}] for every table row on the page. Pure."""
    rows = []
    for t in walk_page(page_html).tables:
        heads = t["headers"]
        for r in t["rows"]:
            cols = {(heads[i] if i < len(heads) and heads[i] else f"c{i}"): c for i, c in enumerate(r["cells"])}
            urls = [urljoin(SITE, l["href"]) for l in r["links"] if l["href"] and not l["href"].startswith(("#", "javascript", "mailto"))]
            m = TENDER_ID.search(" ".join(cols.values()))
            rows.append({"columns": cols, "urls": urls, "tender_id": m.group(1).upper() if m else None})
    return rows


def row_id(path, cols):
    return sha1(path, *(v for k, v in cols.items() if k.strip().lower() not in SERIAL))[:14]


def run(ctx, payload):
    path, page = payload["path"].strip("/"), payload.get("page", 0)
    r = ctx.request("GET", f"{SITE}/{path}", params={"page": page} if page else None)
    if r is None:
        return None
    rows = parse_rows(r.content.decode("utf-8", "replace"))
    section = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")
    for row in rows:
        stored = [ctx.download(u, section) for u in row["urls"] if url_ext(u)] if payload.get("files", True) else []
        ctx.record(f"{section}-{row_id(path, row['columns'])}"[:200],
                   {"kind": "table_row", "path": path, "page": page, "url": f"{SITE}/{path}", **row, "files": stored})
    return len(rows)
