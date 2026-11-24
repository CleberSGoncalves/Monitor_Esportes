# -*- coding: utf-8 -*-
import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.build_portal_web import generate_portal

def test_build_portal_web_creates_file_and_validates_sharepoint_replica_and_rbac():
    html_path = generate_portal()
    assert os.path.exists(html_path)
    assert os.path.getsize(html_path) > 100000

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Validação de Título e Hero Banner 1:1 com SharePoint
    assert "Suporte Captação" in content
    assert "São Paulo, Brasil" in content
    assert "hero-3x3-grid" in content
    assert "hero-network-svg" in content
    assert "Entre em contato com a nossa equipe" in content

    # 2. Validação da Grade 3x3 e Módulos Nativos Autônomos
    assert "Contatos Hospedeiros" in content
    assert "Documentos" in content
    assert "Escala de Trabalho" in content
    assert "Dashboard & Indicadores" in content
    assert "Metas" in content
    assert "Painel de Ocorrências" in content
    assert "Procedimentos N1" in content
    assert "Projetos" in content
    assert "Programação" in content

    # 3. Validação do Módulo Nativo de Escala de Trabalho 2026 & CLT 66
    assert "pane-escala" in content
    assert "Artigo 66 da CLT" in content
    assert "allEscalaMonths" in content
    assert "initEscalaMonths" in content
    assert "Escala_de_trabalho_2026.xlsx" in content

    # 4. Validação dos Dados Nativos Migrados (Hospedeiros, Ocorrências, Procedimentos)
    assert "allHospedeiros" in content
    assert "allOcorrencias" in content
    assert "allProcedimentos" in content
    assert "allDocumentos" in content
    assert "exportHospedeirosCSV" in content
    assert "exportOcorrenciasCSV" in content

    # 5. Validação dos Links Externos Oficiais
    assert "Links Externos" in content
    assert "Site - Media DNA" in content
    assert "Redmine" in content
    assert "Zabbix" in content
    assert "RH Open" in content
    assert "Service Now" in content
    assert "Workday" in content
    assert "Grafana" in content
    assert "Portal BSD" in content

    # 6. Validação da Equipe Completa
    assert "Andre Toshio Uiete Uehara" in content
    assert "Cleber De Souza Gonçalves" in content or "Cleber De Souza Goncalves" in content
    assert "Luiz De Sa Lemos" in content
    assert "ALAN KELVIN CHURA CARRILLO" in content
    assert "RODRIGO DE ALMEIDA MEIRELLES" in content
    assert "Joao Diego Silva Merino" in content

    # 7. Validação do Módulo Streaming Integrado
    assert "allEvents" in content
    assert "PV3623" in content
    assert "PV3687" in content
    assert "PV3679" in content

    # 8. Validação do Módulo de Permissões & RBAC
    assert "allPermissions" in content
    assert "user-role-select" in content
    assert "exportPermsCSV" in content

    # 9. Validação dos arquivos estáticos de download gerados
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_portal = os.path.join(base_dir, "portal_web", "Escala_de_trabalho_2026.xlsx")
    excel_docs = os.path.join(base_dir, "docs", "Escala_de_trabalho_2026.xlsx")
    assert os.path.exists(excel_portal)
    assert os.path.exists(excel_docs)
    assert os.path.getsize(excel_portal) > 100000

    # 10. Validação do CSV de Permissões
    csv_perm = os.path.join(base_dir, "config", "permissoes_google_workspace_suportecaptacao.csv")
    assert os.path.exists(csv_perm)
    assert os.path.getsize(csv_perm) > 500

    # 11. Validação de Sintaxe JavaScript Rigorosa (node -c) e Exposição de Funções de Navegação
    import re
    import subprocess
    import tempfile

    scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
    assert len(scripts) >= 1
    for i, s in enumerate(scripts):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
            tf.write(s)
            tf_path = tf.name
        try:
            res = subprocess.run(["node", "-c", tf_path], capture_output=True, text=True)
            assert res.returncode == 0, f"Erro de sintaxe no script {i}: {res.stderr}"
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    # 12. Validação dos Contêineres de Abas e Funções Globais
    required_panes = [
        "pane-home", "pane-escala", "pane-streaming", "pane-hospedeiros",
        "pane-ocorrencias", "pane-antenistas", "pane-hosts",
        "pane-drive-viewer", "pane-list-viewer", "pane-dashboard",
        "pane-projetos", "pane-receptores", "pane-equipe",
        "pane-permissoes", "pane-links"
    ]
    for pane in required_panes:
        assert f'id="{pane}"' in content, f"Aba obrigatória {pane} não encontrada no HTML"

    assert "window.showPane = showPane;" in content
    assert "window.selectEscalaMonth = selectEscalaMonth;" in content
    assert "window.switchOcoView = switchOcoView;" in content
    assert "window.toggleStatusFilter = toggleStatusFilter;" in content

    # 13. Validação do Painel de Ocorrências 1:1 com SharePoint (13 colunas e views oficiais)
    assert "view-tab-emandamento" in content
    assert "view-tab-recuperacao" in content
    assert "view-tab-operacao" in content
    assert "view-tab-todos" in content
    assert "pill-emandamento" in content
    assert "pill-feedback" in content
    assert "Em recuperação" in content
    assert "GravaçãoStreaming" in content
    assert "Informar Operação" in content
    assert "Ações executadas" in content
    assert "Area/Responsável" in content
    assert "Redmine" in content
    assert "allHosts" in content
    assert "allAntenistas" in content

    # 14. Validação da Programação de Streaming Sincronizada com o SharePoint
    assert "Grêmio x Palmeiras" in content
    assert "Prime Video - PV3687" in content
    assert "streaming-list-title" in content
    assert "864 Confrontos" in content

