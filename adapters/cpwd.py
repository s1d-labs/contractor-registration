"""CPWD (erp.cpwd.gov.in, the new CPWD portal on Liferay; cpwd.gov.in itself does not answer): the contractor lists.

Each list is a Liferay portlet that renders a server-side table, paged with `_<portlet>_cur` / `_<portlet>_delta` (at most 200):
  contractors  gov_in_cpwd_contractor_portlet           every enlisted contractor (~9,700): name, address, state, category,
                                                        class, enlistment / debarment / suspension dates and orders, status
  debarred     gov_in_cpwd_ed_contractors_portlet       CPWD-enlisted contractors debarred, with the order
  suspended    gov_in_cpwd_suspend_contractors_portlet  contractors suspended for violating the EMD declaration, with the order
The site answers Indian addresses only, so the project borrows one of the hub's Indian proxies (proxy="IN").

Queue item payload: {"list": "contractors", "cur": 1, "delta": 200, "files": false}
One record per row (`<list>-<site's contractor id>`, or a hash of the row where the list has no id), with the links of its orders.
The orders themselves (Liferay documents) answer with a CPWD sign-in page, so they are not fetched (files: false).
"""
import html
import re
from urllib.parse import urljoin

from adapters.common import clean, sha1

SITE = "https://erp.cpwd.gov.in"
LISTS = {
    "contractors": ("list-of-cpwd-enlisted-debarred-contractors", "gov_in_cpwd_contractor_portlet", "/contractor-view.jsp",
                    {"active": "true", "orderByType": "desc", "resetCur": "false"}),
    "debarred": ("list-of-cpwd-enlisted-debarred-contractors", "gov_in_cpwd_ed_contractors_portlet", "/edcontractors-view.jsp",
                 {"status": "-1", "orderByCol": "sequenceNo", "orderByType": "desc"}),
    "suspended": ("list-of-suspended-contractors-due-to-violation-of-emd-declaration", "gov_in_cpwd_suspend_contractors_portlet",
                  "/suspendcontractors-view.jsp", {"status": "-1", "orderByCol": "sequenceNo", "orderByType": "asc"}),
}
ROW_ID = re.compile(r"selected\w*Id='(\d+)'")
SKIP = {"", "actions", "s. no.", "s.no.", "uploaded by", "added on"}


def list_url(name, cur=1, delta=200):
    page, portlet, mvc, extra = LISTS[name]
    params = {"mvcPath": mvc, **extra, "cur": cur, "delta": delta}
    q = "&".join(f"_{portlet}_{k}={v}" for k, v in params.items())
    return f"{SITE}/web/cpwd/{page}?p_p_id={portlet}&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&{q}"


def _text(cell):
    return clean(html.unescape(re.sub(r"<!--.*?-->|<[^>]+>", " ", cell, flags=re.S)))


def portlet_section(page_html, portlet):
    """The part of the page that belongs to one portlet (a page can carry several lists)."""
    start = page_html.find(f'id="p_p_id_{portlet}_"')
    if start < 0:
        return ""
    end = page_html.find('id="p_p_id_', start + 10)
    return page_html[start:end if end > 0 else None]


def parse_rows(section):
    """[{"site_id", "columns": {header: text}, "files": {header: url}}] of the portlet's table. Pure."""
    tables = re.findall(r"<table.*?</table>", section, re.S)
    if not tables:
        return []
    rows = re.findall(r"<tr.*?</tr>", max(tables, key=len), re.S)
    heads, out = [], []
    for r in rows:
        cells = re.findall(r"<t([dh])[^>]*>(.*?)</t[dh]>", r, re.S)
        if cells and all(k == "h" for k, _ in cells):
            heads = [_text(c) for _, c in cells]
            continue
        if not heads or len(cells) != len(heads):
            continue
        cols, files = {}, {}
        for h, (_, c) in zip(heads, cells):
            if h.strip().lower() in SKIP:
                continue
            link = re.search(r'href="([^"]*/documents/[^"]*)"', c)
            if link:
                files[h] = urljoin(SITE, html.unescape(link.group(1)))
            elif "download" not in _text(c).lower():
                cols[h] = _text(c)
        if not any(cols.values()) and not files:
            continue
        m = ROW_ID.search(r)
        out.append({"site_id": m.group(1) if m else None, "columns": cols, "files": files})
    return out


def row_id(name, row):
    if row["site_id"]:
        return f"{name}-{row['site_id']}"
    c = row["columns"]
    return f"{name}-{sha1(*(c.get(k, '') for k in sorted(c)))[:14]}"


def run(ctx, payload):
    name, cur, delta = payload["list"], payload.get("cur", 1), payload.get("delta", 200)
    _, portlet, _, _ = LISTS[name]
    r = ctx.request("GET", list_url(name, cur, delta), timeout=180)
    if r is None:
        return None
    section = portlet_section(r.content.decode("utf-8", "replace"), portlet)
    if not section:
        return None
    rows = parse_rows(section)
    for row in rows:
        stored = {h: ctx.download(u, f"{name}/{re.sub(r'[^a-z0-9]+', '-', h.lower()).strip('-')}") for h, u in row["files"].items()} \
            if payload.get("files") else {}
        ctx.record(row_id(name, row), {"kind": "cpwd_contractor", "list": name, "page": cur, **row,
                                       "stored": stored, "source": list_url(name, 1, 20)})
    return len(rows)
