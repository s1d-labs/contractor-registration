"""RDSO (rdso.indianrailways.gov.in): the lists of RDSO items with few approved sources.

The vendor directory itself is on IREPS UVAM, behind a guest sign-in with a mobile OTP, so it is not scraped. RDSO's own page
"list of items with few sources" (view_section.jsp id=0,5,6634) links three PDFs (Word tables, as on 03.06.2024): items with
fewer than three sources, fewer than five, and with no Indian source. Each row: department, sub-directorate, item id, item,
sub-item id, sub-item, vendor count (no vendor names). The site answers Indian addresses only (proxy="IN").

Queue item payload: {"section": "0,5,6634"}: reads the page, then every PDF it links about sources.
One record per item and list (`<list>-<item id>-<sub-item id or 0>`); each PDF is stored as pdf/rdso-items/<name>.
"""
import html
import re
from urllib.parse import urljoin

from adapters.common import clean, safe_name
from adapters.statepwd import join_words, pdf_pages

SITE = "https://rdso.indianrailways.gov.in"
FIELDS = ("sr", "department", "directorate", "item_id", "item", "subitem_id", "subitem", "vendor_count")
ITEM_ID = re.compile(r"^\d{7}(\d{3})?$")     # items 7 digits, sub-items 10


def section_url(section):
    return f"{SITE}/view_section.jsp?lang=0&id={section}"


def source_lists(page_html):
    """[(link text, url)] of the PDFs the page links about sources (English or Hindi captions). Pure."""
    out = []
    for href, text in re.findall(r'<a[^>]*href="([^"]*/uploads/[^"]+\.pdf)"[^>]*>(.*?)</a>', page_html or "", re.S | re.I):
        text = clean(html.unescape(re.sub(r"<[^>]+>", " ", text)))
        if re.search(r"(?i)source|स्रोत", text):
            out.append((text, urljoin(SITE, html.unescape(href))))
    return out


def list_name(title):
    m = re.search(r"(?i)less than (\w+) sources", title)
    if m:
        return f"fewer-than-{m.group(1).lower()}-sources"
    return "no-indigenous-source" if re.search(r"(?i)no indigenous source", title) else "items"


def _header(words):
    """The column borders from the two caption lines: caption words are merged into cells (overlapping, or less than 8 pt
    apart), and each border is half way between two cells (the captions are centred, the cells' text left-aligned)."""
    dep = next((w for w in words if w[3] == "Department"), None)
    if dep is None or not any(w[3] == "Vendor" and abs(w[1] - dep[1]) < 3 for w in words):
        return None, None
    cells = []
    for w in sorted((w for w in words if -14 <= w[1] - dep[1] <= 1), key=lambda w: w[0]):
        if cells and w[0] <= cells[-1][1] + 8:
            cells[-1][1] = max(cells[-1][1], w[2])
        else:
            cells.append([w[0], w[2]])
    if len(cells) != len(FIELDS):
        return None, dep[1]
    return [(a[1] + b[0]) / 2 for a, b in zip(cells, cells[1:])], dep[1]


def parse_items(pages):
    """(meta {title, as_on}, [{sr, group, department, directorate, item_id, item, subitem_id, subitem, vendor_count}]) from the
    words of every page (statepwd.page_words). Rows without an item id are group captions ("No Indian source and ..."). Pure."""
    meta, borders, rows = {"title": "", "as_on": ""}, None, []
    for words in pages:
        b, head_y = _header(words)
        if head_y is not None and not meta["title"]:
            meta["title"] = join_words([w for w in words if w[1] > head_y + 3 and not re.fullmatch(r"Annexure-\d+", w[3])])
            m = re.search(r"(?i)as on (?:date )?\(?(\d{2}\.\d{2}\.\d{4})", meta["title"])
            meta["as_on"] = m.group(1) if m else ""
        borders = b or borders
        if not borders:
            continue
        note = max((w[1] for w in words if w[3].startswith("Note") and w[0] < borders[1]), default=None)
        words = [w for w in words if (head_y is None or w[1] < head_y - 14) and (note is None or w[1] > note + 1)]
        for w in sorted(words, key=lambda w: (-round(w[1]), w[0])):
            same_line = rows and rows[-1]["page"] is words and rows[-1]["y"] == round(w[1])
            if col_of(w, borders) == 0 and re.fullmatch(r"\d+\.?", w[3]) and not same_line:
                rows.append({"y": round(w[1]), "page": words, "sr": w[3].rstrip("."), "words": []})
            elif rows:
                rows[-1]["words"].append(w)       # a row carried over to the next page joins the last row
    out, group = [], ""
    for r in rows:
        cols = lambda *i: [w for w in r["words"] if col_of(w, borders) in i]
        cells = {f: join_words(cols(i)) for i, f in enumerate(FIELDS)}
        item_id, item = _id_and_text(cols(3, 4))
        if not item_id:
            group = clean(" ".join(v for v in cells.values() if v).replace(" .", ""))
            continue
        subitem_id, subitem = _id_and_text(cols(5, 6))
        if not subitem_id:                        # no sub-item: the item's description may run over those columns
            item_id, item = _id_and_text(cols(3, 4, 5, 6))
            subitem = ""
        count = re.findall(r"\d+", cells["vendor_count"])
        out.append({"sr": r["sr"], "group": group, "department": cells["department"], "directorate": cells["directorate"],
                    "item_id": item_id, "item": item, "subitem_id": subitem_id, "subitem": subitem,
                    "vendor_count": int(count[-1]) if count else None})
    return meta, out


def _id_and_text(words):
    """An id cell and the description beside it, read as one: justified descriptions spread into the id column."""
    ident = next((w for w in words if ITEM_ID.match(w[3])), None)
    return (ident[3] if ident else ""), join_words([w for w in words if w is not ident and w[3].strip("-")])   # "--": none


def col_of(w, borders):
    return sum(w[0] >= x for x in borders)


def run(ctx, payload):
    section = payload.get("section", "0,5,6634")
    page = ctx.request("GET", section_url(section), timeout=60)
    if page is None:
        return None
    links = source_lists(page.content.decode("utf-8", "replace"))
    if not links:
        ctx.hub.failure("parse", section, "no lists about sources linked on the page any more")
        return 0
    n = 0
    for text, url in links:
        r = ctx.request("GET", url, timeout=120)
        if r is None or r.content[:5] != b"%PDF-":
            ctx.hub.failure("download", url[:200], "list did not load")
            continue
        meta, items = parse_items(pdf_pages(r.content))
        name = list_name(meta["title"])
        stored = ctx.hub.upload_many([(f"pdf/rdso-items/{safe_name(url.rsplit('/', 1)[-1])}", r.content, "application/pdf")])[0]
        for it in items:
            ctx.record(f"{name}-{it['item_id']}-{it['subitem_id'] or 0}",
                       {"kind": "rdso_item_sources", "list": name, **it, "list_title": meta["title"], "list_as_on": meta["as_on"],
                        "link_text": text, "url": url, "pdf_path": stored.get("path"), "source": section_url(section)})
        n += len(items)
    return n
