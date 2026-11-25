r"""
Teste Automatizado para Validação de Bootstrap Resiliente do PortalSyncManager.
Comprova que, mesmo quando 'config/sharepoint_portal_master_data.json' não existe no disco
(como ocorreu no log de D:\MediaDNA_V2\Applications\Monitor_Esportes), o PortalSyncManager
cria/recupera a estrutura automaticamente e publica com 100% de sucesso.
"""

import os
import sys
import json
import tempfile
import shutil
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.portal_sync import PortalSyncManager


def test_portal_sync_auto_bootstrap_on_missing_master_data():
    """Valida que ausência de sharepoint_portal_master_data.json é resolvida de forma transparente."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock de diretório de projeto limpo (sem config prévio)
        fake_project_root = temp_dir
        
        # Cria PDF fake
        fake_pdf = os.path.join(temp_dir, "test_auto_bootstrap_report.pdf")
        with open(fake_pdf, "wb") as f:
            f.write(b"%PDF-1.4 Mock Test Content for Missing Master Data Bootstrap Recovery")

        # Mock de get_project_root temporário
        original_get_root = PortalSyncManager.__dict__.get("sync_report_to_portal")

        # Monkeypatch get_project_root no módulo
        import modules.portal_sync as ps_module
        old_get_root_func = ps_module.get_project_root
        ps_module.get_project_root = lambda: fake_project_root

        try:
            # Verifica que config/sharepoint_portal_master_data.json NÃO existe
            config_master = os.path.join(fake_project_root, "config", "sharepoint_portal_master_data.json")
            assert not os.path.exists(config_master)

            # Executa sync_report_to_portal (que antes falhava com: [PortalSync] Arquivo master data não encontrado)
            success = PortalSyncManager.sync_report_to_portal(
                pdf_path=fake_pdf,
                drive_name="Relatorios_de_Jogos_NBA",
                category="nba",
                filename="Relatorio_NBA_LAL_at_GSW_20261124.pdf",
                partida="Los Angeles Lakers @ Golden State Warriors",
                campeonato="NBA Regular Season",
                plataforma="Amazon Prime Video",
                confianca="99.9%"
            )

            # Deve ser True!
            assert success is True, "sync_report_to_portal deve retornar True mesmo sem master data pré-existente!"

            # Deve ter criado config/sharepoint_portal_master_data.json
            assert os.path.exists(config_master), "O master data deve ter sido criado automaticamente!"

            with open(config_master, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "Relatorios_de_Jogos_NBA" in data.get("drives", {}), "Drive da NBA deve constar no master data criado!"
            items = data["drives"]["Relatorios_de_Jogos_NBA"]["items"]
            assert len(items) == 1
            assert items[0]["name"] == "Relatorio_NBA_LAL_at_GSW_20261124.pdf"
            assert items[0]["webUrl"] == "reports/nba/Relatorio_NBA_LAL_at_GSW_20261124.pdf"

            # Deve ter copiado o PDF para docs/reports/nba/ e portal_web/reports/nba/
            docs_dest = os.path.join(fake_project_root, "docs", "reports", "nba", "Relatorio_NBA_LAL_at_GSW_20261124.pdf")
            portal_dest = os.path.join(fake_project_root, "portal_web", "reports", "nba", "Relatorio_NBA_LAL_at_GSW_20261124.pdf")
            assert os.path.exists(docs_dest), "PDF deve existir em docs/reports/nba"
            assert os.path.exists(portal_dest), "PDF deve existir em portal_web/reports/nba"

            print("✅ TESTE DE AUTO-BOOTSTRAP E RECUPERAÇÃO DO PORTAL PASSOU COM 100% DE SUCESSO!")

        finally:
            ps_module.get_project_root = old_get_root_func


if __name__ == "__main__":
    test_portal_sync_auto_bootstrap_on_missing_master_data()
