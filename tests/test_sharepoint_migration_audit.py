import os
import json
import pytest

BASE_DIR = r"E:\desenvolvimento\Monitor_Esportes"

def test_authentic_sheets_count_and_indexing():
    sheets_dir = os.path.join(BASE_DIR, "docs", "sheets")
    assert os.path.exists(sheets_dir), "docs/sheets directory must exist"
    files = os.listdir(sheets_dir)
    assert len(files) == 135, f"Expected 135 sheet files, got {len(files)}"

    json_path = os.path.join(BASE_DIR, "docs", "assets", "authentic_sheets_data.json")
    assert os.path.exists(json_path), "authentic_sheets_data.json must exist"
    with open(json_path, "r", encoding="utf-8") as f:
        auth_data = json.load(f)
    assert len(auth_data) == 135, f"Expected 135 indexed datasets in authentic_sheets_data.json, got {len(auth_data)}"
    for fname, sheet_dict in auth_data.items():
        assert isinstance(sheet_dict, dict) and len(sheet_dict) > 0, f"Sheet {fname} has empty data"

def test_authentic_reports_presence():
    docs_rep = os.path.join(BASE_DIR, "docs", "reports")
    portal_rep = os.path.join(BASE_DIR, "portal_web", "reports")

    for root_dir in [docs_rep, portal_rep]:
        fut_dir = os.path.join(root_dir, "futebol")
        yt_dir = os.path.join(root_dir, "youtube")
        nba_dir = os.path.join(root_dir, "nba")

        fut_count = len(os.listdir(fut_dir))
        yt_count = len(os.listdir(yt_dir))
        nba_count = len(os.listdir(nba_dir))
        total = fut_count + yt_count + nba_count

        assert fut_count >= 150, f"Expected >=150 futebol reports in {root_dir}, got {fut_count}"
        assert yt_count >= 200, f"Expected >=200 youtube reports in {root_dir}, got {yt_count}"
        assert nba_count >= 300, f"Expected >=300 nba reports in {root_dir}, got {nba_count}"
        assert total >= 585, f"Expected >=585 total reports in {root_dir}, got {total}"

def test_zero_adgbl_sharepoint_links():
    for p in [os.path.join(BASE_DIR, "docs", "index.html"), os.path.join(BASE_DIR, "portal_web", "index.html")]:
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        assert "adgbl.sharepoint.com" not in content, f"Found adgbl.sharepoint.com in {p}"

def test_procedimentos_and_normatives():
    cfg_path = os.path.join(BASE_DIR, "config", "sharepoint_migrated_standalone_data.json")
    assert os.path.exists(cfg_path)
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data.get("procedimentos", [])) >= 60, "Expected >= 60 procedimentos"
    assert len(data.get("escala_trabalho", [])) >= 20, "Expected >= 20 escala_trabalho items"
