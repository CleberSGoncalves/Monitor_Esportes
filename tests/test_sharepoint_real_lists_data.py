import os
import json
import pytest

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "sharepoint_real_lists_data.json"
)

EXPECTED_KEY_LISTS = [
    "Cadastro - Hosts",
    "Acesso Remote Control - America Central",
    "Configurações de Rede do CS",
    "data_emissoras_logo",
    "Solicitações de Acesso",
    "Controle de contratos parceiros",
    "Metas",
    "data_emissoras",
    "Documentos Técnicos",
    "Validação de Backup",
    "Confirmação de Falhas Suporte Captação",
    "Mapeamento de Streaming CGD",
    "Programação de eventos - Streaming",
    "Análise de Notificações",
    "Painel de gestão de serviços dos CS",
    "Painel de Ocorrências",
    "Relatorio Jogos Youtube",
    "SLA",
    "Redmine_JSON",
    "Analise de Dados",
    "Relatorios_de_Jogos_NBA",
    "Monitoramento de Canais CS",
    "Redmine",
    "Contatos de Antenistas",
    "Contato Técnico de Hospedeiros"
]

def test_file_exists_and_valid_json():
    assert os.path.exists(CONFIG_PATH), f"Arquivo {CONFIG_PATH} não encontrado!"
    file_size = os.path.getsize(CONFIG_PATH)
    assert file_size > 50000, f"Arquivo {CONFIG_PATH} muito pequeno ({file_size} bytes)!"

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "site_id" in data
    assert "site_url" in data
    assert "extracted_at" in data
    assert "total_lists" in data
    assert "summary" in data
    assert "lists" in data
    assert data["total_lists"] >= 40, f"Esperado >= 40 listas, obtido {data['total_lists']}"
    assert len(data["lists"]) == data["total_lists"]

def test_all_expected_lists_present():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    display_names = {l.get("displayName") for l in data.get("lists", [])}
    names = {l.get("name") for l in data.get("lists", [])}
    all_names = display_names.union(names)

    for exp in EXPECTED_KEY_LISTS:
        assert any(exp in n or n in exp for n in all_names), f"Lista obrigatória '{exp}' não encontrada nos dados mapeados!"

def test_columns_structure():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    lists = data.get("lists", [])
    total_columns = 0

    for l in lists:
        assert "list_id" in l and l["list_id"]
        assert "name" in l and l["name"]
        assert "displayName" in l and l["displayName"]
        assert "columns" in l and isinstance(l["columns"], list)
        assert l["columns_count"] == len(l["columns"])

        for col in l["columns"]:
            assert "name" in col and col["name"]
            assert "displayName" in col
            assert "type" in col
            assert "readOnly" in col
            assert "hidden" in col
            total_columns += 1

    print(f"\n[Validação Colunas] Total de colunas mapeadas em todas as listas: {total_columns}")
    assert total_columns > 200, f"Poucas colunas mapeadas ({total_columns})"

def test_items_and_fields_structure():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    lists = data.get("lists", [])
    total_items = 0
    lists_with_items = 0

    for l in lists:
        assert "items" in l and isinstance(l["items"], list)
        assert l["items_count"] == len(l["items"])
        items = l["items"]
        total_items += len(items)

        if len(items) > 0:
            lists_with_items += 1

        for itm in items:
            assert "id" in itm and itm["id"]
            assert "fields" in itm and isinstance(itm["fields"], dict)

    print(f"\n[Validação Itens] Total de itens mapeados: {total_items} em {lists_with_items} listas ativas.")
    assert total_items >= 500, f"Total de itens ({total_items}) muito baixo!"
    assert lists_with_items >= 35, f"Mínimo de 35 listas com itens esperado, obtido {lists_with_items}"

if __name__ == "__main__":
    test_file_exists_and_valid_json()
    test_all_expected_lists_present()
    test_columns_structure()
    test_items_and_fields_structure()
    print("\nTodos os testes de validação das listas do SharePoint passaram com 100% de sucesso!")
