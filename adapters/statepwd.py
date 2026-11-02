"""State PWD / R&B departments: contractor registers the states publish as PDF lists. One queue item per list.

  gujarat-rnb-civil       rnb.gujarat.gov.in  R&B registered civil contractors, classes AA, A, B, C, D, E-1, E-2 (8,113 on 14-09-2026)
  gujarat-rnb-electrical  rnb.gujarat.gov.in  R&B registered electrical contractors, classes A and AA
  maharashtra-pwd-civil   pwd.maharashtra.gov.in (files on the S3WaaS CDN)  PWD registered civil contractors per district and
                          class (RTI manual no. 13, uploaded March 2025; most registrations valid up to 2013-2017)
  maharashtra-pwd-electrical  the same, electrical contractors
The PDFs are printed from a spreadsheet: they have a text layer, one table row per contractor, and the cells wrap over several
lines. The columns are found from where cells start on the page (the header's words are centred, the cells left-aligned), and
every word goes to the row whose serial number is the nearest above it. rnb.gujarat.gov.in answers Indian addresses only; the
Maharashtra files are on a CDN that answers from anywhere.

Queue item payload: {"list": "gujarat-rnb-civil"}
One record per row: division, company, address, class, nature of firm, registration date, certificate valid up to, and the
list's "as on" date. The PDF is stored as pdf/<list>/<list>-<as on>.pdf.
"""
import ctypes
import re
from collections import Counter

from adapters.common import clean, sha1

MH = "https://cdnbbsr.s3waas.gov.in/s3ea80421fc06a2ed5c7adc1018e0026df/uploads/2025/03/"
LISTS = {             # list -> (state, PDF)
    "gujarat-rnb-civil": ("Gujarat", "https://rnb.gujarat.gov.in/otherfile/Contractor%20Registration%20Final%20Data.pdf"),
    "gujarat-rnb-electrical": ("Gujarat", "https://rnb.gujarat.gov.in/otherfile/Aayog%20Electrical%20Contractor%20Registration%20Data.pdf"),
    "maharashtra-pwd-civil": ("Maharashtra", MH + "202503152104805692.pdf"),
    "maharashtra-pwd-electrical": ("Maharashtra", MH + "20250315163259010.pdf"),
}
SOURCES = {
    "Gujarat": "https://rnb.gujarat.gov.in/ (Contractors: R&B registered civil / electrical contractor list)",
    "Maharashtra": "https://pwd.maharashtra.gov.in/en/ (RTI manual no. 13: particulars of recipients of permits, list of contractors)",
}
DATE = re.compile(r"\b\d{2}-\d{2}-\d{4}\b")
MH_DATE = re.compile(r"\d{1,2}/\d{1,2}/\d{4}")
GROUP = re.compile(r"District\s*:\s*(.*?)\s*Class\s*:\s*(.*)$")
SOFT = "\x02"         # pdfium's mark for a word broken at the end of a line (it also gives U+FFFE for some)


def page_words(page):
    """[(x0, y, x1, text)] of one pypdfium2 page: characters joined into words; y is the baseline, from the bottom of the page
    (a character's box would put "-" or "(" off the line, and cells in another font size on another line)."""
    import pypdfium2.raw as pdfium_c
    tp = page.get_textpage()
    ox, oy = ctypes.c_double(), ctypes.c_double()
    out, cur = [], None
    for i in range(tp.count_chars()):
        ch = tp.get_text_range(i, 1).replace("\ufffe", SOFT)
        if ch == SOFT and cur:
            cur[3] += SOFT
        if not ch.strip() or ch == SOFT:
            cur = None
            continue
        left, _, right, _ = tp.get_charbox(i)
        pdfium_c.FPDFText_GetCharOrigin(tp.raw, i, ox, oy)
        if cur and abs(oy.value - cur[1]) < 1.5 and left - cur[2] < 4.5:     # pdfium gives the spaces; Word spreads digits
            cur[2], cur[3] = right, cur[3] + ch
        else:
            cur = [left, oy.value, right, ch]
            out.append(cur)
    return [tuple(w) for w in out]


def join_words(words):
    words = sorted(words, key=lambda w: (-round(w[1]), w[0]))
    return clean(" ".join(w[3] for w in words).replace(SOFT + " ", "-").replace(SOFT, "-"))


def _cell_starts(pages):
    """Counter of x positions where a cell starts: the first word of a line, or a word after a gap wider than a space."""
    starts = Counter()
    for words in pages:
        lines = {}
        for w in words:
            lines.setdefault(round(w[1]), []).append(w)
        for line in lines.values():
            prev = None
            for w in sorted(line):
                if prev is None or w[0] - prev[2] > 4:
                    starts[round(w[0])] += 1
                prev = w
    return starts


def _peak(starts, lo, hi):
    """The left edge of the most used cell start between lo and hi (3 pt buckets)."""
    buckets = Counter()
    for x, n in starts.items():
        if lo <= x <= hi:
            buckets[x // 3] += n
    if not buckets:
        return None
    b = buckets.most_common(1)[0][0]
    return min(x for x in starts if lo <= x <= hi and b - 1 <= x // 3 <= b + 1) - 1


def columns(pages):
    """Left edges of the division, company, address and class columns, from the first page's header and the cell starts, and
    where the "valid up to" dates begin (a row can have only one of its two dates)."""
    head = pages[0]
    div = next((w for w in head if w[3] == "Division"), None)
    if div is None:
        return None
    band = [w for w in head if -20 <= w[1] - div[1] <= 3]       # the caption lines, not the title above them
    find = lambda *names: min((w[0] for w in band if w[3] in names), default=None)
    sr, comp = find("Sr.No", "Sr."), min((w[0] for w in band if w[3] == "Company" and w[0] > div[0]), default=None)
    addr, cls, valid = find("Address"), find("Class", "Registered"), find("Certificate", "Valid")
    if None in (sr, comp, addr, cls, valid):
        return None
    starts = _cell_starts(pages)
    edges = (_peak(starts, sr + 10, div[0]), _peak(starts, div[0] + 30, comp), _peak(starts, comp + 30, addr), _peak(starts, addr + 30, cls + 12))
    return None if None in edges else (*edges, valid - 15)


def parse_list(pages):
    """(meta {title, as_on, total}, [{sr, division, company, address, class, nature_of_firm, registration_date, valid_upto}])
    from the words of every page (page_words). Pure."""
    meta = {"title": "", "as_on": "", "total": None}
    first = sorted(pages[0], key=lambda w: (-round(w[1]), w[0])) if pages else []
    if first:
        top = [w for w in first if abs(w[1] - first[0][1]) < 3]
        meta["title"] = join_words(top)
        m = re.search(r"(?i)as\s+on\s+(\d{2}-\d{2}-\d{4})", meta["title"])
        meta["as_on"] = m.group(1) if m else ""
        m = re.search(r"Total Registered [A-Za-z ]+:\s*(\d+)", join_words(first[:40]))
        meta["total"] = int(m.group(1)) if m else None
    cols = columns(pages) if pages else None
    if not cols:
        return meta, []
    b_div, b_comp, b_addr, b_tail, b_valid = cols
    rows = []
    for words in pages:
        header = next((w for w in words if w[3] == "Division" and any(v[3] == "Address" and abs(v[1] - w[1]) < 20 for v in words)), None)
        starts = sorted((w for w in words if w[2] < b_div and w[3].isdigit()), key=lambda w: -w[1])
        page_rows = [{"sr": w[3], "y": w[1], "words": []} for w in starts]
        for w in words:
            if w[2] < b_div and w[3].isdigit():
                continue
            if header and w[1] >= header[1] - 18:
                continue                                # title and column captions
            above = [r for r in page_rows if r["y"] + 3 >= w[1]]
            if above:
                above[-1]["words"].append(w)
            elif rows:
                rows[-1]["words"].append(w)             # a row carried over from the page before
        rows += page_rows
    out = []
    for r in rows:
        cell = lambda lo, hi: join_words([w for w in r["words"] if lo <= w[0] < hi])
        tail = cell(b_tail, 10_000)
        date = lambda lo, hi: next((w[3] for w in r["words"] if lo <= w[0] < hi and DATE.fullmatch(w[3])), "")
        m = re.match(r"(\S+)\s+Class\b", tail)
        nature = clean(DATE.sub(" ", tail[m.end():] if m else tail))
        out.append({"sr": r["sr"], "division": cell(b_div, b_comp), "company": cell(b_comp, b_addr), "address": cell(b_addr, b_tail),
                    "class": m.group(1) if m else "", "nature_of_firm": nature,
                    "registration_date": date(b_tail, b_valid), "valid_upto": date(b_valid, 10_000)})
    return meta, out


def mh_columns(pages):
    """Maharashtra lists: where each column starts, from the first page's captions and the cell starts."""
    head = pages[0]
    total = next((w for w in head if w[3] == "Total"), None)
    if total is None:
        return None
    x = {}
    for w in sorted((w for w in head if abs(w[1] - total[1]) < 2), key=lambda w: w[0]):
        x.setdefault(w[3], w[0])
    if any(k not in x for k in ("Sr.", "Contractor", "Company", "Address", "Phone", "Registration", "Exempted", "EMD")):
        return None
    starts = _cell_starts(pages)
    company, address = _peak(starts, x["Contractor"] + 20, x["Company"] + 5), _peak(starts, x["Company"] + 20, x["Address"] + 5)
    if None in (company, address):
        return None
    return {"sr": x["Sr."] - 3, "number": x["Contractor"] - 2, "company": company, "address": address, "phone": x["Phone"] - 15,
            "dates": x["Registration"] - 15, "exempted": x["Exempted"] - 15, "emd": x["EMD"] - 15}


def parse_mh(pages):
    """[{district, class, district_sr, sr, contractor_number, registration_no, registered_on, company, address, phone,
    valid_upto, exempted_upto, emd_exempted}] from the words of every page of a Maharashtra PWD list. "District : X Class : Y"
    lines head the rows under them, across pages. Pure."""
    c = mh_columns(pages) if pages else None
    if not c:
        return []
    rows, group = [], {"district": "", "class": ""}
    for words in pages:
        total = next((w for w in words if w[3] == "Total"), None)
        words = [w for w in words if w[1] > 15 and (total is None or w[1] < total[1] - 33)]   # page number, captions
        lines = {}
        for w in words:
            lines.setdefault(round(w[1]), []).append(w)
        marks = []                                          # (y, "group", {...}) or (y, "row", {...}), top of the page first
        taken = set()
        for y, line in lines.items():
            text = join_words(line)
            m = GROUP.search(text) if "District" in text else None
            if m:
                marks.append((y, "group", {"district": clean(m.group(1)), "class": clean(m.group(2))}))
                taken.update(map(id, line))
        nums = [w for w in words if w[0] < c["number"] and w[3].isdigit()]
        taken.update(map(id, nums))
        for y in sorted({round(w[1]) for w in nums}, reverse=True):     # "count in the district" then the serial number
            pair = sorted((w for w in nums if round(w[1]) == y), key=lambda w: w[0])
            if len(pair) >= 2 or pair[0][2] > c["sr"]:
                marks.append((pair[-1][1], "row", {"sr": pair[-1][3], "district_sr": pair[0][3] if len(pair) > 1 else "", "words": []}))
        marks.sort(key=lambda m: -m[0])
        for w in words:
            if id(w) in taken:
                continue
            above = [m for m in marks if m[0] + 3 >= w[1]]
            if above and above[-1][1] == "row":
                above[-1][2]["words"].append(w)
            elif not above and rows:
                rows[-1]["words"].append(w)                 # a row carried over from the page before
        for m in marks:
            if m[1] == "group":
                group = m[2]
            else:
                rows.append({**group, **m[2]})
    out = []
    for r in rows:
        ws = r.pop("words")
        cell = lambda lo, hi: [w for w in ws if lo <= w[0] < hi]
        right = cell(c["phone"], c["dates"])
        phone = [w for w in right if re.fullmatch(r"\d{6,12}", w[3])]
        number, company = join_words(cell(c["number"], c["company"])), join_words(cell(c["company"], c["address"]))
        if not company and not re.search(r"\d", number):
            number, company = "", number                    # some districts typed the name in the number column (Pune, Gondia)
        dated = re.search(r"\d{1,2}[./]\d{1,2}[./]\d{4}", number)
        dates = lambda lo, hi: next((w[3] for w in cell(lo, hi) if MH_DATE.fullmatch(w[3])), "")
        emd = [w[3] for w in cell(c["emd"], 10_000) if w[3] in ("Y", "N")]
        out.append({"district": r["district"], "class": r["class"], "district_sr": r["district_sr"], "sr": r["sr"],
                    "contractor_number": number, "registration_no": number.split()[0] if number else "",
                    "registered_on": dated.group(0).replace(".", "/") if dated else "", "company": company,
                    "address": join_words(cell(c["address"], c["phone"]) + [w for w in right if w not in phone]),
                    "phone": " ".join(w[3] for w in phone), "valid_upto": dates(c["dates"], c["exempted"]),
                    "exempted_upto": dates(c["exempted"], c["emd"]), "emd_exempted": emd[0] if emd else ""})
    return out


def pdf_pages(data):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(data)
    return [page_words(pdf[i]) for i in range(len(pdf))]


def row_id(name, row):
    """No id on the list: the company, address, division, class (one firm can hold several) and dates (a renewal is listed
    beside the older registration). Rows repeated word for word on the list are one record."""
    return f"{name}-{sha1(row['company'].upper(), row['address'].upper(), row['division'], row['class'], row['registration_date'], row['valid_upto'])[:14]}"


def mh_row_id(name, row):
    return f"{name}-{sha1(row['district'], row['class'], row['contractor_number'].upper(), row['company'].upper(), row['valid_upto'])[:14]}"


def run(ctx, payload):
    name = payload["list"]
    state, url = LISTS[name]
    r = ctx.request("GET", url, timeout=300)
    if r is None or r.content[:5] != b"%PDF-":
        return None
    pages = pdf_pages(r.content)
    if state == "Maharashtra":
        meta, rows, rid = {"as_on": "", "title": "", "total": None}, parse_mh(pages), mh_row_id
    else:
        (meta, rows), rid = parse_list(pages), row_id
    if not rows:
        ctx.hub.failure("parse", name, "no rows found in the PDF (layout changed?)")
        return None
    as_on = "".join(reversed(meta["as_on"].split("-"))) or url.rsplit("/", 1)[-1].split(".")[0][:8]
    stored = ctx.hub.upload_many([(f"pdf/{name}/{name}-{as_on}.pdf", r.content, "application/pdf")])[0]
    for row in rows:
        ctx.record(rid(name, row), {"kind": "state_contractor", "list": name, "state": state, **row,
                                    "list_as_on": meta["as_on"], "list_title": meta["title"], "list_total": meta["total"],
                                    "pdf_path": stored.get("path"), "url": url, "source": SOURCES[state]})
    if meta["total"] and meta["total"] != len(rows):
        ctx.hub.metric("rows_short_of_total", meta["total"] - len(rows))
    return len(rows)
