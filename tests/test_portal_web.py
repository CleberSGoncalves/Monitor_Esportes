# -*- coding: utf-8 -*-
import os
import pytest
from scripts.build_portal_web import generate_portal

def test_build_portal_web_creates_file_and_validates_sharepoint_replica_and_rbac():
    html_path = generate_portal()
    assert os.path.exists(html_path)
    assert os.path.getsize(html_path) > 100000

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Validação de Título e Hero Banner 1:1
    assert "Suporte e Captação" in content
    assert "São Paulo, Brasil" in content

    # 2. Validação dos Módulos Nativos Autônomos (Substituição Completa do SharePoint)
    assert "Contatos Hospedeiros" in content
    assert "Painel de Ocorrências" in content
    assert "Procedimentos N1" in content
    assert "Programação de Eventos Streaming" in content
    assert "Receptores & TV BOX" in content
    assert "Equipe & Escala de Plantão" in content

    # 3. Validação dos Dados Nativos Migrados (Hospedeiros & Ocorrências)
    assert "allHospedeiros" in content
    assert "allOcorrencias" in content
    assert "exportHospedeirosCSV" in content
    assert "exportOcorrenciasCSV" in content
    assert "Contatos Técnicos de Hospedeiros" in content
    assert "Painel de Ocorrências & Histórico de Incidentes" in content

    # 4. Validação dos Links Externos
    assert "Links Externos" in content
    assert "Site - Media DNA" in content
    assert "Redmine" in content
    assert "Zabbix" in content
    assert "RH Open" in content
    assert "Service Now" in content
    assert "Workday" in content
    assert "Grafana" in content
    assert "Portal BSD" in content

    # 5. Validação da Equipe Completa
    assert "Andre Toshio Uiete Uehara" in content
    assert "Cleber De Souza Goncalves" in content
    assert "Luiz De Sa Lemos" in content
    assert "Maria Simone De Santana Matos" in content
    assert "ALAN KELVIN CHURA CARRILLO" in content
    assert "Joao Diego Silva Merino" in content

    # 6. Validação do Módulo Streaming Integrado (Google Sheets)
    assert "allEvents" in content
    assert "PV3623" in content
    assert "PV3687" in content
    assert "PV3679" in content

    # 7. Validação do Módulo de Permissões & RBAC
    assert "allPermissions" in content
    assert "user-role-select" in content
    assert "exportPermsCSV" in content
    assert "Proprietários do Suporte Captação" in content
    assert "Visitantes da Suporte Captação" in content

    # 8. Validação do CSV de Permissões
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_perm = os.path.join(base_dir, "config", "permissoes_google_workspace_suportecaptacao.csv")
    assert os.path.exists(csv_perm)
    assert os.path.getsize(csv_perm) > 500
