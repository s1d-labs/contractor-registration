"""Firms that public sector undertakings ban, debar or put "on holiday" (planned source D03): who may not bid.

Each list is one page on the organisation's site: either the list itself (an HTML table) or a page that links the list as a PDF
(the link changes with each new version, so the page is read first). PDF tables are read with pdfplumber; the stored PDF and its
text go to the bucket (pdf/<list>/...). Every row of the list becomes one record with the list's own columns (`columns`) and
common fields where a column says what it is: `firm`, `address`, `vendor_code`, `pan`, `banned_by`, `order_ref`, `from_date`,
`upto`, `period`, `reason`, `remarks`. A "-do-" cell repeats the cell above it. A row that runs over two table lines (no serial
number on the second) is joined to the row before it.

Payload {"list": "<name in LISTS>"}. Rows are as the organisation publishes them: some name individuals (proprietors) and carry
their PAN; keep them out of reports.
"""
import io
import re
from urllib.parse import urljoin

from adapters.common import clean, sha1

LISTS = {
    # name: org, page, kind (what the list says the firms are), pdf (regex of the PDF link on the page; none: the page is the table)
    "bhel-debarred": {"org": "BHEL", "page": "https://www.bhel.com/list-debarred-firms", "kind": "debarred",
                      "pdf": r"Debarred[^\"'<>]*\.pdf"},
    "bhel-banned": {"org": "BHEL", "page": "https://www.bhel.com/list-banned-firms", "kind": "banned",
                    "pdf": r"Banned_firms_list[^\"'<>]*\.pdf"},
    "oil-india": {"org": "Oil India", "page": "https://www.oil-india.com/", "kind": "blocked",
                  "pdf": r"BLOCKED_VENDOR_LIST[^\"'<>]*\.pdf"},
    "opal": {"org": "ONGC Petro additions (OPaL)", "page": "https://opalindia.in/", "kind": "holiday",
             "pdf": r"List_of_vendors_put_on_holiday[^\"'<>]*\.pdf[^\"'<>]*"},
    "nddb": {"org": "NDDB", "page": "https://www.nddb.coop/resources/tenders/blackfirms", "kind": "blacklisted"},
    "nhpc": {"org": "NHPC", "page": "https://www.nhpcindia.com/welcome/language/en/firmbanlist", "kind": "banned"},
    # bharatpetroleum.in answers 403 outside India: these two are in the proxied project (-banlists-in)
    "bpcl-holiday": {"org": "BPCL", "page": "https://www.bharatpetroleum.in/bharat-petroleum-for/business-associates/vendors.aspx",
                     "kind": "holiday", "pdf": r"bpcl-holiday-listing[^\"'<>]*\.pdf"},
    "bpcl-show-cause": {"org": "BPCL", "page": "https://www.bharatpetroleum.in/bharat-petroleum-for/business-associates/vendors.aspx",
                        "kind": "show_cause", "pdf": r"scn-list[^\"'<>]*\.pdf"},
    # hindustanpetroleum.com also answers 403 outside India; its procurement page links the current list as holiday_list.pdf
    "hpcl-holiday": {"org": "HPCL", "page": "https://www.hindustanpetroleum.com/purchase-procurement", "kind": "holiday",
                     "pdf": r"/holiday_list[^\"'<>]*\.pdf"},
}

SERIAL = re.compile(r"^\d{1,4}\s*[.)]?$")
FIRST_HEAD = re.compile(r"^(s\.?\s*no|s[li]\.?\s*no|sl\.?|sr\.?|serial)", re.I)   # "SI. No." (capital I) too
PAN = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
DITTO = re.compile(r"^-?\s*do\s*-?$", re.I)
# common field <- header words (first match wins, in this order)
FIELDS = [
    ("vendor_code", r"vendor code|\bcode\b|^pan\b|/\s*pan\b"),
    ("firm", r"\bname\b"),                        # "Name & Address of the Vendor" is the firm (with its address)
    ("address", r"address|city"),                 # "Address of the Firm" is the address
    ("firm", r"firm|vendor|supplier|contractor\b|bidder"),
    ("banned_by", r"who banned|ministry|organi[sz]ation|issuing|sbu|entity"),
    ("order_ref", r"ref|letter|proposal|order"),
    ("upto", r"\bto\b|end date|expir|upto|up to|lifting|extend"),
    ("from_date", r"w\.?e\.?f|effective|start|date of|from|date"),
    ("period", r"period"),
    ("reason", r"reason"),
    ("remarks", r"remark"),
]


def _cell(c):
    return clean(re.sub(r"\s*\n\s*", " ", c or ""))


def _key(head):
    return re.sub(r"[^a-z0-9]+", "_", head.lower()).strip("_")[:60] or "column"


def _is_head(cells):
    words = " ".join(cells).lower()
    return bool(cells) and FIRST_HEAD.match(cells[0] or "") is not None and ("name" in words or "firm" in words or "vendor" in words)


def common_fields(columns):
    """{common field: value} from a row's {header: value}. Pure."""
    out = {}
    for head, value in columns.items():
        h = head.lower()
        for field, pat in FIELDS:
            if re.search(pat, h):
                if field not in out and value:
                    out[field] = value
                break
    return out


def table_rows(tables):
    """Rows of a list given as tables (each a list of rows of cells, as pdfplumber or an HTML table gives them):
    [{"sr", "section", "columns": {header: value}}]. Pure."""
    head, base, sub, section, out = None, None, False, "", []
    full = {}                                     # header line as printed -> header with its second line (From / To) merged
    for table in tables:
        for raw in table:
            cells = [_cell(c) for c in raw]
            filled = [c for c in cells if c]
            if not filled:
                continue
            if _is_head(cells):
                base = tuple(cells)
                head = []
                for i, c in enumerate(cells):             # an empty header cell is the right half of a merged one
                    head.append(c or (head[-1] if head else f"column {i + 1}"))
                head, sub = list(full.get(base, head)), base not in full
                continue
            if head and FIRST_HEAD.match(cells[0]) and len(filled) > 1:   # "Sr. No. | Banned as per instruction from Govt."
                section = " ".join(filled[1:])[:120]
                continue
            if head and sub and not cells[0] and len(filled) > 1 and len(cells) == len(head) and all(len(c) < 20 for c in filled):
                head = [f"{h} {c}".strip() if c else h for h, c in zip(head, cells)]   # a second header line (From / To)
                full[base] = list(head)
                sub = False
                continue
            sub = False
            if head and SERIAL.match(cells[0]) and len(cells) == len(head):
                prev = out[-1]["columns"] if out else {}
                cols = {}
                for h, c in zip(head[1:], cells[1:]):
                    cols[h] = prev.get(h, "") if DITTO.match(c) else c
                out.append({"sr": cells[0].rstrip(".)").strip(), "section": section, "columns": cols})
            elif head and out and not cells[0] and len(cells) == len(head):
                cols = out[-1]["columns"]                                          # the row goes on in the next table line
                for h, c in zip(head[1:], cells[1:]):
                    if c:
                        cols[h] = f"{cols.get(h, '')} {c}".strip()
            elif (len(filled) == 1 and len(filled[0]) < 120 and not filled[0].lower().startswith(("note", "nb"))
                  and not re.match(r"(?i)(as on|date)\b", filled[0])):
                section = filled[0]                                                # a title line inside the list
    return out


def html_tables(page):
    """Tables of an HTML page as lists of rows of cell texts. Pure."""
    import html as _html
    tables = []
    for t in re.findall(r"<table.*?</table>", page or "", re.S | re.I):
        rows = []
        for tr in re.findall(r"<tr.*?</tr>", t, re.S | re.I):
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)
            rows.append([_html.unescape(re.sub(r"<br\s*/?>", "\n", re.sub(r"<(?!br)[^>]+>", " ", c), flags=re.I)) for c in cells])
        tables.append(rows)
    return tables


def pdf_tables(data):
    """(tables, text) of a PDF. Each table starts with the line printed just above it, as a one-cell row: lists put the
    title of a part there ("Firms Debarred as per Government Instruction")."""
    import pdfplumber
    tables = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            for t in page.find_tables():
                top = t.bbox[1]
                above = page.crop((0, max(0, top - 24), page.width, top)).extract_text() if top > 2 else ""
                line = (above or "").strip().splitlines()[-1:] or [""]
                rows = t.extract()
                tables.append(([[line[0]]] if line[0] and not re.match(r"(?i)^(page\s*)?\d+(\s*of\s*\d+)?$", line[0]) else []) + rows)
        return tables, "\n".join(p.extract_text() or "" for p in pdf.pages)


def pdf_link(page, base, pattern):
    """The first link on the page whose address matches the list's PDF pattern, made absolute. Pure."""
    import html as _html
    for href in re.findall(r"""href\s*=\s*["']([^"']+)["']""", page or "", re.I):
        href = _html.unescape(href).strip()
        if re.search(pattern, href, re.I):
            return urljoin(base, href.replace(" ", "%20"))
    return None


def to_records(name, rows, source, extra=None):
    """(record id, record) for each row of a list. Pure."""
    spec = LISTS[name]
    seen = {}
    for row in rows:
        cols = row["columns"]
        common = common_fields(cols)
        text = " ".join(cols.values())
        pan = PAN.search(text)
        ident = sha1(name, (common.get("firm") or text).upper(), common.get("from_date", ""), common.get("order_ref", ""))[:16]
        seen[ident] = seen.get(ident, 0) + 1
        rid = f"{name}-{ident}" + (f"-{seen[ident]}" if seen[ident] > 1 else "")
        yield rid, {"kind": "banned_firm", "list": name, "org": spec["org"], "list_kind": spec["kind"], "sr": row["sr"],
                    "section": row["section"], **common, **({"pan": pan.group(1)} if pan else {}),
                    "columns": {_key(h): v for h, v in cols.items()}, "source": source, **(extra or {})}


def run(ctx, payload):
    name = payload["list"]
    spec = LISTS[name]
    r = ctx.request("GET", spec["page"], timeout=90)
    if r is None:
        return None
    page = r.content.decode(r.encoding or "utf-8", "replace") if r.content[:5] != b"%PDF-" else ""
    extra = {}
    if spec.get("pdf"):
        if r.content[:5] == b"%PDF-":                  # the page address redirects to the PDF itself (BHEL, 14 Nov 2026)
            url, d = r.url, r
        else:
            url = pdf_link(page, r.url, spec["pdf"])
            if not url:
                ctx.hub.failure("layout", name, f"no link matching {spec['pdf']} on {spec['page']}")
                return None
            d = ctx.request("GET", url, timeout=180)
            if d is None:
                return None
        if d.content[:5] != b"%PDF-":
            ctx.hub.failure("layout", name, f"{url} is not a PDF")
            return None
        tables, text = pdf_tables(d.content)
        file = url.rsplit("/", 1)[-1].split("?")[0]
        stored = ctx.hub.upload_many([(f"pdf/{name}/{sha1(url)[:8]}-{re.sub(r'[^A-Za-z0-9._-]+', '_', file)[:80]}", d.content,
                                       "application/pdf")])[0]
        extra = {"pdf_url": url, "pdf_path": stored.get("path"), "pdf_sha256": stored.get("sha256")}
        source = f"{url} (linked from {spec['page']})"
        if not text.strip():
            ctx.hub.failure("scan", name, f"{url} has no text layer (OCR later)")
    else:
        tables, source = html_tables(page), spec["page"]
    rows = table_rows(tables)
    if not rows:
        ctx.hub.failure("parse", name, "no rows with a serial number found (layout changed?)")
        return None if not extra else 0
    n = 0
    for rid, rec in to_records(name, rows, source, extra):
        ctx.record(rid, rec)
        n += 1
    return n
