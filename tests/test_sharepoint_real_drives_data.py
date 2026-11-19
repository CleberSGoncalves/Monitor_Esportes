import os
import json
import pytest

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "sharepoint_real_drives_data.json")

EXPECTED_DRIVES = [
    "Mapa Campeonatos 2026 SAM",
    "Ficha de Capacitação",
    "Documentos",
    "LogosEmissoras",
    "Tratativa de Problemas de captação",
    "Procedimentos",
    "Avaliação Técnica de Fornecedores",
    "Acesso Remoto",
    "Projetos",
    "Repositorio_Automacoes",
    "Escala de trabalho",
    "Controle de contratos parceiros",
    "Metas",
    "Documentos Técnicos",
    "Análise de Notificações",
    "Relatorio Jogos Youtube",
    "SLA",
    "Redmine_JSON",
    "Analise de Dados",
    "Relatorios_de_Jogos_NBA",
    "Relatorios_de_Jogos"
]

def test_file_exists_and_valid_json():
    assert os.path.exists(CONFIG_PATH), f"Arquivo {CONFIG_PATH} não encontrado!"
    assert os.path.getsize(CONFIG_PATH) > 1000, f"Arquivo {CONFIG_PATH} muito pequeno ou vazio!"
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "site_id" in data
    assert "drives" in data
    assert len(data["drives"]) >= 21, f"Esperado pelo menos 21 drives, encontrado {len(data['drives'])}"

def test_all_expected_drives_present():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    drives_names = [d.get("name") for d in data.get("drives", [])]
    for exp in EXPECTED_DRIVES:
        assert exp in drives_names, f"Drive obrigatório '{exp}' não encontrado nos dados mapeados!"

def test_drive_items_structure():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    total_items = 0
    drives_with_items = 0
    
    for drive in data.get("drives", []):
        assert "drive_id" in drive and drive["drive_id"]
        assert "name" in drive and drive["name"]
        assert "webUrl" in drive and drive["webUrl"]
        assert "items" in drive
        assert isinstance(drive["items"], list)
        
        items = drive["items"]
        total_items += len(items)
        if len(items) > 0:
            drives_with_items += 1
            
        for item in items:
            assert "name" in item and item["name"]
            assert "type" in item and item["type"] in ("file", "folder", "other")
            assert "size" in item
            assert "lastModifiedDateTime" in item
            assert "webUrl" in item
            
            if item["type"] == "folder":
                assert "children" in item
                assert isinstance(item["children"], list)
                for child in item["children"]:
                    assert "name" in child
                    assert "type" in child
                    assert "webUrl" in child
                    
    print(f"\n[Validação] Total de drives: {len(data['drives'])} | Drives com itens: {drives_with_items} | Total itens de raiz: {total_items}")
    assert total_items > 0, "Nenhum item foi mapeado nos drives do SharePoint!"
    assert drives_with_items >= 15, "Menos de 15 drives possuem itens mapeados!"

if __name__ == "__main__":
    test_file_exists_and_valid_json()
    test_all_expected_drives_present()
    test_drive_items_structure()
    print("Todos os testes passaram com sucesso!")
