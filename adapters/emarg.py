"""eMARG (emarg.gov.in): the PMGSY roads under performance-based maintenance, per state, district and block.

The public "Know Your Road" box on the home page fills four lists without a sign-in or a captcha: states, the state's
districts, the district's blocks, and the block's roads (eMARG road id and road name). These are JSON answers to POST
requests (public/getStateListForPublic.do, getDistrictListByState.do, getBlockListByDistrict.do,
getRoadListByDistrictAndBlockId.do). The road's details (length, package, contractor, maintenance start and end, expenditure)
open only after a captcha (getRoadDetailsByRoadIdInKnowYourRoad.do): this adapter does not ask for them.

Queue item payload: {"state": 7, "state_name": "Chhattisgarh"} (eMARG's own state id). One record per road
(`emarg-<roadDetailsId>`: road id, road name, state, district, block with their eMARG ids); every block's JSON answer is stored
as it came, docs/roads/<state>-<date>.json.gz (one file per state: {"districts": ..., "blocks": {district id: ...},
"roads": {block id: ...}}).
"""
import gzip
import json
import time

SITE = "https://emarg.gov.in"
HEADERS = {"X-Requested-With": "XMLHttpRequest", "Referer": SITE + "/application_main.htm"}


def first_list(js):
    """The answers are [[...]]: a list holding the list. Pure."""
    if isinstance(js, list) and js and isinstance(js[0], list):
        return js[0]
    return js if isinstance(js, list) else []


def road_record(road, state, district, block):
    """Every field the road list gives that has a value, plus where the road is. Pure."""
    kept = {k: v for k, v in road.items() if v not in (None, "", 0, 0.0, False) or k in ("roadDetailsId", "roadName")}
    return {"kind": "emarg_road", "road_details_id": road.get("roadDetailsId"), "road_name": (road.get("roadName") or "").strip(),
            "state_id": state["stateId"], "state": state["stateName"],
            "district_id": district["districtId"], "district": district["districtName"],
            "block_id": block["blockId"], "block": block["blockName"], "fields": kept,
            "source": f"{SITE}/application_main.htm (Know Your Road: road list)"}


def _post(ctx, path, data=None):
    return ctx.get_json("POST", f"{SITE}/public/{path}", data=data or {}, headers=HEADERS, timeout=120)


def run(ctx, payload):
    code = int(payload["state"])
    states = _post(ctx, "getStateListForPublic.do")
    if states is None:
        return None
    state = next((s for s in first_list(states) if s.get("stateId") == code), None)
    if state is None:
        return 0                                       # the state is not on eMARG
    raw = {"state": state, "districts": None, "blocks": {}, "roads": {}}
    districts = _post(ctx, "getDistrictListByState.do", {"stateId": state["encStateId"]})
    if districts is None:
        return None
    raw["districts"] = districts
    n = 0
    for d in first_list(districts):
        blocks = _post(ctx, "getBlockListByDistrict.do", {"districtId": d["encDistrictId"]})
        if blocks is None:
            return None
        raw["blocks"][str(d["districtId"])] = blocks
        for b in first_list(blocks):
            roads = _post(ctx, "getRoadListByDistrictAndBlockId.do", {"districtId": d["encDistrictId"], "blockId": b["encBlockId"]})
            if roads is None:
                return None
            raw["roads"][str(b["blockId"])] = roads
            for r in first_list(roads):
                if r.get("roadDetailsId"):
                    ctx.record(f"emarg-{r['roadDetailsId']}", road_record(r, state, d, b))
                    n += 1
    body = gzip.compress(json.dumps(raw, ensure_ascii=False).encode())
    ctx.hub.upload_many([(f"docs/roads/{code:02d}-{time.strftime('%Y%m%d')}.json.gz", body, "application/gzip")])
    return n
