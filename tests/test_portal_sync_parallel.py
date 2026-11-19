"""
Teste Automatizado E2E de Sincronização em Paralelo de Relatórios para o Portal Web.
Garante que a chamada ao PortalSyncManager sincronize arquivos, master data e index.html.
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.portal_sync import PortalSyncManager, PROJECT_ROOT
from scripts.build_portal_web import generate_portal

def test_portal_sync_parallel():
    # 1. Criar PDF temporário de teste
    test_pdf_path = os.path.join(PROJECT_ROOT, "scratch", "test_report_parallel.pdf")
    os.makedirs(os.path.dirname(test_pdf_path), exist_ok=True)
    with open(test_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 Mock PDF Content for Parallel Sync Verification")

    test_filename = "test_audit_flamengo_x_fluminense_20261119.pdf"

    try:
        # 2. Executar sincronização paralela
        res = PortalSyncManager.sync_report_to_portal(
            pdf_path=test_pdf_path,
            drive_name="Relatorios_de_Jogos",
            category="futebol",
            filename=test_filename,
            partida="Flamengo x Fluminense",
            campeonato="Brasileirão Série A",
            plataforma="CazéTV (YouTube)",
            confianca="99.5%"
        )
        assert res is True, "PortalSyncManager.sync_report_to_portal retornou False"

        # 3. Validar arquivos gerados em docs/ e portal_web/
        docs_file = os.path.join(PROJECT_ROOT, "docs", "reports", "futebol", test_filename)
        portal_file = os.path.join(PROJECT_ROOT, "portal_web", "reports", "futebol", test_filename)
        assert os.path.exists(docs_file), f"Arquivo não encontrado em {docs_file}"
        assert os.path.exists(portal_file), f"Arquivo não encontrado em {portal_file}"

        # 4. Validar que master data foi atualizado
        master_data_path = os.path.join(PROJECT_ROOT, "config", "sharepoint_portal_master_data.json")
        with open(master_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        futebol_items = data["drives"]["Relatorios_de_Jogos"]["items"]
        matching = [it for it in futebol_items if it.get("name") == test_filename]
        assert len(matching) == 1, f"Item {test_filename} não encontrado no master data"
        assert matching[0]["webUrl"] == f"reports/futebol/{test_filename}"
        assert matching[0]["meta"]["partida"] == "Flamengo x Fluminense"

        # 5. Validar que docs/index.html foi recompilado e contém o item
        docs_html = os.path.join(PROJECT_ROOT, "docs", "index.html")
        with open(docs_html, "r", encoding="utf-8") as f:
            html_text = f.read()
        assert test_filename in html_text, f"Item {test_filename} não encontrado no HTML de docs/index.html"

        print("✅ TESTE DE REPORTES EM PARALELO PASSOU COM 100% DE SUCESSO!")

    finally:
        # Limpeza do item de teste para manter o master data idêntico ao SharePoint
        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)
        docs_file = os.path.join(PROJECT_ROOT, "docs", "reports", "futebol", test_filename)
        if os.path.exists(docs_file):
            os.remove(docs_file)
        portal_file = os.path.join(PROJECT_ROOT, "portal_web", "reports", "futebol", test_filename)
        if os.path.exists(portal_file):
            os.remove(portal_file)

        master_data_path = os.path.join(PROJECT_ROOT, "config", "sharepoint_portal_master_data.json")
        if os.path.exists(master_data_path):
            with open(master_data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data["drives"]["Relatorios_de_Jogos"]["items"]
            data["drives"]["Relatorios_de_Jogos"]["items"] = [it for it in items if it.get("name") != test_filename]
            data["drives"]["Relatorios_de_Jogos"]["items_count"] = len(data["drives"]["Relatorios_de_Jogos"]["items"])
            with open(master_data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        generate_portal()

if __name__ == "__main__":
    test_portal_sync_parallel()
