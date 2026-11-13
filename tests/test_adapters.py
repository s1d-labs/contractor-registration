"""Parsing tests on saved responses: fast, no network. Add a saved response for every layout a site has."""
import io
import json
from pathlib import Path

import time

import pytest

from adapters import common, cpwd, mes, morth, nhai, ocr, pmgsy, rdso, statepwd

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


def test_an_unreadable_text_layer_is_flagged_for_ocr():
    junk = "f\\€\nd\\T\nt9\nE.L\n!\n(s\neCI\n\"-,I.rfi\n,-.4\nLU'lt *\n[:* :-affi:>11 f,L\nreL;-\n" * 20
    real = ("Certificate of enlistment. The firm is enlisted as Class III contractor in the Public Works Department "
            "(Roads and Buildings) for the period 01/04/2024 to 31/03/2027, tender limit Rs. 50.00 lakh. ") * 5
    hindi = "ठेकेदार का पंजीकरण प्रमाण पत्र लोक निर्माण विभाग दिनांक 01/04/2024 " * 10
    assert common.readable(junk) < 0.2 and common.needs_ocr(junk, 1)
    assert common.readable(real) > 0.6 and not common.needs_ocr(real, 1)
    assert not common.needs_ocr(hindi, 1)


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


def test_pmgsy_agreements_drill_through_the_states_total_row():
    viewer = (PAGES / "pmgsy_agr_viewer.html").read_text(encoding="utf-8")
    url, form = pmgsy.drill_form(viewer, pmgsy.DRILLS["awarded"][0])
    assert url.startswith("https://pmgsy.dord.gov.in/MvcReportViewer.aspx?_r=%2fPMGSYCitizen%2fTend_Agr_DetailsReport&Level=2&State=30")
    assert form["ReportViewer$ctl09$ReportControl$ctl03"] == "249iT0:0" and form["__EVENTTARGET"] == "ReportViewer$ctl03"
    assert form["ReportViewer$ctl09$VisibilityState$ctl00"] == "ReportPage"      # every hidden field goes back, or the viewer fails
    assert pmgsy.drill_form(viewer, "999iT0:0") == (None, {})                      # no such cell: a state without works


def test_pmgsy_works_awarded_and_terminated_from_the_csv_exports():
    works = pmgsy.parse_works((PAGES / "pmgsy_agr_awarded.csv").read_text(encoding="utf-8"))
    assert len(works) == 6 and works[0]["package"] == "BM0201" and works[0]["work_name"] == "MANGTHANG"
    assert works[0]["sanction_cost_lakh"] == "1.01" and works[0]["awarded_cost_lakh"] == "1.01" and works[0]["road_length_km"] == "0.010"
    assert works[-1]["sanction_date"] == "22-01-2026" and works[-1]["awarded_cost_lakh"] == "505.85" and works[-1]["block"] == "Yuksom"
    assert "Textbox14" not in works[0] and "CURRDATE" not in works[0]               # the report's totals and today's date are dropped
    gone = pmgsy.parse_works((PAGES / "pmgsy_agr_terminated.csv").read_text(encoding="utf-8"))
    assert len(gone) == 4 and gone[0]["road_length_km"] == "3.800" and gone[0]["sanction_cost_lakh"] == "226.23"
    assert "awarded_cost_lakh" not in gone[0]
    twins = [{**works[0], "work_type": "LSB", "work_name": "Ramitey Khola", "sanction_cost_lakh": c} for c in ("201.19", "190.47")]
    assert pmgsy.work_id(30, "awarded", twins[0]) != pmgsy.work_id(30, "awarded", twins[1])   # two bridges, one name, one package


# --- State PWD / R&B ----------------------------------------------------------------------------------------------------

def test_gujarat_civil_contractor_list_columns_from_the_pdf():
    meta, rows = statepwd.parse_list(statepwd.pdf_pages((PAGES / "gujarat_rnb_civil.pdf").read_bytes()))
    assert meta["as_on"] == "14-09-2026" and meta["total"] == 8113
    assert len(rows) == 39 and [r["sr"] for r in rows] == [str(k) for k in range(1, 40)]
    r = rows[0]
    assert r["division"] == "Arvalli (R&B) Division, Modasa" and r["company"] == "SITARAM INFRA PROJECT"
    assert r["address"] == "5327, Malpur Chokdi, Nr. Ankur Petrleum, Bayad Building, Dhansura,Arvalli-383310"
    assert (r["class"], r["nature_of_firm"], r["registration_date"], r["valid_upto"]) == ("A", "Partnership Firm", "20-01-2026", "31-12-2028")
    r = rows[16]                                                                  # wrapped company name and a four-line address
    assert r["company"] == "RAJPUT INFRASTRUCTURE COMPANY" and r["address"].endswith("OPP. GURUKUL SCHOOL, GANDHIDHAM-KACHCHH")
    assert rows[25]["nature_of_firm"] == "Private Limited Company" and rows[25]["class"] == "AA"


def test_gujarat_electrical_list_and_row_ids():
    meta, rows = statepwd.parse_list(statepwd.pdf_pages((PAGES / "gujarat_rnb_electrical.pdf").read_bytes()))
    assert meta["as_on"] == "31-07-2026" and len(rows) == 13
    assert rows[0]["company"] == "CIMCON SOFTWARE INDIA PRIVATE LIMITED" and rows[0]["address"].startswith("1106,11th Floor,Time Square")
    assert rows[0]["address"].endswith("Thaltej ,Ahmedabad -380059") and rows[0]["nature_of_firm"] == "Private Limited Company"
    assert len({statepwd.row_id("gujarat-rnb-electrical", r) for r in rows}) == 13


# --- RDSO ---------------------------------------------------------------------------------------------------------------

def test_rdso_section_links_the_lists_about_sources():
    links = rdso.source_lists((PAGES / "rdso_section.html").read_text(encoding="utf-8"))
    assert [u.rsplit("/", 1)[1] for _, u in links] == ["D_13403_1717398395798.pdf", "D_13403_1717398403672(1).pdf", "D_13403_1717398409779.pdf"]


def test_rdso_items_with_fewer_than_three_sources():
    meta, items = rdso.parse_items(statepwd.pdf_pages((PAGES / "rdso_fewer_than_three.pdf").read_bytes()))
    assert meta["as_on"] == "03.06.2024" and rdso.list_name(meta["title"]) == "fewer-than-three-sources"
    assert len(items) == 25 and [i["sr"] for i in items] == [str(k) for k in range(1, 26)]
    assert items[0]["item_id"] == "3100429" and items[0]["item"].startswith("Control and Relay Panel including") and items[0]["subitem_id"] == ""
    assert items[0]["vendor_count"] == 2 and items[0]["directorate"] == "TI"
    sub = next(i for i in items if i["subitem_id"] == "3100508002")             # a justified description over two columns
    assert sub["subitem"] == "Spring Auto tensioning device for 2400 kgf Tension in OHE" and sub["vendor_count"] == 0
    assert len({(i["item_id"], i["subitem_id"]) for i in items}) == 25


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


def test_nhai_refetch_records_only_documents_that_now_load():
    class Stub:
        def __init__(self):
            self.records = {}

        def download(self, url, section, headers=None):
            return {"path": f"pdf/{section}/x.pdf", "bytes": 10} if url.endswith("ok.pdf") else None

        def record(self, rid, data):
            self.records[rid] = data

    ctx = Stub()
    n = nhai.run(ctx, {"kind": "refetch", "section": "tenders-archive/tenderarchive",
                       "documents": [{"tender": "1", "url": "https://nhai.gov.in/a/ok.pdf"}, {"tender": "2", "url": "https://nhai.gov.in/b/empty.pdf"}]})
    [(rid, data)] = ctx.records.items()
    assert n == 1 and rid == f"refetch-{common.sha1('https://nhai.gov.in/a/ok.pdf')[:16]}" and data["tender_record"] == "tender-1"


def test_family_refetch_items_are_on_the_archive_project():
    import family
    archive = next(p for p in family.PROJECTS if p["name"].endswith("-nhai-tender-archive"))
    refetch = [i for i in archive["items"] if i["payload"].get("kind") == "refetch"]
    assert refetch and all(i["payload"]["section"].startswith("tenders-archive/") for i in refetch)
    assert sum(len(i["payload"]["documents"]) for i in refetch) >= 2000


def test_maharashtra_electrical_list_groups_rows_by_district_and_class():
    rows = statepwd.parse_mh(statepwd.pdf_pages((PAGES / "maharashtra_pwd_electrical.pdf").read_bytes()))
    assert [r["sr"] for r in rows] == [str(k) for k in range(1, 16)]
    r = rows[1]
    assert (r["district"], r["class"], r["contractor_number"], r["company"]) == ("Ahmadnagar", "A", "A-38", "M/s. A. B. Electricals")
    assert r["address"] == "Maliwada, Near Veshi, Ahmadnagar.," and r["valid_upto"] == "6/9/2017" and r["emd_exempted"] == "N"
    assert rows[-1]["class"] == "Unemployed Engineers(D class)" and rows[-1]["company"].startswith("M/s. Mawal Infrastructure")
    assert len({statepwd.mh_row_id("maharashtra-pwd-electrical", r) for r in rows}) == 15


def test_maharashtra_civil_list_registration_numbers_and_dates():
    rows = statepwd.parse_mh(statepwd.pdf_pages((PAGES / "maharashtra_pwd_civil.pdf").read_bytes()))
    assert len(rows) == 11 and rows[0]["district"] == "Ahmadnagar"
    assert (rows[1]["registration_no"], rows[1]["registered_on"]) == ("6993", "5/8/2009")
    assert (rows[1]["valid_upto"], rows[1]["exempted_upto"], rows[1]["emd_exempted"]) == ("21/07/2014", "21/07/2014", "Y")
    assert rows[-1]["class"] == "I" and rows[-1]["registered_on"] == "27/10/2010"       # the class header on the second page


def test_pmgsy_awarded_cost_repeated_per_package_is_marked():
    works = [{"package": "CG1639", "sanction_cost_lakh": s, "awarded_cost_lakh": "5111.40"} for s in ("123.20", "144.34", "253.98")]
    works += [{"package": "SK03", "sanction_cost_lakh": s, "awarded_cost_lakh": a} for s, a in (("201.19", "199.19"), ("195.17", "193.25"))]
    works += [{"package": "BM0201", "sanction_cost_lakh": "1.01", "awarded_cost_lakh": "1.01"}]
    marked = {(w["package"], w["awarded_is_package_total"]) for w in pmgsy.mark_package_totals(works)}
    assert marked == {("CG1639", True), ("SK03", False), ("BM0201", False)}
    gone = pmgsy.mark_package_totals([{"package": "X", "sanction_cost_lakh": "1"}])
    assert "awarded_is_package_total" not in gone[0]


def test_wb_phed_vendor_lists_table():
    rows = statepwd.parse_doc_table((PAGES / "wbphed_vendor_lists.html").read_text(encoding="utf-8"), "https://wbphed.gov.in/en/approved-vendor-list")
    assert len(rows) == 4 and rows[0]["category"] == "Mechanical" and rows[0]["issue_date"] == "12-10-2026"
    assert rows[0]["url"] == ("https://wbphed.gov.in/resources/approvedVendor/"
                              "List%20of%20approved%20Vendors%20for%20Elecro-%20Mechanical%20items%20dated%2012.10.2026.pdf")
    assert rows[2]["description"].startswith("Updated Approved list of vendors (Civil and Electromechanical Items)")


def test_pmgsy_contractor_kpi_scores():
    rows = pmgsy.parse_kpi(load("pmgsy_kpi.json"))
    assert len(rows) == 4 and rows[0]["company"] == "M/S NIKUMBH BHARDWAZ CONSTRUCTION"
    assert (rows[0]["construction"], rows[0]["mobilization"], rows[0]["quality"], rows[0]["score"]) == (32.0, 30.0, 25.0, 87.0)
    assert len(rows[0]["pan"]) == 10 and pmgsy.parse_kpi(None) == []


def test_uttarakhand_pwd_applications():
    rows = statepwd.parse_uk((PAGES / "ukpwd_contractors.html").read_text())
    assert [r["application_no"] for r in rows] == ["69424", "53624", "107668"]
    first = rows[0]
    assert first["registration_no"] == "B1006ME1223" and first["pan"] == "AAAAA1111A"
    assert first["class"] == "B" and first["category"] == "Mechanical" and first["status"] == "Registration Granted"
    assert first["valid_upto"] == "30 Jun 2026" and first["offices"] == ["CE-Dehradun"]
    assert rows[1]["company"] == "Sample & Sons" and rows[1]["pan"] == "" and rows[1]["registration_no"] == ""
    assert rows[2]["offices"] == ["CE-Tehri", "CE-Pauri"]          # one application sent to two offices
    assert statepwd.parse_uk("<html>signed out</html>") == []


def test_odisha_works_ledger():
    rows, more = statepwd.parse_ledger((PAGES / "odisha_ledger.html").read_text())
    assert more
    assert rows[0] == {"sr": "1", "company": "M/s Example Infra Pvt. Ltd.", "address": "At- Test Sahi; Dist: Cuttack, Odisha"}
    assert rows[1]["company"] == "Sample Constructions & Co." and rows[1]["address"] == "Plot 4, Unit-2; Bhubaneswar"
    assert statepwd.parse_ledger("<table><tbody></tbody></table>") == ([], False)


def test_tripura_enlisted_tables():
    rows = statepwd.parse_accordion_tables((PAGES / "tripura_enlisted.html").read_text())
    assert len(rows) == 2
    a, b = rows
    assert a["section"] == "Enlistment of Contractors Class-I" and a["enlistment_no"] == "PWD/TRIP/C-I/00099"
    assert (a["valid_from"], a["valid_upto"], a["qualified_upto"]) == ("2021-02-08", "2026-02-07", "Any amount")
    assert a["certificate_url"].endswith("/CLASS-I/00099.pdf") and a["father_or_partner"] == "Lt.Sample Das"
    assert b["section"] == "Enlistment of Contractors Class-V" and b["valid_from"] == "" and b["valid_upto"] == "2020-12-08"
    assert b["qualified_upto"] == "Upto Rs. 40 Lac" and b["certificate_url"] == ""


def _w(x, y, text):
    return (x, y, x + 5 * len(text), text)


def test_arunachal_column_list():
    head = [_w(88, 679, "Sl"), _w(134, 679, "Name"), _w(216, 679, "Address"), _w(332, 679, "Enlistment"),
            _w(435, 679, "Validity"), _w(511, 679, "Remarks"), _w(435, 669, "Enlistment")]
    title = [_w(246, 726, "Class"), _w(270, 726, "II"), _w(282, 726, "(Civil)"), _w(320, 726, "Category"), _w(362, 726, "as"),
             _w(374, 726, "on"), _w(388, 726, "30/09/2026.")]
    numbers = [_w(97, 655, "1"), _w(158, 655, "2"), _w(267, 655, "3"), _w(372, 655, "4"), _w(454, 655, "5"), _w(526, 655, "6")]
    page1 = title + head + numbers + [
        _w(97, 640, "1"), _w(113, 640, "M/s"), _w(132, 640, "Example"), _w(210, 640, "Shri"), _w(232, 640, "Test,"),
        _w(331, 640, "No.CEAP(D&P)/"), _w(441, 640, "5th"), _w(460, 640, "June'"), _w(490, 640, "2029"),
        _w(113, 629, "Builders"), _w(210, 629, "Itanagar"), _w(331, 629, "PLG-48/2008-09/II/03"),
        _w(331, 618, "Dated"), _w(360, 618, "6th"), _w(378, 618, "June"), _w(400, 618, "2008.")]
    page2 = head + [
        _w(210, 650, "Pin"), _w(230, 650, "791111."),                       # continues row 1 from the previous page
        _w(97, 630, "2"), _w(113, 630, "M/s"), _w(132, 630, "Demo"), _w(210, 630, "Naharlagun"),
        _w(331, 630, "No."), _w(350, 630, "CEAP(CSQ)/W-48/II/466."), _w(331, 619, "Dtd:"), _w(355, 619, "7th"), _w(372, 619, "May'"),
        _w(397, 619, "2026"), _w(441, 630, "5th"), _w(460, 630, "May'"), _w(490, 630, "2031"), _w(511, 630, "Cancelled"),
        _w(97, 590, "NB:"), _w(120, 590, "1)"), _w(140, 590, "Discrepancies")]
    meta, rows = statepwd.parse_columns([page1, page2])
    assert meta["as_on"] == "30/09/2026" and len(rows) == 2
    a, b = rows
    assert (a["sr"], a["class"], a["company"]) == ("1", "II", "M/s Example Builders")
    assert a["address"] == "Shri Test, Itanagar Pin 791111."
    assert a["enlistment_no"] == "No.CEAP(D&P)/ PLG-48/2008-09/II/03" and a["enlistment_date"] == "6th June 2008"
    assert a["valid_upto"] == "5th June' 2029" and a["remarks"] == ""
    assert b["enlistment_no"] == "No. CEAP(CSQ)/W-48/II/466." and b["enlistment_date"] == "7th May' 2026"
    assert b["remarks"] == "Cancelled" and "Discrepancies" not in b["company"]


def test_numbered_list_and_pdf_links():
    text = "LIST OF ENLISTED CONTRATOR AS CLASS-1\n1. Example Construction Ltd, Sector 16, Hisar.\n2. Sample Co,\nVillage Test, Rohtak.\n3.Demo Infra, Plot 4, Jind\n"
    rows = statepwd.parse_numbered(text)
    assert [r["sr"] for r in rows] == ["1", "2", "3"]
    assert rows[1]["entry"] == "Sample Co, Village Test, Rohtak." and rows[2]["entry"] == "Demo Infra, Plot 4, Jind"
    page = ('<a href="pdf/31072025/cancellation_x.pdf">Office Order for Cancellation of Contractor Registration of M/S X</a>'
            '<a href="pdf/BE2019-20.pdf">Budget Estimate 19-20</a>'
            '<a href="pdf/06102026/Class-II.pdf">List of valid Enlisted Re-validated Contractors Firms Class-II</a>'
            '<a href="pdf/31072025/cancellation_x.pdf">Office Order for Cancellation of Contractor Registration of M/S X</a>')
    links = statepwd.parse_pdf_links(page, "https://arunachalpwd.org/contractors.php")
    assert [(l["doc_type"], l["url"]) for l in links] == [
        ("cancellation", "https://arunachalpwd.org/pdf/31072025/cancellation_x.pdf"),
        ("list", "https://arunachalpwd.org/pdf/06102026/Class-II.pdf")]


# --- PMGSY road register (pmgsyreg) and eMARG ----------------------------------------------------------------------------

from adapters import emarg, pmgsyreg  # noqa: E402


def test_pmgsyreg_core_network_roads_of_a_block():
    text = (PAGES / "pmgsy_corenetwork_leaf.csv").read_text(encoding="utf-8")
    rows = pmgsyreg.parse_leaf(text)
    assert len(rows) == 5                                            # 4 roads; L059 serves two habitations (two rows)
    assert rows[0]["plan_cn_road_number"] == "L031" and rows[0]["rd_from"] == "T05" and rows[0]["plan_rd_length"] == "7.000"
    assert rows[1]["mast_hab_name"] == "DUNGDUNG." and rows[2]["mast_hab_name"] == "RALAP."
    assert "textbox87" not in rows[0]                                # captions ("Sr.No.") are not data
    assert pmgsyreg.heading_block(pmgsyreg.heading(text)) == "Khamdung"


def test_pmgsyreg_completed_and_maintenance_leaves():
    done = pmgsyreg.parse_leaf((PAGES / "pmgsy_completed_leaf.csv").read_text(encoding="utf-8"))
    assert done[0]["ims_package_id"] == "BM0101" and done[0]["completion_date"] == "March-2001" and len(done) == 5
    upkeep = pmgsyreg.parse_leaf((PAGES / "pmgsy_maintenance_leaf.csv").read_text(encoding="utf-8"))
    assert upkeep[0]["ims_package_id"] == "02PKG3PHV2" and upkeep[0]["main_tot_exp"] == "38.10" and len(upkeep) == 4


def test_pmgsyreg_drill_ids_in_row_order():
    page = "".join(f"InvokeReportAction('Drillthrough','65iT0R0x{k}:0')" for k in (10, 2, 0, 1, 2))
    assert pmgsyreg.drill_ids(page) == ["65iT0R0x0:0", "65iT0R0x1:0", "65iT0R0x2:0", "65iT0R0x10:0"]
    assert pmgsyreg.leaf_name('"ExportUrlBase":"/Reserved.ReportViewerWebControl.axd?OpType=Export\\u0026FileName=RWCN_LVLReport\\u0026Format="') == "RWCN_LVLReport"


def test_emarg_road_list():
    roads = emarg.first_list(load("emarg_roads.json"))
    rec = emarg.road_record(roads[0], {"stateId": 7, "stateName": "Chhattisgarh"}, {"districtId": 622, "districtName": "Balod"},
                            {"blockId": 6990, "blockName": "Balod"})
    assert rec["road_details_id"] == 14124 and rec["road_name"] == "Jamarua  - Semarkona Road".strip()
    assert rec["fields"] == {"roadDetailsId": 14124, "encRoadDetailsId": "wzlHKPKyuuQ", "roadName": "Jamarua  - Semarkona Road"}


def test_pmgsyreg_knows_the_sites_error_page():
    err = "<html><head><title>Error &ndash; OMMAS | PMGSY</title></head><body><h1>Something went wrong</h1>" \
          "<p>An error occurred while processing your request. Please try again in a few moments.</p></body></html>"
    assert pmgsyreg.site_error(err)
    assert not pmgsyreg.site_error("") and not pmgsyreg.site_error(None)
    assert not pmgsyreg.site_error("x" * 6000 + "Something went wrong")     # a report page that happens to hold the words
