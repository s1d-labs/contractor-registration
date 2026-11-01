"""Parsing tests on saved responses: fast, no network. Add a saved response for every layout a site has."""
import io
import json
from pathlib import Path

import time

import pytest

from adapters import common, cpwd, mes, morth, nhai, ocr, pmgsy

PAGES = Path(__file__).parent / "pages"
load = lambda name: json.loads((PAGES / name).read_text(encoding="utf-8"))


# --- NHAI ---------------------------------------------------------------------------------------------------------------

def test_nhai_tender_list():
    total, rows = nhai.parse_tender_list(load("nhai_tenderlist.json"))
    assert total == 242 and len(rows) == 3
    assert rows[0]["id"] == "59064" and rows[0]["tender_no"].startswith("11057/NHAI")
    assert rows[0]["bid_submission_end_date"] == "2026-11-05"
    assert len({r["id"] for r in rows}) == 3                         # the site's own ids: stable across runs


def test_nhai_tender_list_with_no_records():
    assert nhai.parse_tender_list({"message": "No Records Found.", "_resultflag": 0}) == (0, [])
    assert nhai.parse_tender_list(None) == (0, [])


def test_nhai_tender_detail_keeps_only_filled_fields_and_https_documents():
    d = nhai.parse_tender_detail(load("nhai_tenderdetail.json"))
    assert d["title"].startswith("Request For Empanelment (RFE)")
    assert d["basic"] == {"Tender No": "NHAI/RFE/National Highways/2026/09"}
    assert d["dates"]["Bid Submission End Date"] == "2026-11-23 05:30 AM" and "Pre Bid Clarification End Date" not in d["dates"]
    assert d["documents"] == {}
    assert d["files"][0]["url"].startswith("https://nhai.gov.in/nhai/sites/default/files/") and d["files"][0]["url"].endswith(".pdf")


def test_nhai_empanelment_calls_are_recognised():
    assert nhai.EMPANELMENT.search("Request For Empanelment (RFE) of Manufacturers of Expansion Joints")
    assert nhai.EMPANELMENT.search("Expression of Interest for enlistment of agencies")
    assert not nhai.EMPANELMENT.search("Providing and Fixing portable containers under PIU Sambalpur")


def test_nhai_debarment_page_gives_rows_with_their_pdf():
    page = nhai.parse_page(load("nhai_page_debarred.json"), "individualsagencies-debarredblacklisted-morthnhidclpwds")
    assert len(page["rows"]) == 6
    row = page["rows"][0]
    assert list(row["columns"]) == ["Date", "Order Number", "Subject", "Document"]
    assert row["columns"]["Date"] == "15/06/2026" and row["columns"]["Order Number"].endswith("/5058")
    assert row["columns"]["Subject"].startswith("Debarment of Shri Raj Kumar")
    assert row["urls"] == ["https://nhai.gov.in/nhai/sites/default/files/mix_file/Debarment_order_No_5058_dated_15_06_2026_Mr_Raj_kumar.pdf"]
    assert page["docs"] == []                                        # row links are not repeated as loose documents


def test_nhai_ratings_page_gives_documents_under_their_heading():
    page = nhai.parse_page(load("nhai_page_ratings.json"), "publication-rating-dpr-consultants")
    assert page["rows"] == [] and len(page["docs"]) >= 8
    first = page["docs"][0]
    assert first["heading"] == "DPR Consultant Rating" and first["text"] == "Publication of Final Rating of DPR Consultants"
    assert first["size"] == "1.08 MB"
    assert {d["heading"] for d in page["docs"]} >= {"DPR Consultant Rating", "AE/IE Consultant Rating"}
    assert len({d["url"] for d in page["docs"]}) == len(page["docs"])


# --- MoRTH --------------------------------------------------------------------------------------------------------------

def test_morth_documents_come_with_group_and_absolute_url():
    docs = morth.parse_documents(load("morth_orders.json"), "orders-and-notices")
    assert len(docs) == 4
    deb = [d for d in docs if d["group"] == "Related to Debarment and Blacklisting"]
    assert len(deb) == 2 and all(d["url"].startswith("https://morth.gov.in/backend/") for d in deb)
    assert len({d["doc_id"] for d in docs}) == 4
    assert all(" " not in d["url"] for d in docs)                    # spaces in stored names are percent-encoded


def test_morth_broken_tmp_upload_is_flagged_not_fetched():
    assert morth.file_url("/tmp/phpOaDEMa") is None
    js = {"page": {"files": [{"name": "Circulars", "files_data": [{"title": "Broken", "file": "/tmp/phpOaDEMa"}]}]}}
    [d] = morth.parse_documents(js, "orders-and-notices")
    assert d["url"] is None and d["broken_file"] is True


def test_morth_empty_response_gives_nothing():
    assert morth.parse_documents({}, "guidelines") == [] and morth.parse_documents(None, "guidelines") == []


def test_morth_parts_split_the_documents_without_overlap():
    js = load("morth_orders.json")
    docs = morth.parse_documents(js, "orders-and-notices")
    parts = [[d for d in docs if int(d["doc_id"], 16) % 3 == k] for k in range(3)]
    assert sorted(d["doc_id"] for p in parts for d in p) == sorted(d["doc_id"] for d in docs)


def test_morth_relevance_flag():
    assert morth.RELEVANT.search("Related to Debarment and Blacklisting Speaking order declaring the firm")
    assert morth.RELEVANT.search("Model Concession Agreement (MCA) for Hybrid Annuity Model (HAM)")
    assert not morth.RELEVANT.search("Financial Sanctions Revised allocation of funds to NHIDCL")


# --- MES ----------------------------------------------------------------------------------------------------------------

def test_mes_tender_rows_with_attachment_and_cppp_id():
    rows = mes.parse_rows((PAGES / "mes_tenders.html").read_text(encoding="utf-8"))
    assert len(rows) == 4
    first = rows[0]
    assert list(first["columns"]) == ["SN", "Title", "Start Date", "End Date", "Attachment"]
    assert first["tender_id"] == "2026_MES_792606_1"
    assert first["urls"] == ["https://mes.gov.in/sites/default/files/2026-10/Tendernotice_1.pdf"]


def test_mes_row_id_ignores_the_serial_number():
    cols = {"SN": "1", "Title": "Repair of roads", "Start Date": "x"}
    assert mes.row_id("tenders", cols) == mes.row_id("tenders", {**cols, "SN": "7"})
    assert mes.row_id("tenders", cols) != mes.row_id("tenders", {**cols, "Title": "Other"})


def test_mes_product_approval_rows():
    rows = mes.parse_rows((PAGES / "mes_product_approval.html").read_text(encoding="utf-8"))
    assert rows and rows[0]["columns"]["Subject"].lower().startswith("list of approved products")
    assert rows[0]["urls"][0].startswith("https://mes.gov.in/sites/default/files/") and rows[0]["tender_id"] is None


# --- shared helpers -----------------------------------------------------------------------------------------------------

def test_upload_names_only_use_characters_the_hub_accepts():
    n = common.safe_name("Debarment order No 5058 (Mr. Raj kumar)_0001.PDF")
    assert n == "Debarment_order_No_5058_Mr._Raj_kumar_0001.pdf"
    assert common.safe_name("a%20b/c.pdf").endswith(".pdf") and "/" not in common.safe_name("a%20b/c.pdf")


def test_a_pdf_without_a_text_layer_is_flagged_for_ocr():
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    text, pages = common.pdf_text(buf.getvalue())
    assert pages == 1 and common.needs_ocr(text, pages)
    assert common.pdf_text(b"not a pdf") == ("", 0)
    assert not common.needs_ocr("x" * 500, 1)


def test_local_hub_stores_files_under_the_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    hub = common.LocalHub("p")
    [out] = hub.upload_many([("pdf/x/a.pdf", b"%PDF-1.4", "application/pdf")])
    assert (tmp_path / "data" / "p" / "pdf" / "x" / "a.pdf").read_bytes() == b"%PDF-1.4" and out["bytes"] == 8


def test_requests_stop_when_the_time_budget_is_used_up():
    ctx = common.Ctx(common.LocalHub("p"), deadline=time.time() - 1)
    with pytest.raises(common.TimeUp):
        ctx.request("GET", "https://example.invalid/")


def test_nul_characters_are_removed_before_records_are_sent():
    assert common.no_nul({"a\x00": ["x\x00y", {"t": "\x00"}], "n": 3}) == {"a": ["xy", {"t": ""}], "n": 3}
    sent = []
    hub = common.LocalHub("p")
    hub.record = lambda rid, data: sent.append((rid, data))
    common.Ctx(hub).record("id\x00", {"text": "annual\x00report"})
    assert sent == [("id", {"text": "annualreport"})]


# --- download cache, refresh items, OCR ---------------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, content=b"", headers=None, status_code=200):
        self.content, self.headers, self.status_code = content, headers or {}, status_code


def test_a_document_stored_before_is_reused_until_it_changes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = common.Ctx(common.LocalHub("p"), project="p")
    site = {"body": b"PK\x03\x04 a spreadsheet", "Content-Length": "22"}
    calls = []

    def fake(method, url, **kw):
        calls.append(method)
        return FakeResponse(site["body"] if method == "GET" else b"", {"Content-Length": site["Content-Length"]})
    monkeypatch.setattr(ctx, "request", fake)
    first = ctx.download("https://example.gov.in/a/list.xlsx", "sec")
    assert first["path"].startswith("docs/sec/") and (tmp_path / "data" / "p" / first["path"]).is_file()
    assert ctx.download("https://example.gov.in/a/list.xlsx", "sec") == first and calls == ["GET", "HEAD"]
    site.update(body=b"PK\x03\x04 a longer spreadsheet", **{"Content-Length": "29"})
    assert ctx.download("https://example.gov.in/a/list.xlsx", "sec")["bytes"] == 25 and calls[-2:] == ["HEAD", "GET"]


def test_morth_refresh_items_skip_documents_collected_before(tmp_path, monkeypatch):
    import gzip
    js = load("morth_orders.json")
    docs = morth.parse_documents(js, "orders-and-notices")
    known = tmp_path / "known.txt.gz"
    known.write_bytes(gzip.compress(f"orders-and-notices-{docs[0]['doc_id']}\n".encode()))
    monkeypatch.setattr(morth, "KNOWN", known)
    monkeypatch.setattr(morth.known_ids, "__defaults__", (known,))
    sent = []
    hub = common.LocalHub("p")
    hub.record = lambda rid, data: sent.append(rid)
    ctx = common.Ctx(hub)
    monkeypatch.setattr(ctx, "get_json", lambda *a, **k: js)
    assert morth.run(ctx, {"slug": "orders-and-notices", "new_only": True}) == len(docs) - 1
    assert f"orders-and-notices-{docs[0]['doc_id']}" not in sent


def test_family_items_have_unique_keys_and_todays_refresh():
    import family
    for p in family.PROJECTS:
        keys = [i["key"] for i in p["items"]]
        assert len(keys) == len(set(keys)) and all(1 <= len(k) <= 200 for k in keys), p["name"]
        assert p["name"].startswith(family.FAMILY) and not p.get("probe")
    by = {p["name"]: p for p in family.PROJECTS}
    assert f"tenders-{family.DAY}-p0" in {i["key"] for i in by["contractor-registration-nhai-tenders"]["items"]}
    assert by["contractor-registration-mes-works"]["proxy"] == "IN"


def test_ocr_batches_stay_within_one_project_and_the_page_budget():
    from tools.build_queues import FILES, PAGES, batches
    files = [{"project": "a", "path": f"x{i}", "pages": 100} for i in range(5)] + [{"project": "b", "path": "y", "pages": 900}]
    out = batches(files)
    assert [len(b) for b in out] == [2, 2, 1, 1] and all(len({f["project"] for f in b}) == 1 for b in out)
    assert all(len(b) <= FILES for b in out) and sum(f["pages"] for f in out[0]) <= PAGES
    assert ocr.record_id("contractor-registration-morth-documents", "ocr-needed/a.pdf").startswith("morth-documents-")


@pytest.mark.skipif(not ocr.tesseract_langs(), reason="tesseract is not installed")
def test_ocr_reads_a_scanned_page():
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("L", (1240, 600), 255)
    ImageDraw.Draw(img).text((60, 200), "DEBARMENT ORDER 5058", fill=0, font=ImageFont.load_default(size=72))
    buf = io.BytesIO()
    img.save(buf, "PDF", resolution=150)
    text, pages, read = ocr.ocr_pdf(buf.getvalue())
    assert pages == read == 1 and "DEBARMENT" in text.upper()


# --- PMGSY --------------------------------------------------------------------------------------------------------------

def test_pmgsy_report_chain_addresses():
    assert pmgsy.token((PAGES / "pmgsy_layout.html").read_text())
    src = pmgsy.iframe_src((PAGES / "pmgsy_report.html").read_text())
    assert src.startswith("https://pmgsy.dord.gov.in/MvcReportViewer.aspx?_r=%2fPMGSYCitizen%2fContractorInformation&State=30")
    exp = pmgsy.export_url((PAGES / "pmgsy_viewer.html").read_text())
    assert "OpType=Export" in exp and "&ControlID=" in exp and exp.endswith("Format=CSV")


def test_pmgsy_contractors_from_the_csv_export():
    rows = pmgsy.parse_contractors((PAGES / "pmgsy_contractors.csv").read_text(encoding="utf-8"))
    assert len(rows) == 6 and rows[0]["company"] == "A LSHERPA" and rows[0]["registration_no"] == "257/PWD/2000"
    assert rows[0]["phone1"] == "03595 254244" and rows[0]["phone2"] == "" and rows[0]["pan"] == ""
    assert rows[4]["pincode"] == "737135" and "State -" not in rows[4]["address"]
    ids = {pmgsy.contractor_id(30, r) for r in rows}
    assert len(ids) == 6 and pmgsy.contractor_id(30, {**rows[0], "sr": "99"}) == pmgsy.contractor_id(30, rows[0])
    [r] = pmgsy.parse_contractors('Sr.No.,a,b,c,d,e,f,g,1,Uttar Pradesh,M/s Chaurasiya &amp; Comp.,R P,263/99 LKO,"Middha, Ballia State - '
                                  'Uttar Pradesh Pincode - 277001",Phone1 - 0547 2227153 Phone2 -   Fax - 0 0 Email - x@y.in,AHBTSXXXXC\n')
    assert r["company"] == "M/s Chaurasiya & Comp." and r["pincode"] == "277001" and r["email"] == "x@y.in" and r["fax"] == ""
    [r] = pmgsy.parse_contractors("Sr.No.,a,b,c,d,e,f,g,1,Assam,Abdul Mannan,Abdul Mannan,APWD/R/01430,Karaiani Tezpur State - Assam Pincode - -,"
                                  "Phone1 - Phone2 - Fax - Email - ,ACTPMXXXXA\n")
    assert r["address"] == "Karaiani Tezpur" and r["pincode"] == "" and r["pan"] == "ACTPMXXXXA"


# --- CPWD ---------------------------------------------------------------------------------------------------------------

def test_cpwd_contractor_list_rows_with_the_sites_ids():
    page = (PAGES / "cpwd_contractors.html").read_text(encoding="utf-8")
    rows = cpwd.parse_rows(cpwd.portlet_section(page, "gov_in_cpwd_contractor_portlet"))
    assert len(rows) == 3 and rows[0]["site_id"] == "20071"
    c = rows[0]["columns"]
    assert c["Name of Contractor"].startswith("Sh. Shashank Sharma") and c["Class"] == "V" and c["Enlistment Valid Upto"] == "04/01/2026"
    assert "S. No." not in c and "Uploaded By" not in c
    assert cpwd.row_id("contractors", rows[0]) == "contractors-20071"
    assert cpwd.portlet_section(page, "gov_in_cpwd_ed_contractors_portlet") == ""


def test_cpwd_suspended_rows_keep_their_order_pdf():
    page = (PAGES / "cpwd_suspended.html").read_text(encoding="utf-8")
    rows = cpwd.parse_rows(cpwd.portlet_section(page, "gov_in_cpwd_suspend_contractors_portlet"))
    assert len(rows) == 2 and rows[0]["columns"]["Date of Suspension"] == "18/11/2021"
    assert rows[0]["files"]["Link"].startswith("https://erp.cpwd.gov.in/documents/") and ".pdf" in rows[0]["files"]["Link"]
    assert len({cpwd.row_id("suspended", r) for r in rows}) == 2


def test_cpwd_list_url_pages_the_portlet():
    u = cpwd.list_url("contractors", 3, 200)
    assert "_gov_in_cpwd_contractor_portlet_cur=3" in u and "_gov_in_cpwd_contractor_portlet_delta=200" in u


def test_a_login_page_is_not_stored_as_a_document(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = common.Ctx(common.LocalHub("p"), project="p")
    page = b"\n\t<!DOCTYPE html><html><head><title>Please select your identity provider.</title>"
    monkeypatch.setattr(ctx, "request", lambda method, url, **kw: FakeResponse(page, {"Content-Type": "text/html;charset=UTF-8"}))
    assert ctx.download("https://erp.cpwd.gov.in/documents/1/2/Order.pdf/uuid?t=1", "orders") is None
    assert not (tmp_path / "data" / "p" / "docs").exists()


def test_an_empty_answer_is_not_stored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = common.Ctx(common.LocalHub("p"), project="p")
    monkeypatch.setattr(ctx, "request", lambda method, url, **kw: FakeResponse(b"", {"Content-Type": "application/pdf"}))
    assert ctx.download("https://nhai.gov.in/nhai/sites/default/files/1_NIT.pdf", "tenders") is None
