"""Build the queue files family.py seeds from what the pool has already stored. Run on a team box (it reads scrape_hub), then commit
queues/ and run the setup workflow:

    python tools/build_queues.py            # psql connection from the environment (PGHOST etc.), default dbname scrape_hub

queues/ocr.json.gz        OCR queue items: every stored scan (needs_ocr) not yet read by the contractor-registration-ocr project,
                          in batches of about PAGES pages. State lists' files are checked again here with common.needs_ocr, so
                          PDFs stored before 4 Nov 2026 with an unreadable text layer (Tripura certificates) count as scans. Keys hash their files, so building again only adds the new batches.
queues/morth_known.txt.gz MoRTH record ids collected so far: the weekly MoRTH refresh items skip them.
queues/nhai_refetch.json.gz NHAI archive documents stored empty in the first pass (2,789 on 2 Nov 2026), DOCS a queue item.
"""
import gzip
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from adapters.common import needs_ocr, sha1  # noqa: E402
from adapters.ocr import MAX_PAGES, record_id  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "queues"
PAGES, FILES = 250, 60
DOCS = 50
F = "contractor-registration"

SCANS = f"""
with s as (
  select r.project, r.record_id, d->'stored' s from public.records r,
         jsonb_array_elements(case when jsonb_typeof(r.data->'documents') = 'array' then r.data->'documents' else '[]' end) d
   where r.project in ('{F}-nhai-tenders', '{F}-nhai-tender-archive') and (d->'stored'->>'needs_ocr')::bool
  union all
  select project, record_id, data->'file' from public.records
   where project in ('{F}-morth-documents', '{F}-nhai-pages', '{F}-mes-works') and (data->'file'->>'needs_ocr')::bool
  union all
  select r.project, r.record_id, f from public.records r,
         jsonb_array_elements(case when jsonb_typeof(r.data->'files') = 'array' then r.data->'files' else '[]' end) f
   where r.project in ('{F}-nhai-pages', '{F}-mes-works') and (f->>'needs_ocr')::bool
)
select json_build_object('project', project, 'path', s->>'path', 'pages', max((s->>'pages')::int),
                         'records', (array_agg(distinct record_id))[1:5], 'ocr', bool_or((s->>'ocr')::bool))
from s where s->>'path' is not null group by project, s->>'path' order by project, s->>'path'
"""

STATE_FILES = f"""
with s as (
  select project, record_id, coalesce(data->'file', data->'certificate') s from public.records
   where project like '{F}-state-pwd%' and coalesce(data->'file', data->'certificate') is not null
)
select json_build_object('project', project, 'path', s->>'path', 'pages', max((s->>'pages')::int),
                         'records', (array_agg(distinct record_id))[1:5], 'ocr', bool_or((s->>'ocr')::bool),
                         'needs_ocr', bool_or((s->>'needs_ocr')::bool), 'text', max(s->>'text'))
from s where s->>'path' like '%.pdf' group by project, s->>'path' order by project, s->>'path'
"""

EMPTY = f"""
select json_build_object('endpoint', r.data->>'endpoint', 'tender', r.data->>'id', 'url', d->>'url')
from public.records r, jsonb_array_elements(r.data->'documents') d
where r.project = '{F}-nhai-tender-archive' and (d->'stored'->>'bytes')::int < 100
order by r.data->>'endpoint', r.record_id, d->>'url'
"""


def psql(sql):
    out = subprocess.run(["psql", os.environ.get("PGDATABASE", "scrape_hub"), "-AtX", "-c", sql], capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line]


def batches(files):
    """Groups of files of about PAGES pages (at most FILES files), per source project."""
    out, cur, pages = [], [], 0
    for f in files:
        p = min(f.get("pages") or 1, MAX_PAGES)
        if cur and (pages + p > PAGES or len(cur) >= FILES or cur[0]["project"] != f["project"]):
            out.append(cur)
            cur, pages = [], 0
        cur.append(f)
        pages += p
    return out + ([cur] if cur else [])


def main():
    OUT.mkdir(exist_ok=True)
    done = set(psql(f"select record_id from public.records where project = '{F}-ocr'"))
    scans = [json.loads(line) for line in psql(SCANS)]
    for f in map(json.loads, psql(STATE_FILES)):
        if f.pop("needs_ocr") or needs_ocr(f.pop("text") or "", f["pages"] or 0):
            f.pop("text", None)
            scans.append(f)
    todo = [s for s in scans if not s["ocr"] and record_id(s["project"], s["path"]) not in done]
    old = OUT / "ocr.json.gz"
    items = json.loads(gzip.decompress(old.read_bytes())) if old.exists() else []
    keys = {i["key"] for i in items}
    queued = {(i["payload"]["source"], f["path"]) for i in items for f in i["payload"]["files"]}
    todo = [s for s in todo if (s["project"], s["path"]) not in queued]
    for b in batches(todo):
        src = b[0]["project"]
        key = f"{src.removeprefix(F + '-')}-{sha1(*(f['path'] for f in b))[:12]}"
        if key not in keys:
            items.append({"key": key, "payload": {"source": src, "expected": len(b),
                                                  "files": [{"path": f["path"], "pages": f["pages"], "records": f["records"]} for f in b]}})
            keys.add(key)
    old.write_bytes(gzip.compress(json.dumps(items, separators=(",", ":")).encode(), mtime=0))
    known = sorted(psql(f"select record_id from public.records where project = '{F}-morth-documents'"))
    (OUT / "morth_known.txt.gz").write_bytes(gzip.compress(("\n".join(known) + "\n").encode(), mtime=0))
    fetched = set(psql(f"select record_id from public.records where project = '{F}-nhai-tender-archive' and record_id like 'refetch-%'"))
    empty = [e for e in map(json.loads, psql(EMPTY)) if f"refetch-{sha1(e['url'])[:16]}" not in fetched]
    refetch = []
    for ep in sorted({e["endpoint"] for e in empty}):
        docs = [{"tender": e["tender"], "url": e["url"]} for e in empty if e["endpoint"] == ep]
        for k in range(0, len(docs), DOCS):
            part = docs[k:k + DOCS]
            refetch.append({"key": f"refetch-{ep}-{sha1(*(d['url'] for d in part))[:12]}",
                            "payload": {"kind": "refetch", "section": f"tenders-archive/{ep}", "documents": part, "expected": len(part)}})
    (OUT / "nhai_refetch.json.gz").write_bytes(gzip.compress(json.dumps(refetch, separators=(",", ":")).encode(), mtime=0))
    print(f"nhai refetch: {len(empty)} documents in {len(refetch)} items")
    pages = sum(min(f["pages"] or 1, MAX_PAGES) for i in items for f in i["payload"]["files"])
    print(f"scans {len(scans)}, already read {len(scans) - len(todo)}; ocr items {len(items)} "
          f"({sum(len(i['payload']['files']) for i in items)} files, {pages} pages); morth known {len(known)}")


if __name__ == "__main__":
    main()
