import os
import sys
import json
import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, r"E:\desenvolvimento\Monitor_Esportes")


def test_streaming_today_tomorrow_cards():
    portal_path = r"E:\desenvolvimento\Monitor_Esportes\portal_web\index.html"
    assert os.path.exists(portal_path)
    with open(portal_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    streaming_pane = soup.find("div", {"id": "pane-streaming"})
    assert streaming_pane is not None, "pane-streaming deve existir no DOM"

    grid = streaming_pane.find("div", class_="today-tomorrow-grid")
    assert grid is not None, "Quadro de destaques Hoje/Amanhã deve existir em pane-streaming"

    card_hoje = grid.find("div", class_="card-hoje")
    assert card_hoje is not None, "Card Hoje deve existir"
    assert card_hoje.find("span", {"id": "badge-count-hoje"}) is not None
    assert card_hoje.find("div", {"id": "list-eventos-hoje"}) is not None

    card_amanha = grid.find("div", class_="card-amanha")
    assert card_amanha is not None, "Card Amanhã deve existir"
    assert card_amanha.find("span", {"id": "badge-count-amanha"}) is not None
    assert card_amanha.find("div", {"id": "list-eventos-amanha"}) is not None


def test_batch_delete_and_checkall_components():
    portal_path = r"E:\desenvolvimento\Monitor_Esportes\portal_web\index.html"
    with open(portal_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    list_pane = soup.find("div", {"id": "pane-list-viewer"})
    assert list_pane is not None, "pane-list-viewer deve existir"

    btn_del = list_pane.find("button", {"id": "btn-delete-generic"})
    assert btn_del is not None, "Botão btn-delete-generic deve existir na barra de comandos"

    # Verificar presença das funções no script JS
    assert "function toggleCheckAllGeneric" in html
    assert "function updateGenericSelectionUI" in html
    assert "function deleteSelectedGenericItems" in html
    assert "function handleRowDblClick" in html
    assert "function openReportPdf" in html
    assert "modal-pdf-viewer" in html


def test_reports_column_structure_in_master_data():
    master_file = r"E:\desenvolvimento\Monitor_Esportes\config\sharepoint_portal_master_data.json"
    assert os.path.exists(master_file)
    with open(master_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Relatorios_de_Jogos
    rel_jogos = data.get("lists", {}).get("Relatorios_de_Jogos")
    assert rel_jogos is not None
    cols_jogos = [c["displayName"] for c in rel_jogos.get("columns", [])]
    assert "Data_Hora" in cols_jogos
    assert "Campeonato" in cols_jogos
    assert "Partida" in cols_jogos
    assert "Plataforma" in cols_jogos
    assert "Confiança" in cols_jogos
    assert "Auditado" in cols_jogos
    assert "Modificado" in cols_jogos
    assert "Criado por" in cols_jogos
    assert "Arquivo / Relatório PDF" in cols_jogos

    # Relatorio Jogos Youtube
    rel_yt = data.get("lists", {}).get("Relatorio Jogos Youtube")
    assert rel_yt is not None
    cols_yt = [c["displayName"] for c in rel_yt.get("columns", [])]
    assert "Data_Jogo" in cols_yt
    assert "Campeonato" in cols_yt
    assert "Partida" in cols_yt
    assert "Canal" in cols_yt
    assert "Confiança" in cols_yt

    # Relatorios_de_Jogos_NBA
    rel_nba = data.get("lists", {}).get("Relatorios_de_Jogos_NBA")
    assert rel_nba is not None
    cols_nba = [c["displayName"] for c in rel_nba.get("columns", [])]
    assert "Data_Hora" in cols_nba
    assert "Campeonato" in cols_nba
    assert "Partida" in cols_nba
    assert "Plataforma" in cols_nba
    assert "Confiança" in cols_nba


def test_portal_sync_dual_update():
    from modules.portal_sync import PortalSyncManager
    import tempfile

    # Criar um PDF temporário
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"%PDF-1.4 dummy content")
        tmp_pdf = tmp.name

    try:
        ok = PortalSyncManager.sync_report_to_portal(
            pdf_path=tmp_pdf,
            drive_name="Relatorios_de_Jogos",
            category="futebol",
            filename="test_auto_audit_unit_test.pdf",
            partida="Teste x Unit",
            campeonato="Brasileiro Serie A",
            plataforma="Amazon Prime",
            confianca="100.0%",
            auditado=True,
            publish_github=False
        )
        assert ok is True

        # Verificar se refletiu no master_data
        master_file = r"E:\desenvolvimento\Monitor_Esportes\config\sharepoint_portal_master_data.json"
        with open(master_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Verificar em drives
        drive_items = data.get("drives", {}).get("Relatorios_de_Jogos", {}).get("items", [])
        assert any(it.get("name") == "test_auto_audit_unit_test.pdf" for it in drive_items)

        # Verificar em lists
        list_items = data.get("lists", {}).get("Relatorios_de_Jogos", {}).get("items", [])
        target_item = next((it for it in list_items if it.get("Title") == "test_auto_audit_unit_test.pdf"), None)
        assert target_item is not None
        assert target_item["Partida"] == "Teste x Unit"
        assert target_item["Campeonato"] == "Brasileiro Serie A"
        assert target_item["Plataforma"] == "Amazon Prime"
        assert target_item["Confianca"] == "100.0%"
        assert target_item["Auditado"] is True
        assert target_item["CriadoPor"] == "svc.captacao"
    finally:
        if os.path.exists(tmp_pdf):
            os.remove(tmp_pdf)
        # Limpar item de teste do disco e do master data para não poluir produção
        for sub in ("docs", "portal_web"):
            p_rem = os.path.join(r"E:\desenvolvimento\Monitor_Esportes", sub, "reports", "futebol", "test_auto_audit_unit_test.pdf")
            if os.path.exists(p_rem):
                os.remove(p_rem)
            idx_p = os.path.join(r"E:\desenvolvimento\Monitor_Esportes", sub, "reports", "index_futebol.json")
            if os.path.exists(idx_p):
                with open(idx_p, "r", encoding="utf-8") as f_i:
                    idx_d = json.load(f_i)
                idx_d["items"] = [it for it in idx_d.get("items", []) if it.get("name") != "test_auto_audit_unit_test.pdf"]
                idx_d["items_count"] = len(idx_d["items"])
                with open(idx_p, "w", encoding="utf-8") as f_i:
                    json.dump(idx_d, f_i, ensure_ascii=False, indent=2)
        master_file = r"E:\desenvolvimento\Monitor_Esportes\config\sharepoint_portal_master_data.json"
        if os.path.exists(master_file):
            with open(master_file, "r", encoding="utf-8") as f_m:
                m_d = json.load(f_m)
            drv = m_d.get("drives", {}).get("Relatorios_de_Jogos")
            if drv and "items" in drv:
                drv["items"] = [it for it in drv["items"] if it.get("name") != "test_auto_audit_unit_test.pdf"]
                drv["items_count"] = len(drv["items"])
            lst = m_d.get("lists", {}).get("Relatorios_de_Jogos")
            if lst and "items" in lst:
                lst["items"] = [it for it in lst["items"] if it.get("Title") != "test_auto_audit_unit_test.pdf"]
            with open(master_file, "w", encoding="utf-8") as f_m:
                json.dump(m_d, f_m, ensure_ascii=False, indent=2)
