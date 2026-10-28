"""Parsing tests on saved responses: fast, no network. Add a saved response for every layout a site has."""
import io
import json
from pathlib import Path

from adapters import common, morth, nhai

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
