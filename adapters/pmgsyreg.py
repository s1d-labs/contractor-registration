"""PMGSY road register (pmgsy.dord.gov.in, OMMAS citizen reports): every rural road of the core network, every completed road
with its value of work done and completion date, and every road's maintenance (DLP) cost and expenditure per year.

The reports are SSRS reports behind the same ASP.NET MVC pages as adapters/pmgsy.py (form -> report POST -> report viewer -> CSV
export). Their road lists are not at the top level: the reader clicks a row (a "drill-through") to go one level down. A queue
item names the form (state, district) and a path of steps down to the road list:
  "first": click the first row (the level has one row, or every row opens the same list),
  "each": click every row in turn, each from a fresh viewer (a drill-through changes the viewer's state),
  "last": click the last row (the Total row, which opens the rows of every district at once).
Each road list (leaf) is exported as CSV, stored as it came (docs/<report>/...), and every row becomes a record with every
column of the export (the SSRS field names, lower case). Caption columns (the same text on every row) are left out of the
records; the stored CSV has them.

  corenetwork  "Road-wise Core Network" (CNRW): per district, every block -> the block's core network roads: road number
               (L031, T05: the DRRP / core network code), name, route (link / through), chainage, length, from, to, and the
               habitations it serves (one row per habitation). Payload {"report": "corenetwork", "state", "state_name",
               "district", "district_name"}.
  completed    "Completed Roads with Value of Work Done": per district (one list for the whole district): block, package,
               road name, sanction year, sanctioned cost, state cost, value of work done, payment made, completion month.
  maintenance  "Expenditure on DLP Maintenance" for one financial year: per state, the Total row -> every road of the state: block, year,
               package, road, connectivity, proposal type, sanctioned and completed length, stage, completion date,
               maintenance cost, in liability, the year's cost, the year's and total maintenance expenditure.
"""
import csv
import io
import re
import time

from adapters.common import sha1
from adapters.pmgsy import SITE, _viewer, drill_form

LEAF_TIMEOUT = 900
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DRILL = re.compile(r"Drillthrough','([^']+)'")


def _cnrw_fields(p):
    return {"Mast_State_Code": 0, "Mast_District_Code": 0, "Mast_Block_Code": 0, "StateName": p["state_name"],
            "DistName": p.get("district_name", "All Districts"), "BlockName": "All Blocks", "LevelCode": 1, "localizedValue": "en",
            "RouteName": "All", "StateCode": p["state"], "DistrictCode": p.get("district", 0), "BlockCode": 0, "Route": "0"}


def _completed_fields(p):
    return {"Mast_State_Code": 0, "Mast_District_Code": 0, "Mast_Block_Code": 0, "StateName": p["state_name"],
            "DistName": p.get("district_name", "All Districts"), "BlockName": "0", "CollaborationName": "All Collaborations",
            "LevelCode": 1, "localizedValue": "en", "StateCode": p["state"], "DistrictCode": p.get("district", 0), "Year": 0,
            "FundingAgency": 0}


def _maintenance_fields(p):
    return {"Mast_State_Code": 0, "StateName": p["state_name"], "BatchName": "", "Year": p["year"], "Scheme": 0,
            "StateCode": p["state"], "WorkType": 0, "WorkStage": 0, "MaintenanceLiability": 0}


REPORTS = {
    "corenetwork": {"layout": "/CoreNetworkArea/CoreNetwork/CNRWLayout", "report": "/CoreNetworkArea/CoreNetwork/CNRWReport/",
                    "fields": _cnrw_fields, "path": ["each"], "leaf": "RWCN_LVLReport",
                    "title": "Core Network: Road-wise Core Network"},
    "completed": {"layout": "/ProposalArea/Proposal/CompletedRoadValueLayout", "report": "/ProposalArea/Proposal/CompletedRoadValueReport/",
                  "fields": _completed_fields, "path": ["first", "first"], "leaf": "CompletedRoadsSubReport",
                  "title": "Proposals: Completed Roads with Value of Work Done"},
    "maintenance": {"layout": "/ProposalArea/Proposal/ExpHomePageLayout", "report": "/ProposalArea/Proposal/ExpReport/",
                    "fields": _maintenance_fields, "path": ["first", "last"], "leaf": "Blockwise_Maintenance_Details",
                    "title": "Expenditure on DLP Maintenance"},
}


def drill_ids(viewer_html):
    """The drill-through cells of a report page, in row order ("65iT0R0x2:0" is row 2). Pure."""
    ids = set(DRILL.findall(viewer_html or ""))
    row = lambda a: [int(n) for n in re.findall(r"\d+", a)]
    return sorted(ids, key=row)


def leaf_name(viewer_html):
    m = re.search(r'"ExportUrlBase":"[^"]*?FileName=([^&"\\]+)', viewer_html or "")
    return m.group(1) if m else None


def parse_leaf(csv_text):
    """The detail rows of an SSRS CSV export as dicts {field name (lower case): value}. The export has a few sections, each a
    row of field names and then its rows; the detail section is the one with the most rows. Fields that only repeat a caption
    or a total (the same value on every row, and named TextboxN) are left out. Pure."""
    rows = list(csv.reader(io.StringIO(csv_text.lstrip("﻿"))))
    best, i = [], 0
    while i < len(rows):
        head = rows[i]
        if head and all(IDENT.match(c or "") for c in head):
            body = []
            j = i + 1
            while j < len(rows) and len(rows[j]) == len(head) and not all(IDENT.match(c or "") for c in rows[j]):
                body.append(rows[j])
                j += 1
            if body and (not best or len(body) > len(best[1])):
                best = (head, body)
            i = j
        else:
            i += 1
    if not best or not best[1]:
        return []
    head, body = best
    keep = [k for k, h in enumerate(head)
            if not h.startswith("Textbox") or len(body) == 1 or len({r[k] for r in body}) > 1]
    keep = [k for k in keep if not (head[k].startswith("Textbox") and len(body) > 1 and _is_caption(body, k))]
    return [{head[k].lower(): r[k].strip() for k in keep} for r in body]


def heading(csv_text):
    """The report's title line (first section's values), e.g. "State: Sikkim  District: East  Block: Khamdung  Route: All". Pure."""
    rows = list(csv.reader(io.StringIO(csv_text.lstrip("\ufeff"))))
    return re.sub(r"\s+", " ", " | ".join(rows[1])).strip() if len(rows) > 1 else ""


def heading_block(head):
    m = re.search(r"Block\s*:\s*(.*?)\s+(?:Route|Collaboration)\s*:", head or "")
    return m.group(1).strip() if m else None


def _is_caption(body, k):
    """A Textbox column whose value is the same caption text on most rows (an SSRS label), not data."""
    vals = [r[k] for r in body]
    top = max(set(vals), key=vals.count)
    return vals.count(top) == len(vals) and not re.match(r"^[\d.,\s-]*$", top)


def _post_drill(ctx, viewer, action):
    url, form = drill_form(viewer or "", action)
    if not url:
        return None
    r = ctx.request("POST", url, data=form, timeout=LEAF_TIMEOUT)
    return r.text if r is not None else None


def _viewer_at(ctx, spec, payload, prefix):
    v = _viewer(ctx, SITE + spec["layout"], SITE + spec["report"], spec["fields"](payload))
    for a in prefix:
        if v is None:
            return None
        v = _post_drill(ctx, v, a)
    return v


def walk(ctx, spec, payload):
    """[(prefix, leaf viewer html)] for every leaf the item's path reaches; None when the site does not answer."""
    leaves = []
    path = spec["path"]

    def go(prefix, v, depth):
        if depth == len(path):
            leaves.append((prefix, v))
            return True
        ids = drill_ids(v)
        if not ids:
            return True                                   # nothing below (a district without roads)
        if path[depth] == "first":
            ids = ids[:1]
        elif path[depth] == "last":                       # the Total row: every row of the level at once
            ids = ids[-1:]
        for n, a in enumerate(ids):
            vv = v if n == 0 else _viewer_at(ctx, spec, payload, prefix)
            nxt = _post_drill(ctx, vv, a) if vv is not None else None
            if nxt is None or not go(prefix + [a], nxt, depth + 1):
                return False
        return True

    top = _viewer(ctx, SITE + spec["layout"], SITE + spec["report"], spec["fields"](payload))
    if top is None or not go([], top, 0):
        return None
    return leaves


def start_session(ctx):
    """The citizen page sets the session's cookies (scheme, state); without them the report viewer leaves out its
    drill-through links. Once per session."""
    if "globalPMGSYScheme" not in ctx.session.cookies.keys():
        return ctx.request("GET", SITE + "/Home/CitizenPage", timeout=60) is not None
    return True


def run(ctx, payload):
    kind = payload["report"]
    if not start_session(ctx):
        return None
    spec = REPORTS[kind]
    code = int(payload["state"])
    leaves = walk(ctx, spec, payload)
    if leaves is None:
        return None
    day = time.strftime("%Y%m%d")
    where = "-".join(str(x) for x in (f"{code:02d}", payload.get("district"), payload.get("year")) if x not in (None, ""))
    n = 0
    for k, (prefix, v) in enumerate(leaves):
        name = leaf_name(v)
        if name != spec["leaf"]:
            raise ValueError(f"{kind}: reached report {name}, expected {spec['leaf']} (path {prefix})")
        exp_url = SITE + re.search(r'"ExportUrlBase":"([^"]+)"', v).group(1).replace("\\u0026", "&") + "CSV"
        exp = ctx.request("GET", exp_url, timeout=LEAF_TIMEOUT)
        if exp is None:
            return None
        text = exp.content.decode("utf-8-sig", "replace")
        rows, head = parse_leaf(text), heading(text)
        stored = ctx.hub.upload_many([(f"docs/{kind}/{where}-{k:03d}-{day}.csv", exp.content, "text/csv")])[0]
        base = {"kind": f"pmgsy_{kind}", "state_code": code, "state": payload["state_name"],
                **({"district_code": payload["district"], "district": payload.get("district_name")} if payload.get("district") else {}),
                **({"year": payload["year"]} if payload.get("year") else {}),
                **({"block": heading_block(head)} if kind == "corenetwork" else {}),
                "report_heading": head, "source": f"{SITE}/Home/CitizenPage ({spec['title']})", "csv_path": stored.get("path")}
        for r in rows:
            ident = [f"{a}={b}" for a, b in sorted(r.items()) if not a.startswith("textbox")]   # not the row number
            rid = f"{kind}-{code:02d}-{sha1(str(payload.get('year', '')), *ident)[:16]}"
            ctx.record(rid, {**base, **r})
        n += len(rows)
    return n
