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

    # 1. Validação de Título e Hero Banner 1:1 SharePoint
    assert "Suporte e Captação" in content
    assert "Bem vindo(a) ao site da equipe de Suporte e Captação!" in content
    assert "São Paulo, Brasil" in content

    # 2. Validação dos 9 Links Úteis do SharePoint
    assert "Links úteis" in content
    assert "Contatos Hospedeiros" in content
    assert "Documentos" in content
    assert "Escala de Trabalho" in content
    assert "Dashboard & Indicadores" in content
    assert "Metas" in content
    assert "Painel de Ocorrências" in content
    assert "Procedimentos N1" in content
    assert "Projetos" in content
    assert "Programação de Eventos Streaming" in content

    # 3. Validação dos CTAs (Teams & Redmine)
    assert "Entre em contato com a nossa equipe" in content
    assert "Enviar uma mensagem" in content
    assert "Sugestões e Demandas" in content
    assert "teams.microsoft.com" in content

    # 4. Validação dos Links Externos (Waffle Layout)
    assert "Links Externos" in content
    assert "Site - Media DNA" in content
    assert "Redmine" in content
    assert "Zabbix" in content
    assert "RH Open" in content
    assert "Service Now" in content
    assert "Workday" in content
    assert "Grafana" in content
    assert "Portal BSD" in content

    # 5. Validação da Equipe Completa (People Web Part)
    assert "CONHEÇA NOSSA EQUIPE" in content
    assert "Administração" in content
    assert "Andre Toshio Uiete Uehara" in content
    assert "andre.uehara@ibope.com" in content
    assert "Gestores" in content
    assert "Cleber De Souza Goncalves" in content
    assert "Luiz De Sa Lemos" in content
    assert "Análise de Dados" in content
    assert "Maria Simone De Santana Matos" in content
    assert "Suporte N1" in content
    assert "ALAN KELVIN CHURA CARRILLO" in content
    assert "Bruno Lopes Viana" in content
    assert "Cleber Rodrigo Gomes" in content
    assert "Suporte N2" in content
    assert "Joao Diego Silva Merino" in content
    assert "Lucieudes Vicente Ferreira" in content
    assert "Marcelo Pereira Silva" in content

    # 6. Validação do Módulo Streaming Integrado (Google Sheets & PVIDs)
    assert "allEvents" in content
    assert "PV3623" in content
    assert "PV3687" in content
    assert "PV3679" in content

    # 7. Validação do Módulo de Permissões & RBAC (SharePoint Graph & Google Sites)
    assert "allPermissions" in content
    assert "Permissões & Controle de Acesso" in content
    assert "user-role-select" in content
    assert "exportPermsCSV" in content
    assert "Proprietários do Suporte Captação" in content
    assert "Visitantes da Suporte Captação" in content

    # 8. Validação do arquivo CSV gerado para Google Workspace
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_perm = os.path.join(base_dir, "config", "permissoes_google_workspace_suportecaptacao.csv")
    assert os.path.exists(csv_perm)
    assert os.path.getsize(csv_perm) > 500
