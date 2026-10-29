"""Pieces every site adapter shares: polite requests with the hub's counters, file storage, PDF text, a stand-in hub for --local.

Public data only. Nothing here logs in, solves a captcha or works around a block: a page that needs a login or answers 403 is
reported with hub.failure() and skipped.
"""
import hashlib
import io
import json
import logging
import os
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

UA = "s1d-labs scraper (https://github.com/s1d-labs)"
RECORD_TEXT = 20_000            # characters of PDF text kept in the record; the whole text is stored next to the PDF as .txt
MAX_PDF_PAGES = 400             # pages read for text; the PDF itself is stored whole
MAX_FILE_BYTES = 80 * 1024 * 1024
DOC_EXT = {"pdf", "doc", "docx", "xls", "xlsx", "xlsm", "csv", "ppt", "pptx", "zip", "rar", "odt", "ods", "txt", "rtf"}
SIZE = re.compile(r"\(\s*([\d.,]+\s*[KMG]?B)\s*\)", re.I)
logging.getLogger("pypdf").setLevel(logging.ERROR)    # font-encoding warnings on government PDFs, not errors


def sha1(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def no_nul(x):
    """x with NUL characters removed from every string: Postgres cannot store \\u0000 in JSON, and the hub refuses the whole batch."""
    if isinstance(x, str):
        return x.replace("\x00", "")
    if isinstance(x, dict):
        return {no_nul(k): no_nul(v) for k, v in x.items()}
    if isinstance(x, list):
        return [no_nul(v) for v in x]
    return x


def safe_name(name, limit=90):
    """File name restricted to the characters the hub accepts in upload paths ([A-Za-z0-9._-])."""
    name = unquote(name)
    stem, dot, ext = name.rpartition(".")
    if not dot or len(ext) > 5:
        stem, ext = name, ""
    stem = re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9._-]+", "_", stem)).strip("._-")[:limit] or "file"
    ext = re.sub(r"[^A-Za-z0-9]", "", ext).lower()
    return f"{stem}.{ext}" if ext else stem


def url_ext(url):
    ext = urlparse(url).path.rsplit(".", 1)[-1].lower() if "." in urlparse(url).path else ""
    return ext if ext in DOC_EXT else ""


def pdf_text(data):
    """(text, pages) of a PDF; ('', 0) if it cannot be read. Pure apart from the pypdf import."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        pages = len(reader.pages)
        text = "\n".join((p.extract_text() or "") for p in reader.pages[:MAX_PDF_PAGES])
        return text, pages
    except Exception:
        return "", 0


def needs_ocr(text, pages):
    """A PDF whose pages carry (almost) no text layer is a scan: it goes under ocr-needed/ for a later OCR pass."""
    return pages > 0 and len(text.strip()) < 40 * min(pages, MAX_PDF_PAGES)


class LocalHub:
    """Stand-in for HubClient so `--local` runs without the hub: records go to stdout, files to ./data/<project>/, counters to stderr."""
    settings = {"threads": 1, "delay_ms": 0, "paused": False}

    def __init__(self, project="local"):
        self.project = project
        self.counts = {}

    def metric(self, name, value=1):
        self.counts[name] = self.counts.get(name, 0) + value

    def error(self, n=1):
        self.metric("errors", n)

    def block(self, n=1):
        self.metric("blocked", n)

    def failure(self, kind, key, reason, **detail):
        print(f"FAILURE {kind} {key[:120]}: {reason}", file=sys.stderr)

    def record(self, rid, data):
        print(json.dumps({"record_id": rid, "data": data}, ensure_ascii=False))

    def upload_many(self, files):
        out = []
        for path, content, _ctype in files:
            target = Path("data") / self.project / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            out.append({"path": path, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        return out


class TimeUp(Exception):
    """The run's time budget (SCRAPE_MAX_HOURS) is used up: the item is handed back unfinished and retried later."""


class Ctx:
    """What an adapter works with: requests (counted, spaced by the hub's delay), records, files."""

    def __init__(self, hub, session=None, project="", deadline=None):
        self.hub = hub
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = UA
        self.project = project
        self.last = 0.0
        self.deadline = deadline

    def pause_if_held(self):
        while self.hub.settings.get("paused"):
            time.sleep(30)

    def request(self, method, url, **kw):
        """Response for a 200 answer, else None (counted for the hub's throttle). Never retries in a tight loop."""
        self.pause_if_held()
        if self.deadline and time.time() > self.deadline:
            raise TimeUp("time budget used up")
        gap = max(0.5, self.hub.settings.get("delay_ms", 0) / 1000)
        time.sleep(max(0.0, self.last + gap - time.time()))
        t = time.time()
        try:
            r = self.session.request(method, url, timeout=kw.pop("timeout", 45), **kw)
        except requests.RequestException:
            self.last = time.time()
            self.hub.metric("http_error")
            self.hub.error()
            return None
        self.last = time.time()
        self.hub.metric("n_http")
        self.hub.metric("t_http_s", self.last - t)
        if r.status_code != 200:
            self.hub.metric(f"http_{r.status_code}")
            if r.status_code in (403, 429, 503):
                self.hub.block()
            return None
        return r

    def get_json(self, method, url, **kw):
        r = self.request(method, url, **kw)
        if r is None:
            return None
        try:
            return r.json()
        except ValueError:
            self.hub.error()
            return None

    def record(self, rid, data):
        self.hub.record(no_nul(rid), no_nul(data))

    def download(self, url, section, headers=None):
        """Fetch a document and store it. PDFs with no text layer go to ocr-needed/, other PDFs to pdf/, the rest to docs/.
        A PDF's whole text is stored beside it as <path>.txt. Returns {path, bytes, sha256, ext, pages, needs_ocr, text_path,
        text_chars, text (first RECORD_TEXT characters)} or None."""
        r = self.request("GET", url, headers=headers or {}, timeout=120)
        if r is None:
            self.hub.failure("download", url[:200], "document did not load")
            return None
        data = r.content
        if len(data) > MAX_FILE_BYTES:
            self.hub.failure("download", url[:200], f"file larger than {MAX_FILE_BYTES // 2**20} MB: not stored")
            return None
        ext = url_ext(url) or ("pdf" if data[:5] == b"%PDF-" else "bin")
        text, pages, ocr = "", 0, False
        if ext == "pdf" and data[:5] == b"%PDF-":
            text, pages = pdf_text(data)
            ocr = needs_ocr(text, pages)
            folder = "ocr-needed" if ocr else "pdf"
        else:
            folder = "docs"
        name = safe_name(Path(urlparse(url).path).name or "file")
        path = f"{folder}/{section}/{sha1(url)[:8]}-{name}"
        ctype = r.headers.get("Content-Type", "application/octet-stream").split(";")[0]
        files = [(path, data, ctype)]
        if text.strip():
            files.append((path + ".txt", text.encode("utf-8"), "text/plain"))
        stored = self.hub.upload_many(files)[0]
        return {"path": path, "bytes": stored.get("bytes", len(data)), "sha256": stored.get("sha256"), "ext": ext, "pages": pages,
                "needs_ocr": ocr, "text_path": path + ".txt" if len(files) > 1 else None, "text_chars": len(text),
                "text": text[:RECORD_TEXT]}


class PageWalker(HTMLParser):
    """Reads a CMS page body: headings, tables (cells + links per row) and every link.
    The anchors' text and the nearest heading above them come with them, which is the context a document list needs."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading, self._in_heading, self._buf = "", None, []
        self.tables, self._table, self._row, self._cell = [], None, None, None
        self.links, self._a = [], None
        self.text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._in_heading, self._buf = tag, []
        elif tag == "table":
            self._table = {"headers": [], "rows": []}
        elif tag == "tr" and self._table is not None:
            self._row = {"cells": [], "links": [], "th": False}
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
            self._row["th"] = self._row["th"] or tag == "th"
        elif tag == "a" and a.get("href"):
            self._a = {"href": a["href"].strip(), "text": [], "heading": self.heading}

    def handle_endtag(self, tag):
        if tag == self._in_heading:
            self.heading = clean("".join(self._buf))
            self._in_heading = None
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row["cells"].append(clean("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row["th"] and not self._table["headers"]:
                self._table["headers"] = self._row["cells"]
            elif any(self._row["cells"]):
                self._table["rows"].append({"cells": self._row["cells"], "links": self._row["links"]})
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None
        elif tag == "a" and self._a is not None:
            text = clean("".join(self._a["text"]))
            link = {"href": self._a["href"], "text": SIZE.sub("", text).strip(), "size": (SIZE.search(text) or [None, None])[1],
                    "heading": self._a["heading"]}
            self.links.append(link)
            if self._row is not None:
                self._row["links"].append(link)
            self._a = None

    def handle_data(self, data):
        if self._in_heading:
            self._buf.append(data)
        if self._cell is not None:
            self._cell.append(data)
        if self._a is not None:
            self._a["text"].append(data)
        self.text.append(data)


def walk_page(html_text):
    w = PageWalker()
    w.feed(html_text or "")
    return w
