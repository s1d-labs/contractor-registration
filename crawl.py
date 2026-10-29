"""The family's `crawl` task (see scrape.json): one worker loop, one adapter per site.

The project's pool entry sets ADAPTER (nhai | morth | ...); the adapter in adapters/<ADAPTER>.py turns one queue item into records
and stored documents. The pool worker runs this with the assignment's env and:
SCRAPE_POOL_PROJECT (which project), SCRAPE_JOB_INDEX / SCRAPE_TOTAL_JOBS (this worker's slice), SCRAPE_MAX_HOURS (time budget).

Try an adapter without the hub (records on stdout, documents under ./data/, counters on stderr):
    python crawl.py --local nhai '{"kind": "tenders", "endpoint": "tenderlist", "page": 0, "detail": false}'
The sites drop some foreign hosting addresses (the team box); there, set ALL_PROXY=socks5h://127.0.0.1:1080 NO_PROXY=127.0.0.1,localhost
(needs `pip install pysocks`). GitHub's runners reach them directly.
"""
import importlib
import json
import os
import sys
import time

from adapters.common import Ctx, LocalHub, TimeUp

PROJECT = os.environ.get("SCRAPE_POOL_PROJECT", "")
ADAPTER = os.environ.get("ADAPTER", "")
MAX_S = float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600
DEADLINE = time.time() + MAX_S - 120
ITEM_S = min(15 * 60, MAX_S / 4)   # an item can take ~15 minutes (50 tenders and their documents): none starts with less time left


def adapter(name):
    if not name:
        sys.exit("ADAPTER is not set: the project's pool entry (family.py env) names the adapter, e.g. ADAPTER=nhai")
    return importlib.import_module(f"adapters.{name}")


def local(name, payload):
    hub = LocalHub(f"local-{name}")
    n = adapter(name).run(Ctx(hub, project=hub.project), json.loads(payload))
    print(f"{n} records, counters {hub.counts}", file=sys.stderr)


def main():
    from scrape_hub_client import HubClient      # imported here so --local works without it
    run = adapter(ADAPTER).run
    hub = HubClient(PROJECT, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", "0")), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", "1")))
    ctx = Ctx(hub, project=PROJECT, deadline=DEADLINE)
    try:
        while time.time() < DEADLINE - ITEM_S:
            if hub.settings.get("paused"):
                time.sleep(30)                          # the hub holds us (site down, or the family owner paused it)
                continue
            items = hub.claim(1, steal=True, retry_failed=True)
            if not items:
                break                                   # nothing left for this project: exit, the worker asks the hub for more
            item = items[0]
            try:
                n = run(ctx, item["payload"])
            except TimeUp:                              # records sent so far are kept (upserts); the item goes back to the queue
                hub.complete([item["key"]], "failed", error="time budget used up before the item finished")
                break
            except Exception as e:                      # one bad item must not stop the worker; the hub retries it later
                hub.failure("item", item["key"][:200], f"{type(e).__name__}: {e}"[:300])
                hub.complete([item["key"]], "failed", error=f"{type(e).__name__}: {e}"[:200])
                continue
            if n is None:
                hub.complete([item["key"]], "failed", error="site did not answer")
            else:
                hub.complete([item["key"]], "done", fetched=n)
        hub.close()
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


if __name__ == "__main__":
    if sys.argv[1:2] == ["--local"]:
        local(sys.argv[2], sys.argv[3])
    else:
        main()
