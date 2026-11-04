"""State PWD / R&B departments: contractor registers the states publish (PDF lists, HTML tables, online registration reports).
One queue item per list.

  gujarat-rnb-civil       rnb.gujarat.gov.in  R&B registered civil contractors, classes AA, A, B, C, D, E-1, E-2 (8,113 on 14-09-2026)
  gujarat-rnb-electrical  rnb.gujarat.gov.in  R&B registered electrical contractors, classes A and AA
  maharashtra-pwd-civil   pwd.maharashtra.gov.in (files on the S3WaaS CDN)  PWD registered civil contractors per district and
                          class (RTI manual no. 13, uploaded March 2025; most registrations valid up to 2013-2017)
  maharashtra-pwd-electrical  the same, electrical contractors
Document lists (DOC_PAGES): a page that lists registers as PDF downloads; every PDF is stored (scans under ocr-needed/, OCR later)
and each row of the page becomes a record pointing to its file.
  wb-phed-approved-vendors  wbphed.gov.in  West Bengal PHED approved vendors, civil and electro-mechanical items (scanned
                            lists, 12-10-2026 back to 2024)
The PDFs are printed from a spreadsheet: they have a text layer, one table row per contractor, and the cells wrap over several
lines. The columns are found from where cells start on the page (the header's words are centred, the cells left-aligned), and
every word goes to the row whose serial number is the nearest above it. rnb.gujarat.gov.in answers Indian addresses only; the
Maharashtra files are on a CDN that answers from anywhere.

Online registers (HTML tables):
  uttarakhand-pwd-<A|B|C|D>  registrationpwd.uk.gov.in  PWD Uttarakhand's online contractor registration: every application of the
                          class (36,405 on 4 Nov 2026, 33,858 granted) with office, dates, firm, address, category, status,
                          registration number (which ends in the firm's PAN) and validity. One GET per class (class D: 91 MB).
                          The server needs TLS legacy renegotiation (common.LEGACY_TLS).
  odisha-works-<civil|electrical>  works.odisha.gov.in  Works Department contractor ledger (Super / Special / A / B class civil,
                          MV / HT electrical): name and address, a Drupal table of 20 rows a page, read per class.
  tripura-pwd-enlisted    pwd.tripura.gov.in  PWD (R&B) Tripura enlisted contractors, one table per class (I to IV, electrical IE,
                          services SE): enlistment no, name, father's / partner's name, address, validity, tender limit; each
                          row's enlistment certificate (PDF) is stored too.
Column PDF lists (COLUMN_LISTS): one table row per firm, columns found from the header words on each page.
  arunachal-pwd-class-i|ii|iii  arunachalpwd.org  PWD Arunachal Pradesh valid enlisted / re-validated civil contractors, classes
                          IAA / IA / I, II and III, as on 30-09-2026 (the page lists newer files under new dated folders)
Numbered PDF lists (NUMBERED): "1. Firm, address" entries, one per contractor.
  haryana-pwd-class1      haryanapwd.gov.in  PWD (B&R) Haryana contractors enlisted in Class-1, 1.4.2014 to 16.12.2020
Linked documents (LINK_PAGES): the contractor-related PDFs a page links to (lists, cancellation / extension orders, memoranda,
corrigenda), stored for reading later (most are scans).
  arunachal-pwd-documents arunachalpwd.org/contractors.php

Queue item payload: {"list": "gujarat-rnb-civil"}, {"doc_page": "wb-phed-approved-vendors"}, {"uk_class": "A"},
{"ledger": "odisha-works-civil"}, {"tables": "tripura-pwd-enlisted"}, {"columns": "arunachal-pwd-class-i"},
{"numbered": "haryana-pwd-class1"} or {"links": "arunachal-pwd-documents"}.
PDF lists (Gujarat, Maharashtra): one record per row: division, company, address, class, nature of firm, registration date,
certificate valid up to, and the list's "as on" date. The PDF is stored as pdf/<list>/<list>-<as on>.pdf.
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
DOC_PAGES = {         # page -> (state, URL of the page listing the PDFs)
    "wb-phed-approved-vendors": ("West Bengal", "https://wbphed.gov.in/en/approved-vendor-list"),
}
UK = "https://registrationpwd.uk.gov.in/Report/Contractor_Information.aspx?contractor="
UK_SOURCE = "https://registrationpwd.uk.gov.in/Dashboard.aspx (PWD Uttarakhand, Contractor Registration System: Registration Reports)"
PAN = re.compile(r"^(.*?):\s*([A-Z]{5}[0-9]{4}[A-Z])$")
LEDGERS = {           # ledger -> (state, page, filter field, {value: class})
    "odisha-works-civil": ("Odisha", "https://works.odisha.gov.in/en/more/contractor-ledger/civil", "field_civil_contractor_value",
                           {"1": "Super Class", "2": "Special Class", "3": "A Class", "4": "B Class"}),
    "odisha-works-electrical": ("Odisha", "https://works.odisha.gov.in/en/more/contractor-ledger/electrical",
                                "field_electrical_contractor_value", {"1": "MV", "2": "HT"}),
}
TABLE_PAGES = {       # page -> (state, URL): accordion sections of enlisted-contractor tables
    "tripura-pwd-enlisted": ("Tripura", "https://pwd.tripura.gov.in/enlistment-of-contractors-2/"),
}
COLUMN_LISTS = {      # list -> (state, PDF): tables with Sl / Name of firm / Address / Enlistment No. & Date / Validity / Remarks
    "arunachal-pwd-class-i": ("Arunachal Pradesh", "https://arunachalpwd.org/pdf/06102026/Class-IAA-I-A_I-ason-30092026.pdf"),
    "arunachal-pwd-class-ii": ("Arunachal Pradesh", "https://arunachalpwd.org/pdf/06102026/Class-II-ason-30092026.pdf"),
    "arunachal-pwd-class-iii": ("Arunachal Pradesh", "https://arunachalpwd.org/pdf/06102026/Class-III-ason-30092026.pdf"),
}
LINK_PAGES = {        # page -> (state, URL): every contractor-related PDF linked from the page is stored, one record per link
    "arunachal-pwd-documents": ("Arunachal Pradesh", "https://arunachalpwd.org/contractors.php"),
}
NUMBERED = {          # list -> (state, PDF, title)
    "haryana-pwd-class1": ("Haryana", "https://haryanapwd.gov.in/home/docs/Contractor%20List.pdf",
                           "List of enlisted contractors as Class-1 category for the period from 1.4.2014 to 16.12.2020"),
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


def parse_doc_table(page_html, base):
    """[{sl, category, description, issue_date, url}] from a page's table of downloads (header row of <th>, one link per row).
    Pure."""
    import html as _html
    from urllib.parse import quote, urljoin
    tables = re.findall(r"<table.*?</table>", page_html or "", re.S)
    if not tables:
        return []
    heads, out = [], []
    for r in re.findall(r"<tr.*?</tr>", max(tables, key=len), re.S):
        ths = re.findall(r"<th[^>]*>(.*?)</th>", r, re.S)
        if ths:
            heads = [clean(_html.unescape(re.sub(r"<[^>]+>", " ", h))).lower() for h in ths]
            continue
        cells = [clean(_html.unescape(re.sub(r"<[^>]+>", " ", c))) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        link = re.search(r'href="([^"]+)"', r)
        if not link or len(cells) < 4:
            continue
        row = dict(zip(heads, cells))
        url = urljoin(base, quote(_html.unescape(link.group(1)), safe="/:()%.-_"))
        out.append({"sl": row.get("sl no.", cells[0]), "category": row.get("category", cells[1]),
                    "description": row.get("description", cells[2]), "issue_date": row.get("issue date", cells[3]), "url": url})
    return out


def run_doc_page(ctx, name):
    state, url = DOC_PAGES[name]
    r = ctx.request("GET", url, timeout=120)
    if r is None:
        return None
    rows = parse_doc_table(r.content.decode("utf-8", "replace"), url)
    if not rows:
        ctx.hub.failure("parse", name, "no downloads found in the page's table (layout changed?)")
        return None
    for row in rows:
        stored = ctx.download(row["url"], name)
        ctx.record(f"{name}-{sha1(row['url'])[:14]}", {"kind": "state_register_document", "list": name, "state": state, **row,
                                                       "file": stored, "source": url})
    return len(rows)


def _cells(row_html):
    import html as _html
    return [clean(_html.unescape(re.sub(r"<[^>]+>", " ", c))) for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)]


UK_FIELDS = ["sno", "office", "application_no", "applied_date", "company", "address", "class", "category", "status", "timeline",
             "registration_no", "valid_upto"]


def parse_uk(page_html):
    """Rows of PWD Uttarakhand's "View All Application with their Status" table, one per application: an application sent to
    several offices is listed once per office, so those rows merge into one with every office in `offices`. The registration
    number ends in ":<PAN>", split off into `pan`. Pure."""
    i = (page_html or "").find('id="tblAllApplications"')
    if i < 0:
        return []
    body = page_html[i:page_html.find("</table>", i)]
    out, by_no = [], {}
    for r in re.findall(r"<tr.*?</tr>", body, re.S):
        c = _cells(r)
        if len(c) != len(UK_FIELDS) or not c[2].isdigit():
            continue
        row = dict(zip(UK_FIELDS, c))
        row["class"] = row["class"].replace("Class ", "")
        m = PAN.match(row["registration_no"])
        row["pan"] = m.group(2) if m else ""
        if m:
            row["registration_no"] = m.group(1).strip()
        if row["application_no"] in by_no:
            by_no[row["application_no"]]["offices"].append(row["office"])
            continue
        row["offices"] = [row.pop("office")]
        row.pop("sno")
        by_no[row["application_no"]] = row
        out.append(row)
    return out


def run_uk(ctx, cls):
    url = UK + cls
    r = ctx.request("GET", url, timeout=600)
    if r is None:
        return None
    rows = parse_uk(r.content.decode("utf-8", "replace"))
    if not rows:
        ctx.hub.failure("parse", f"uttarakhand-pwd-{cls}", "no applications found in the report (layout changed, or signed out?)")
        return None
    for row in rows:
        ctx.record(f"uttarakhand-pwd-{row['application_no']}", {"kind": "state_contractor", "list": f"uttarakhand-pwd-{cls}",
                                                                 "state": "Uttarakhand", **row, "url": url, "source": UK_SOURCE})
    return len(rows)


def parse_ledger(page_html):
    """([{sr, company, address}], has next page) from a Drupal views table (Odisha Works contractor ledger). Pure."""
    import html as _html
    t = re.search(r"<tbody>(.*?)</tbody>", page_html or "", re.S)
    rows = []
    for r in re.findall(r"<tr.*?</tr>", t.group(1) if t else "", re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
        if len(cells) < 3:
            continue
        address = "; ".join(clean(_html.unescape(re.sub(r"<[^>]+>", " ", p))) for p in re.split(r"</p>|<br\s*/?>", cells[2]))
        rows.append({"sr": clean(re.sub(r"<[^>]+>", " ", cells[0])), "company": clean(_html.unescape(re.sub(r"<[^>]+>", " ", cells[1]))),
                     "address": "; ".join(x for x in address.split("; ") if x)})
    return rows, 'rel="next"' in (page_html or "") or "Next page" in (page_html or "")


def run_ledger(ctx, name):
    state, url, field, classes = LEDGERS[name]
    n = 0
    for value, cls in classes.items():
        for page in range(200):
            r = ctx.request("GET", url, params={field: value, "page": page}, timeout=120)
            if r is None:
                return None
            rows, more = parse_ledger(r.content.decode("utf-8", "replace"))
            for row in rows:
                ctx.record(f"{name}-{sha1(cls, row['company'].upper(), row['address'].upper())[:14]}",
                           {"kind": "state_contractor", "list": name, "state": state, "class": cls, **row,
                            "url": url, "source": f"{url} (Works Department, Government of Odisha: Contractor Ledger)"})
            n += len(rows)
            if not rows or not more:
                break
    if not n:
        ctx.hub.failure("parse", name, "no contractors found in the ledger (layout changed?)")
        return None
    return n


TRIPURA_FIELDS = ["enlistment_no", "contractor", "father_or_partner", "address", "validity", "qualified_upto"]


def parse_accordion_tables(page_html):
    """Rows of every table on an Elementor accordion page (PWD Tripura), each with the title of the section it sits in.
    Validity "YYYY-MM-DD to YYYY-MM-DD" (or one date: valid up to) splits into valid_from / valid_upto; the row's link (the
    enlistment certificate) is kept. Pure."""
    import html as _html
    page_html = page_html or ""
    titles = [(m.start(), clean(_html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).replace("\u200b", "").strip())
              for m in re.finditer(r'class="e-n-accordion-item-title-text">(.*?)</div>', page_html, re.S)]
    out = []
    for m in re.finditer(r"<table.*?</table>", page_html, re.S):
        section = next((t for at, t in reversed(titles) if at < m.start()), "")
        for r in re.findall(r"<tr.*?</tr>", m.group(0), re.S):
            cells = [re.sub(r"<span.*?</span>\s*</span>", "", c, flags=re.S) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
            if len(cells) < len(TRIPURA_FIELDS):
                continue
            row = dict(zip(TRIPURA_FIELDS, (clean(_html.unescape(re.sub(r"<[^>]+>", " ", c))) for c in cells)))
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", row["validity"])
            row["valid_from"], row["valid_upto"] = (dates[0], dates[-1]) if len(dates) > 1 else ("", dates[0] if dates else "")
            link = re.search(r'href="([^"]+\.pdf)"', r, re.I)
            row["certificate_url"] = _html.unescape(link.group(1)) if link else ""
            row["section"] = section
            out.append(row)
    return out


def run_tables(ctx, name):
    state, url = TABLE_PAGES[name]
    r = ctx.request("GET", url, timeout=180)
    if r is None:
        return None
    rows = parse_accordion_tables(r.content.decode("utf-8", "replace"))
    if not rows:
        ctx.hub.failure("parse", name, "no enlisted contractors found in the page's tables (layout changed?)")
        return None
    for row in rows:
        stored = ctx.download(row["certificate_url"], f"{name}-certificates") if row["certificate_url"] else None
        ctx.record(f"{name}-{sha1(row['section'], row['enlistment_no'], row['contractor'].upper())[:14]}",
                   {"kind": "state_contractor", "list": name, "state": state, **row, "certificate": stored, "url": url,
                    "source": f"{url} (PWD (R&B), Government of {state}: Enlistment of Contractors)"})
    return len(rows)


def parse_numbered(text):
    """[{sr, entry}] from a list whose entries are "12. Firm, address" over one or more lines. Pure."""
    text = (text or "").replace("\r", "\n").replace("\ufffe", "-").replace("\x02", "-")
    out, expect = [], 1
    for m in re.finditer(r"(?m)^\s*(\d{1,5})\s*\.\s*", text):
        if int(m.group(1)) == expect:
            out.append([expect, m.end()])
            expect += 1
    rows = []
    for i, (n, start) in enumerate(out):
        end = text.rfind("\n", start, out[i + 1][1]) if i + 1 < len(out) else len(text)
        rows.append({"sr": str(n), "entry": clean(text[start:end].replace("\n", " "))})
    return rows


COLUMN_HEADS = ("Name", "Address", "Enlistment", "Validity", "Remarks")


def parse_columns(pages):
    """(meta, rows) from a list laid out as Sl | Name of firm | Address | Enlistment No. & Date | Validity | Remarks (PWD Arunachal
    Pradesh). Each page repeats the header: its words give the column edges (cells start a little left of their heading). A
    row starts at a serial number in the first column; lines before the first one on a page continue the previous row.
    "CLASS - IAA" lines inside the table set the class of the rows below. Pure."""
    meta, rows, cur, cls = {"as_on": "", "title": ""}, [], None, ""
    for pi, words in enumerate(pages):
        head = {}
        for w in words:
            if w[3] in COLUMN_HEADS and w[3] not in head:
                head[w[3]] = w
        if len(head) < len(COLUMN_HEADS):
            continue
        top = head["Remarks"][1]
        bottom = min([w[1] for w in words if top - 16 <= w[1] <= top + 2 and w[0] < head["Remarks"][0] + 40] + [top])
        edges = [head["Name"][0] - 30, head["Address"][0] - 10, head["Enlistment"][0] - 8, head["Validity"][0] - 18, head["Remarks"][0] - 6]
        lines = {}
        for w in words:
            if w[1] < bottom - 1:
                lines.setdefault(round(w[1]), []).append(w)
        title = join_words([w for w in words if w[1] > top + 5 and "Page" not in w[3]])
        m = re.search(r"(?:as\s+on)\s+(\d{2}/\d{2}/\d{4})", title, re.I)
        if m and not meta["as_on"]:
            meta["as_on"], meta["title"] = m.group(1), re.sub(r"Page \d+ of \d+", "", title).strip()
        for y in sorted(lines, reverse=True):
            line = sorted(lines[y])
            text = join_words(line)
            if [w[3] for w in line] == [str(k) for k in range(1, 7)] or re.fullmatch(r"Page \d+ of \d+", text):
                continue
            c = re.fullmatch(r"CLASS\s*-\s*([A-Z/]+)\s*(?:\(.*\))?", text, re.I)
            if c:
                cls = c.group(1).upper()
                continue
            if re.match(r"NB\s*:", text):                    # the closing note and signature on the last page
                break
            first = line[0]
            if first[0] < edges[0] and first[3].rstrip(".").isdigit():
                cur = {"sr": first[3].rstrip("."), "class": cls, "cols": [[] for _ in range(5)]}
                rows.append(cur)
                line = line[1:]
            if cur is None:
                continue
            for w in line:
                k = sum(1 for e in edges if w[0] >= e) - 1
                cur["cols"][max(0, k)].append((w[0], w[1] - 10000 * pi, w[2], w[3]))   # keeps page order in join_words
    m = re.search(r"CLASS\s*-?\s*([IVX/A]+)\s*\(", meta["title"], re.I)
    title_cls = m.group(1).upper() if m and "/" not in m.group(1) else ""
    out = []
    for r in rows:
        name, address, enl, valid, remarks = (join_words(ws) for ws in r["cols"])
        parts = re.split(r"\b(?:Dated|Dtd|Dt)\b[.:]?", enl, maxsplit=1, flags=re.I)
        no, dated = parts[0], parts[1] if len(parts) > 1 else ""
        out.append({"sr": r["sr"], "class": r["class"] or title_cls, "company": name, "address": address, "enlistment_no": clean(no),
                    "enlistment_date": clean(dated).rstrip("."), "valid_upto": valid, "remarks": remarks})
    return meta, out


def run_columns(ctx, name):
    state, url = COLUMN_LISTS[name]
    r = ctx.request("GET", url, timeout=300)
    if r is None or r.content[:5] != b"%PDF-":
        return None
    meta, rows = parse_columns(pdf_pages(r.content))
    if not rows:
        ctx.hub.failure("parse", name, "no rows found in the PDF (layout changed?)")
        return None
    stored = ctx.hub.upload_many([(f"pdf/{name}/{url.rsplit('/', 1)[-1]}", r.content, "application/pdf")])[0]
    for row in rows:
        ctx.record(f"{name}-{sha1(row['class'], row['enlistment_no'].upper(), row['company'].upper())[:14]}",
                   {"kind": "state_contractor", "list": name, "state": state, **row, "list_as_on": meta["as_on"],
                    "list_title": meta["title"], "pdf_path": stored.get("path"), "url": url,
                    "source": f"https://arunachalpwd.org/contractors.php ({meta['title'] or name})"})
    return len(rows)


DOC_TYPES = (("cancellation", r"cancel"), ("extension", r"extend|extension"), ("corrigendum", r"corrigendum"),
             ("fake_enlistment", r"fake"), ("memorandum", r"memorandum"), ("list", r"list of|registered contractor"),
             ("rules", r"rules?\b|circular|certificate"))


def parse_pdf_links(page_html, base):
    """[{title, url, doc_type}] of the PDF links on a page whose text is about contractors (enlistment, registration, lists,
    cancellations), first occurrence of each URL. Pure."""
    import html as _html
    from urllib.parse import quote, urljoin
    out, seen = [], set()
    for href, text in re.findall(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', page_html or "", re.S | re.I):
        title = clean(_html.unescape(re.sub(r"<[^>]+>", " ", text)))
        url = urljoin(base, quote(_html.unescape(href), safe="/:()%.-_'"))
        if url in seen or not re.search(r"contract|enlist|regist|firm", title, re.I):
            continue
        seen.add(url)
        kind = next((k for k, rx in DOC_TYPES if re.search(rx, title, re.I)), "other")
        out.append({"title": title, "url": url, "doc_type": kind})
    return out


def run_links(ctx, name):
    state, url = LINK_PAGES[name]
    r = ctx.request("GET", url, timeout=120)
    if r is None:
        return None
    links = parse_pdf_links(r.content.decode("utf-8", "replace"), url)
    if not links:
        ctx.hub.failure("parse", name, "no contractor documents linked from the page (layout changed?)")
        return None
    for link in links:
        stored = ctx.download(link["url"], name)
        ctx.record(f"{name}-{sha1(link['url'])[:14]}", {"kind": "state_register_document", "list": name, "state": state, **link,
                                                        "file": stored, "source": url})
    return len(links)


def run_numbered(ctx, name):
    state, url, title = NUMBERED[name]
    r = ctx.request("GET", url, timeout=180)
    if r is None or r.content[:5] != b"%PDF-":
        return None
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(r.content)
    rows = parse_numbered("\n".join(doc[i].get_textpage().get_text_range() for i in range(len(doc))))
    if not rows:
        ctx.hub.failure("parse", name, "no numbered entries found in the PDF (scan, or layout changed?)")
        return None
    stored = ctx.hub.upload_many([(f"pdf/{name}/{name}.pdf", r.content, "application/pdf")])[0]
    for row in rows:
        ctx.record(f"{name}-{sha1(row['entry'].upper())[:14]}", {"kind": "state_contractor", "list": name, "state": state, **row,
                                                                 "list_title": title, "pdf_path": stored.get("path"), "url": url,
                                                                 "source": f"{url} ({title})"})
    return len(rows)


def mh_row_id(name, row):
    return f"{name}-{sha1(row['district'], row['class'], row['contractor_number'].upper(), row['company'].upper(), row['valid_upto'])[:14]}"


def run(ctx, payload):
    if payload.get("doc_page"):
        return run_doc_page(ctx, payload["doc_page"])
    if payload.get("uk_class"):
        return run_uk(ctx, payload["uk_class"])
    if payload.get("ledger"):
        return run_ledger(ctx, payload["ledger"])
    if payload.get("tables"):
        return run_tables(ctx, payload["tables"])
    if payload.get("links"):
        return run_links(ctx, payload["links"])
    if payload.get("columns"):
        return run_columns(ctx, payload["columns"])
    if payload.get("numbered"):
        return run_numbered(ctx, payload["numbered"])
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
