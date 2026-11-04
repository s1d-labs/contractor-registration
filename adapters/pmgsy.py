"""PMGSY / OMMAS (pmgsy.dord.gov.in, the citizen reports of OMMAS): the contractor master of rural road works, and the works
awarded, per state.

The public report "Contractor Information" (Proposals menu) is an SSRS report behind an ASP.NET MVC page. One state and one
contractor status (A active, I inactive, B blacklisted, E expired) take four requests: the form (cookie + anti-forgery token),
the report POST (answers an iframe address), the report viewer (carries the export address), the CSV export. The site answers
Indian addresses only, so the project borrows one of the hub's Indian proxies (proxy="IN").

Queue item payload: {"state": 33, "state_name": "Uttar Pradesh", "status": "A"}
One record per contractor (company, contact person, registration number, address, phones, e-mail, PAN as the site shows it:
first five and last character); the CSV is stored too, as docs/contractor-information/<state>-<status>-<date>.csv.

"Agreement Details" (Work Awarded menu) is a state summary per district; its Total row drills through to every work of the
state: the works awarded (package, road, sanction date, lengths, sanctioned cost, awarded cost) and the works awarded and then
terminated. A drill-through is a postback of the report viewer's form, then the CSV export of the report it opens.
The public reports do not name the contractor of a work (only the contractor master above lists contractors).
Queue item payload: {"report": "agreements", "state": 30, "state_name": "Sikkim"}

The dashboard's "KPI Based Contractors' Performance" (/dbweb) scores contractors out of 100: construction, mobilisation and
quality, each with its points, and the contractor's PAN in full. One JSON request per state.
Queue item payload: {"report": "kpi", "state": 30, "state_name": "Sikkim"}; one record per contractor (`kpi-<state>-<PAN>`).
One record per work (`<state>-awarded-<hash>`, `<state>-terminated-<hash>`); both CSVs are stored under docs/agreements/.
"""
import csv
import html
import io
import re
import time

from adapters.common import clean, sha1

SITE = "https://pmgsy.dord.gov.in"
LAYOUT = SITE + "/MasterArea/Master/ContractorInformationLayout"
REPORT = SITE + "/MasterArea/Master/ContractorInformationLayoutReport/"
AGREEMENTS_LAYOUT = SITE + "/WorkAwardedArea/WorkAwarded/TendAgrDetailsLayout"
AGREEMENTS_REPORT = SITE + "/WorkAwardedArea/WorkAwarded/TendAgrDetailsReport/"
# the cells of the summary's Total row that drill through to the state's works (report item ids), and the report each opens
DRILLS = {"awarded": ("249iT0:0", "Tend_Agr_Awarded"), "terminated": ("293iT0:0", "Tend_Agr_Work_Awarded_Terminated_Report")}
WORK_COLUMNS = {      # CSV export column -> record field (amounts in Rs lakh, as the site gives them)
    "MAST_STATE_NAME": "state", "MAST_DISTRICT_NAME": "district", "MAST_BLOCK_NAME": "block", "IMS_YEAR": "sanction_year",
    "SANCTION_YEAR": "sanction_date", "IMS_BATCH": "batch", "IMS_PACKAGE_ID": "package", "WORK_TYPE": "work_type",
    "WORK_NAME": "work_name", "AWARDED_ROAD_LENGTH": "road_length_km", "ROAD_LENGTH1": "road_length_km",
    "AWARED_BRIDGE_LENGTH": "bridge_length_m", "BRIDGE_LENGTH": "bridge_length_m",
    "SANCTION_PACKAGE_COST": "sanction_cost_lakh", "SANCTION_COST": "sanction_cost_lakh", "AGREEMENT_AMOUNT": "awarded_cost_lakh",
}
STATUS = {"A": "Active", "I": "Inactive", "B": "Blacklisted", "E": "Expired"}
ADDRESS = re.compile(r"^(.*?)\s*State\s*-\s*(.*?)\s*Pincode\s*-\s*([\d\s-]*)$", re.S)
CONTACT = re.compile(r"Phone1\s*-\s*(.*?)\s*Phone2\s*-\s*(.*?)\s*Fax\s*-\s*(.*?)\s*Email\s*-\s*(.*)$", re.S)
EMPTY = re.compile(r"^[\s0-]*$")


def token(layout_html):
    m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', layout_html or "")
    return m.group(1) if m else None


def iframe_src(report_html):
    m = re.search(r'<iframe[^>]+src="([^"]+)"', report_html or "", re.I)
    return SITE + html.unescape(m.group(1)) if m else None


def export_url(viewer_html, fmt="CSV"):
    m = re.search(r'"ExportUrlBase":"([^"]+)"', viewer_html or "")
    return SITE + m.group(1).replace("\\u0026", "&") + fmt if m else None


KPI = SITE + "/dbweb/Contractor/GetContractorData"


def parse_kpi(rows):
    """[{state, company, pan, construction, mobilization, quality, score}] from the dashboard's JSON. Pure."""
    num = lambda v: None if v is None else round(float(v), 2)
    return [{"state": clean(r.get("MAST_STATE_NAME")), "company": clean(r.get("COMPANY_NAME")), "pan": clean(r.get("PAN")),
             "construction": num(r.get("CONSTRUCTION")), "mobilization": num(r.get("MOBILIZATION")), "quality": num(r.get("QUALITY")),
             "score": num(r.get("SCORE"))} for r in rows or [] if isinstance(r, dict)]


def kpi(ctx, payload):
    code = int(payload["state"])
    js = ctx.get_json("POST", KPI, json={"StateID": str(code), "Company": "", "ScoreGreaterThan": None, "ScoreLessThan": None}, timeout=180)
    if js is None:
        return None
    rows = parse_kpi(js)
    for r in rows:
        ident = r["pan"] or sha1(r["company"].upper())[:12]
        ctx.record(f"kpi-{code:02d}-{ident}", {"kind": "contractor_kpi", "state_code": code, **r,
                                              "band": "satisfactory" if (r["score"] or 0) >= 75 else "average" if (r["score"] or 0) >= 55 else "unsatisfactory",
                                              "source": f"{SITE}/dbweb/ (KPI Based Contractors' Performance)"})
    return len(rows)


def report_form(page_html):
    """(action url, fields) of the report viewer's form: every hidden field, as a browser would post it back."""
    m = re.search(r'<form[^>]*action="\./([^"]+)"', page_html or "")
    if not m:
        return None, {}
    fields = {}
    for tag in re.findall(r"<input[^>]*type=\"hidden\"[^>]*>", page_html):
        n, v = re.search(r'name="([^"]+)"', tag), re.search(r'value="([^"]*)"', tag)
        if n:
            fields[n.group(1)] = html.unescape(v.group(1)) if v else ""
    return SITE + "/" + html.unescape(m.group(1)), fields


def drill_form(viewer_html, action):
    """The postback that clicks a drill-through cell (`InvokeReportAction('Drillthrough', action)` in the page). Pure."""
    url, fields = report_form(viewer_html)
    if not url or f"'Drillthrough','{action}'" not in viewer_html:
        return None, {}
    return url, {**fields, "__EVENTTARGET": "ReportViewer$ctl03", "__EVENTARGUMENT": "",
                 "ReportViewer$ctl03$ctl00": "Drillthrough", "ReportViewer$ctl03$ctl01": action,
                 "ReportViewer$ctl09$ReportControl$ctl02": "Drillthrough", "ReportViewer$ctl09$ReportControl$ctl03": action}


def parse_works(csv_text):
    """[{state, district, block, sanction_year, sanction_date?, batch, package, work_type, work_name, road_length_km,
    bridge_length_m, sanction_cost_lakh, awarded_cost_lakh?}] from a works report's CSV export; the trailing total columns
    are dropped. Pure."""
    rows = list(csv.reader(io.StringIO(csv_text.lstrip("\ufeff"))))
    if not rows:
        return []
    head, out = rows[0], []
    for r in rows[1:]:
        if len(r) != len(head) or not r[1].strip().isdigit():
            continue
        w = {WORK_COLUMNS[h]: _value(v) for h, v in zip(head, r) if h in WORK_COLUMNS}
        for k in ("road_length_km", "bridge_length_m", "sanction_cost_lakh", "awarded_cost_lakh"):
            if k in w:
                w[k] = w[k].replace(",", "")
        out.append({"sr": r[1], **w})
    return out


def mark_package_totals(works):
    """Some states give each work its own awarded cost; others repeat the package's agreement amount on every work of the
    package (Chhattisgarh CG1639: 5,111.40 lakh on its 5 roads). `awarded_is_package_total` marks the second case, so a sum
    takes that amount once per package. Pure."""
    by = {}
    for w in works:
        by.setdefault(w.get("package"), []).append(w)
    for pk in by.values():
        amounts = {w.get("awarded_cost_lakh") for w in pk}
        repeated = len(pk) > 1 and len(amounts) == 1 and "" not in amounts and len({w.get("sanction_cost_lakh") for w in pk}) > 1
        for w in pk:
            if "awarded_cost_lakh" in w:
                w["awarded_is_package_total"] = repeated
    return works


def work_id(state_code, kind, w):
    """A package can hold two bridges of the same name (Sikkim SK03P7P11R): the cost and lengths tell them apart."""
    return f"{state_code}-{kind}-{sha1(w['package'], w['work_name'], w['work_type'], w['sanction_year'], w['block'], w['sanction_cost_lakh'], w.get('road_length_km', ''), w.get('bridge_length_m', ''))[:14]}"


def _value(s):
    s = clean(html.unescape(s or ""))
    return "" if EMPTY.match(s) else s


def parse_contractors(csv_text):
    """[{company, contact_person, registration_no, address, pincode, phone1, phone2, fax, email, pan, state, sr}] from the CSV
    export. Every data row repeats the column captions first; rows without them are the report's title lines. Pure."""
    out = []
    for r in csv.reader(io.StringIO(csv_text.lstrip("﻿"))):
        if len(r) != 16 or r[0] != "Sr.No.":
            continue
        sr, state, company, person, reg, addr, contact, pan = r[8:16]
        a = ADDRESS.match(clean(addr))
        c = CONTACT.match(clean(contact))
        pin = re.sub(r"\D", "", a.group(3)) if a else ""
        out.append({"sr": sr, "state": clean(state), "company": _value(company), "contact_person": _value(person),
                    "registration_no": _value(reg), "address": _value(a.group(1) if a else addr), "pincode": pin if pin.strip("0") else "",
                    **dict(zip(("phone1", "phone2", "fax", "email"), (_value(x) for x in (c.groups() if c else ("", "", "", ""))))),
                    "pan": _value(pan)})
    return out


def contractor_id(state_code, row):
    return f"{state_code}-{sha1(row['company'].upper(), row['registration_no'].upper(), row['contact_person'].upper(), row['pan'])[:14]}"


def _viewer(ctx, layout_url, report_url, fields):
    """The report viewer page of one report: form (token), report POST (iframe address), viewer."""
    layout = ctx.request("GET", layout_url, timeout=60, headers={"X-Requested-With": "XMLHttpRequest"})
    tok = token(layout.text if layout is not None else "")
    if not tok:
        return None
    rep = ctx.request("POST", report_url, timeout=300, headers={"X-Requested-With": "XMLHttpRequest", "Referer": SITE + "/Home/CitizenPage"},
                      data={"__RequestVerificationToken": tok, **fields})
    src = iframe_src(rep.text if rep is not None else "")
    viewer = ctx.request("GET", src, timeout=600) if src else None
    return viewer.text if viewer is not None else None


def agreements(ctx, payload):
    code, name = int(payload["state"]), payload["state_name"]
    fields = {"Mast_State_Code": 0, "Mast_District_Code": 0, "Mast_Block_Code": 0, "StateName": name, "DistName": "All Districts",
              "BlockName": 0, "LevelCode": 1, "localizedValue": "en", "PMGSYScheme": "", "PropType": "", "StateCode": code,
              "DistrictCode": 0, "ProposalType": "%", "Year": 0, "Batch": 0, "Scheme": 0}
    n = 0
    for kind, (action, report) in DRILLS.items():
        viewer = _viewer(ctx, AGREEMENTS_LAYOUT, AGREEMENTS_REPORT, fields)   # a fresh viewer each time: a drill-through stacks
        url, form = drill_form(viewer or "", action)
        if not url:
            return None if viewer is None else n          # a state with no works has no Total row to drill into
        page = ctx.request("POST", url, data=form, timeout=900)
        exp_url = export_url(page.text if page is not None else "")
        if not exp_url or f"FileName={report}&" not in exp_url:
            return None
        exp = ctx.request("GET", exp_url, timeout=900)
        if exp is None:
            return None
        works = mark_package_totals(parse_works(exp.content.decode("utf-8-sig", "replace")))
        stored = ctx.hub.upload_many([(f"docs/agreements/{code:02d}-{kind}-{time.strftime('%Y%m%d')}.csv", exp.content, "text/csv")])[0]
        for w in works:
            ctx.record(work_id(code, kind, w), {"kind": f"pmgsy_work_{kind}", "state_code": code, **w,
                                                "source": f"{SITE}/Home/CitizenPage (Work Awarded: Agreement Details)",
                                                "csv_path": stored.get("path")})
        n += len(works)
    return n


def run(ctx, payload):
    if payload.get("report") == "agreements":
        return agreements(ctx, payload)
    if payload.get("report") == "kpi":
        return kpi(ctx, payload)
    code, status = int(payload["state"]), payload.get("status", "A")
    name = payload["state_name"]
    layout = ctx.request("GET", LAYOUT, timeout=60)
    tok = token(layout.text if layout is not None else "")
    if not tok:
        return None
    rep = ctx.request("POST", REPORT, timeout=120, headers={"X-Requested-With": "XMLHttpRequest", "Referer": SITE + "/Home/CitizenPage"},
                      data={"__RequestVerificationToken": tok, "Mast_State_Code": 0, "Mast_District_Code": 0, "Mast_Block_Code": 0,
                            "StateName": name, "DistName": 0, "BlockName": 0, "Active": "%", "Code": 0,
                            "RegistrationStatusName": "All", "ContractorStatusName": STATUS.get(status, "All"), "localizedValue": "en",
                            "StateCode": code, "RegisterStatus": "%", "ContratorStatus": status})
    src = iframe_src(rep.text if rep is not None else "")
    viewer = ctx.request("GET", src, timeout=300) if src else None
    url = export_url(viewer.text if viewer is not None else "")
    exp = ctx.request("GET", url, timeout=300) if url else None
    if exp is None:
        return None
    text = exp.content.decode("utf-8-sig", "replace")
    rows = parse_contractors(text)
    stored = ctx.hub.upload_many([(f"docs/contractor-information/{code:02d}-{status}-{time.strftime('%Y%m%d')}.csv",
                                   exp.content, "text/csv")])[0]
    for row in rows:
        ctx.record(contractor_id(code, row), {"kind": "contractor", "state_code": code, **row, "contractor_status": STATUS.get(status, status),
                                              "source": f"{SITE}/Home/CitizenPage (Proposals: Contractor Information)",
                                              "csv_path": stored.get("path")})
    return len(rows)
