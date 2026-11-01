"""Build the queue files family.py seeds from what the pool has already stored. Run on a team box (it reads scrape_hub), then commit
queues/ and run the setup workflow:

    python tools/build_queues.py            # psql connection from the environment (PGHOST etc.), default dbname scrape_hub

queues/ocr.json.gz        OCR queue items: every stored scan (needs_ocr) not yet read by the contractor-registration-ocr project,
                          in batches of about PAGES pages. Keys hash their files, so building again only adds the new batches.
queues/morth_known.txt.gz MoRTH record ids collected so far: the weekly MoRTH refresh items skip them.
"""
import gzip
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from adapters.common import sha1  # noqa: E402
from adapters.ocr import MAX_PAGES, record_id  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "queues"
PAGES, FILES = 250, 60
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
    pages = sum(min(f["pages"] or 1, MAX_PAGES) for i in items for f in i["payload"]["files"])
    print(f"scans {len(scans)}, already read {len(scans) - len(todo)}; ocr items {len(items)} "
          f"({sum(len(i['payload']['files']) for i in items)} files, {pages} pages); morth known {len(known)}")


if __name__ == "__main__":
    main()
