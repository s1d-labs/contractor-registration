"""Text for scanned PDFs: pypdfium2 renders each page at 200 dpi, tesseract (English + Hindi) reads it, one tesseract per CPU.

Used two ways:
- inline: Ctx.download reads a scan as it stores it when the project's env has OCR=1 (documents the refresh items bring in);
- as the `ocr` adapter (project contractor-registration-ocr) for the scans stored before that. Queue item payload:
    {"source": "<project>", "files": [{"path": "ocr-needed/...pdf", "pages": 3, "records": ["tender-1"], "url": "https://..."}]}
  Each file is read back from the bucket (hub.read_urls; its `url` on the site only if the bucket has no copy). Its text is stored
  at <source>/<path>.txt in this project's folder, and one record per file (`<source>-<hash>`) carries the text.
"""
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from adapters.common import RECORD_TEXT, sha1

LANGS = ("eng", "hin")
DPI = 200
MAX_SIDE = 5000          # pixels: large drawings are rendered smaller rather than at 200 dpi
MAX_PAGES = 300          # pages read per document
_lang = None


def tesseract_langs():
    try:
        out = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    return {line.strip() for line in out.splitlines()[1:] if line.strip()}


def ensure_tesseract():
    """The tesseract language string to use ("eng+hin"), installing tesseract with apt where sudo needs no password (GitHub
    runners); "" when there is no tesseract (e.g. on the India pool servers, which have no sudo)."""
    global _lang
    if _lang is None:
        have = tesseract_langs()
        if not set(LANGS) <= have and shutil.which("sudo") and shutil.which("apt-get"):
            env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
            for cmd in (["sudo", "-n", "apt-get", "update", "-qq"],
                        ["sudo", "-n", "apt-get", "install", "-y", "-qq", "tesseract-ocr", "tesseract-ocr-eng", "tesseract-ocr-hin"]):
                try:
                    subprocess.run(cmd, capture_output=True, timeout=600, env=env)
                except (OSError, subprocess.SubprocessError):
                    break
            have = tesseract_langs()
        _lang = "+".join(lang for lang in LANGS if lang in have)
    return _lang


def _read(png, lang):
    try:
        r = subprocess.run(["tesseract", str(png), "stdout", "-l", lang, "--psm", "1"], capture_output=True, timeout=300,
                           env={**os.environ, "OMP_THREAD_LIMIT": "1"})
        return r.stdout.decode("utf-8", "replace").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def ocr_pdf(data, max_pages=MAX_PAGES, lang=None):
    """(text, pages, pages_read) of a scanned PDF, pages separated by a form feed; ("", 0, 0) if it cannot be read."""
    lang = lang or ensure_tesseract()
    if not lang:
        return "", 0, 0
    import pypdfium2 as pdfium
    try:
        doc = pdfium.PdfDocument(data)
    except Exception:
        return "", 0, 0
    pages = len(doc)
    n = min(pages, max_pages)
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor(os.cpu_count() or 2) as pool:
        jobs = []
        for i in range(n):                       # rendering stays on this thread (pdfium is not thread-safe); reading runs in parallel
            try:
                page = doc[i]
                w, h = page.get_size()
                png = Path(tmp) / f"{i:04d}.png"
                page.render(scale=min(DPI / 72, MAX_SIDE / max(w, h, 1)), grayscale=True).to_pil().save(png)
                jobs.append(pool.submit(_read, png, lang))
            except Exception:
                jobs.append(None)
        texts = [j.result() if j else "" for j in jobs]
    doc.close()
    return "\f".join(texts), pages, n


def record_id(source, path):
    return f"{source.removeprefix('contractor-registration-')}-{sha1(source, path)[:16]}"


def run(ctx, payload):
    src, files = payload["source"], payload["files"]
    lang = ensure_tesseract()
    if not lang:
        raise RuntimeError("tesseract is not available on this runner")
    keys = [f"{src}/{f['path']}" for f in files]
    links = ctx.read_links(src, keys)
    n = 0
    for f, key in zip(files, keys):
        data = ctx.fetch_stored(links.get(key))
        if data is None and f.get("url"):
            r = ctx.request("GET", f["url"], timeout=120)
            data = r.content if r is not None else None
        if not data or data[:5] != b"%PDF-":
            ctx.hub.failure("ocr", key[:200], "the stored file could not be read")
            continue
        text, pages, read = ocr_pdf(data, lang=lang)
        out = f"{src}/{f['path']}.txt"
        if text.strip():
            ctx.hub.upload_many([(out, text.encode("utf-8"), "text/plain")])
        ctx.record(record_id(src, f["path"]), {
            "kind": "ocr", "source_project": src, "path": f["path"], "records": f.get("records", []), "url": f.get("url"),
            "pages": pages, "pages_read": read, "lang": lang, "text_path": out if text.strip() else None, "text_chars": len(text),
            "text": text[:RECORD_TEXT]})
        n += 1
    return n
