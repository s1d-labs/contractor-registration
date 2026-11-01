"""Put this family's projects in the pool and register its health checks. Run by the Setup workflow (GitHub Actions: the hub
trusts this repo, s1d-labs/<family>, through its OIDC token), by hand and every day. Safe to run again: queue items that exist
are kept, new keys (the day's / week's refresh items, new OCR batches) are added, and items that used up their retries get
another go."""
from scrape_hub_client import register_project, seed_queue, set_pool, set_probes

from family import FAMILY, PROBES, PROJECTS

print("health checks:", set_probes(FAMILY, PROBES))
for p in PROJECTS:
    register_project(p["name"], title=p["title"], unit_label=p["unit_label"], record_label=p["record_label"],
                     expected_units=len(p["items"]), expected_records=sum(i["payload"].get("expected", 0) for i in p["items"]))
    set_pool(p["name"], FAMILY, p["task"], target=p["target"], env=p["env"], probe=p.get("probe", ""), max_workers=p.get("max_workers"),
             proxy=p.get("proxy", ""), geo=p.get("geo", ""))
    print(p["name"], "queue:", seed_queue(p["name"], p["items"], reset_failed=True))
