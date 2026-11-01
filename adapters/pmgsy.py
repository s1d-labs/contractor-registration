"""PMGSY / OMMAS (pmgsy.dord.gov.in, the citizen reports of OMMAS): the contractor master of rural road works, per state.

The public report "Contractor Information" (Proposals menu) is an SSRS report behind an ASP.NET MVC page. One state and one
contractor status (A active, I inactive, B blacklisted, E expired) take four requests: the form (cookie + anti-forgery token),
the report POST (answers an iframe address), the report viewer (carries the export address), the CSV export. The site answers
Indian addresses only, so the project borrows one of the hub's Indian proxies (proxy="IN").

Queue item payload: {"state": 33, "state_name": "Uttar Pradesh", "status": "A"}
One record per contractor (company, contact person, registration number, address, phones, e-mail, PAN as the site shows it:
first five and last character); the CSV is stored too, as docs/contractor-information/<state>-<status>-<date>.csv.
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


def run(ctx, payload):
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
