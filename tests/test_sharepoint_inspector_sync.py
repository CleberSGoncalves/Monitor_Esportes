# -*- coding: utf-8 -*-
"""
Testes Automatizados para o Inspetor Headless de Alterações (SharePoint -> Google).
Valida:
1. Inicialização e resolução de caminhos.
2. Limpeza de campos e remoção de ruídos de metadados do SharePoint.
3. Persistência de estado de sincronização (config/sharepoint_sync_state.json).
4. Algoritmo de detecção de listas e bibliotecas modificadas (dirty detection).
5. Upsert e desduplicação no master data e no painel de ocorrências clean.
6. Ciclo de sincronização de ponta a ponta (E2E).
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_inspector_sync import SharePointInspectorSync, SYSTEM_FIELDS_NOISE


def test_inspector_initialization(tmp_path):
    """Valida inicialização correta com caminhos e sessão HTTP."""
    state_file = str(tmp_path / "test_state.json")
    master_file = str(tmp_path / "test_master.json")

    inspector = SharePointInspectorSync(state_file=state_file, master_data_file=master_file)
    assert inspector.state_file == state_file
    assert inspector.master_data_file == master_file
    assert inspector.session is not None


def test_clean_item_fields():
    """Valida que ruídos técnicos do SharePoint são removidos mantendo dados de negócio."""
    inspector = SharePointInspectorSync()
    raw = {
        "@odata.etag": "etag-1234",
        "_UIVersionString": "2.0",
        "LinkTitle": "Ignorar",
        "Title": "Bundesliga",
        "Partida": "Bayern x Dortmund",
        "Hor_x00e1_rio": "15:30",
        "ItemChildCount": "0"
    }
    cleaned = inspector.clean_item_fields(raw)
    assert "@odata.etag" not in cleaned
    assert "_UIVersionString" not in cleaned
    assert "ItemChildCount" not in cleaned
    assert cleaned["Title"] == "Bundesliga"
    assert cleaned["Partida"] == "Bayern x Dortmund"
    assert cleaned["Hor_x00e1_rio"] == "15:30"


def test_state_load_and_save(tmp_path):
    """Valida leitura e escrita atômica do arquivo de estado."""
    state_file = str(tmp_path / "sharepoint_sync_state.json")
    inspector = SharePointInspectorSync(state_file=state_file)

    # Estado inicial inexistente
    initial_state = inspector.load_state()
    assert initial_state["lists"] == {}
    assert initial_state["drives"] == {}

    # Modificar e salvar
    initial_state["last_scan_utc"] = "2026-11-23T12:00:00Z"
    initial_state["lists"]["Painel de Ocorrências"] = {
        "id": "list-123",
        "last_synced_modified": "2026-11-23T11:50:00Z"
    }
    inspector.save_state(initial_state)

    # Recarregar
    reloaded = inspector.load_state()
    assert reloaded["last_scan_utc"] == "2026-11-23T12:00:00Z"
    assert reloaded["lists"]["Painel de Ocorrências"]["id"] == "list-123"


def test_detect_dirty_entities(tmp_path):
    """Valida se o sensor de metadados detecta corretamente quando uma lista foi modificada."""
    state_file = str(tmp_path / "state.json")
    master_file = str(tmp_path / "master.json")
    inspector = SharePointInspectorSync(state_file=state_file, master_data_file=master_file)

    # Estado existente: última sincronização foi às 10:00
    state = {
        "lists": {
            "Painel de Ocorrências": {
                "id": "list-1",
                "last_synced_modified": "2026-11-23T10:00:00Z"
            },
            "Programação de eventos - Streaming": {
                "id": "list-2",
                "last_synced_modified": "2026-11-23T10:00:00Z"
            }
        },
        "drives": {}
    }

    # Mock do retorno do Graph API: Painel foi modificado às 11:50, Streaming não mudou
    mock_lists_resp = MagicMock()
    mock_lists_resp.status_code = 200
    mock_lists_resp.json.return_value = {
        "value": [
            {
                "id": "list-1",
                "displayName": "Painel de Ocorrências",
                "lastModifiedDateTime": "2026-11-23T11:50:34Z"  # MAIS RECENTE!
            },
            {
                "id": "list-2",
                "displayName": "Programação de eventos - Streaming",
                "lastModifiedDateTime": "2026-11-23T10:00:00Z"  # IGUAL
            }
        ]
    }

    mock_drives_resp = MagicMock()
    mock_drives_resp.status_code = 200
    mock_drives_resp.json.return_value = {"value": []}

    with patch.object(inspector, "_request_graph", side_effect=[mock_lists_resp, mock_drives_resp]):
        res = inspector.inspect_live_changes(state)
        assert res["has_changes"] is True
        assert len(res["changed_lists"]) == 1
        assert res["changed_lists"][0]["displayName"] == "Painel de Ocorrências"
        assert res["changed_lists"][0]["id"] == "list-1"


def test_sync_painel_ocorrencias_clean(tmp_path):
    """Valida transformação e ordenação de ocorrências no painel clean."""
    state_file = str(tmp_path / "state.json")
    master_file = str(tmp_path / "master.json")
    inspector = SharePointInspectorSync(state_file=state_file, master_data_file=master_file)
    inspector.painel_ocorrencias_file = str(tmp_path / "painel_clean.json")

    # Arquivo inicial com 1 item antigo (ID 15500)
    old_items = [{
        "id": "15500",
        "Status": "Concluido",
        "Criado": "2026-11-18T23:40:04Z",
        "hostLookupId": "201",
        "CS": ["01"],
        "Veiculo": "Todos",
        "Equipamento": ["Maquina"],
        "TipoProblema": "Sem comunicação",
        "EmRecuperacao": "Não",
        "GravacaoStreaming": "Não",
        "InformarOperacao": True,
        "AcoesExecutadas": "Antigo",
        "AreaResponsavel": "N1",
        "Redmine": ""
    }]
    with open(inspector.painel_ocorrencias_file, "w", encoding="utf-8") as f:
        json.dump(old_items, f)

    # Novo item recebido do SharePoint (ID 15521)
    raw_sp_items = [{
        "id": "15521",
        "fields": {
            "Problema": "Concluido",
            "Created": "2026-11-22T01:49:50Z",
            "hostLookupId": "97",
            "CS": ["01", "02"],
            "Veiculoo": "Todos",
            "Equipamento": ["Maquina"],
            "Problema0": "Sem comunicação",
            "Emrecupera_x00e7__x00e3_o": "Não",
            "Graca_x00e7__x00e3_o_x0020_por_x": "Não",
            "Informar_x0020_Opera_x00e7__x00e": True,
            "A_x00e7__x00f5_esexecutadas": "Estamos sem comunicação com nossas máquinas.",
            "Area_x002f_Usuarioresponsavel": "N1",
            "Resolucao": "normalizado"
        }
    }]

    inspector._sync_painel_ocorrencias_clean(raw_sp_items)

    with open(inspector.painel_ocorrencias_file, "r", encoding="utf-8") as f:
        updated = json.load(f)

    assert len(updated) == 2
    # ID 15521 deve estar no topo (ordenação decrescente de ID)
    assert updated[0]["id"] == "15521"
    assert updated[0]["Status"] == "Concluido"
    assert updated[0]["hostLookupId"] == "97"
    assert updated[0]["AcoesExecutadas"] == "Estamos sem comunicação com nossas máquinas."
    assert updated[0]["Redmine"] == "normalizado"
    assert updated[1]["id"] == "15500"


def test_upsert_list_items_in_master_data(tmp_path):
    """Valida inserção e atualização de itens no master data sem duplicatas."""
    state_file = str(tmp_path / "state.json")
    master_file = str(tmp_path / "master.json")
    inspector = SharePointInspectorSync(state_file=state_file, master_data_file=master_file)

    # Dados iniciais no master data com 1 item
    initial_master = {
        "lists": {
            "Contatos do Suporte": {
                "displayName": "Contatos do Suporte",
                "name": "Contatos do Suporte",
                "id": "c-1",
                "items_count": 1,
                "items": [{"id": "10", "Title": "Antigo", "Telefone": "1111"}]
            }
        }
    }
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(initial_master, f)

    # Mock de resposta do Graph: Item 10 atualizado e Item 11 novo
    mock_items_resp = MagicMock()
    mock_items_resp.status_code = 200
    mock_items_resp.json.return_value = {
        "value": [
            {"id": "10", "fields": {"Title": "Atualizado", "Telefone": "9999"}},
            {"id": "11", "fields": {"Title": "Novo Contato", "Telefone": "2222"}}
        ]
    }

    with patch.object(inspector, "_request_graph", return_value=mock_items_resp):
        ins, upd = inspector.sync_list_items({
            "id": "c-1",
            "displayName": "Contatos do Suporte",
            "lastModifiedDateTime": "2026-11-23T12:00:00Z"
        })
        assert ins == 1
        assert upd == 1

    with open(master_file, "r", encoding="utf-8") as f:
        master_updated = json.load(f)

    target_items = master_updated["lists"]["Contatos do Suporte"]["items"]
    assert len(target_items) == 2
    # Item 10 deve estar atualizado
    item_10 = next(it for it in target_items if it["id"] == "10")
    assert item_10["Title"] == "Atualizado"
    assert item_10["Telefone"] == "9999"
    # Item 11 inserido
    item_11 = next(it for it in target_items if it["id"] == "11")
    assert item_11["Title"] == "Novo Contato"


def test_end_to_end_sync_cycle(tmp_path):
    """Valida o ciclo completo de sincronização com mock de alterações."""
    state_file = str(tmp_path / "state.json")
    master_file = str(tmp_path / "master.json")
    inspector = SharePointInspectorSync(state_file=state_file, master_data_file=master_file)

    # Mock inspection: lista alterada
    with patch.object(inspector, "inspect_live_changes", return_value={
        "has_changes": True,
        "changed_lists": [{"id": "list-x", "displayName": "Lista Teste", "lastModifiedDateTime": "2026-11-23T12:30:00Z"}],
        "changed_drives": []
    }), patch.object(inspector, "sync_list_items", return_value=(2, 1)), \
       patch.object(inspector, "rebuild_portal_web", return_value=True):

        res = inspector.run_sync_cycle(rebuild=True)
        assert res["has_changes"] is True
        assert res["items_inserted"] == 2
        assert res["items_updated"] == 1
        assert "Lista Teste" in res["lists_synced"]

    # Verificar se o estado foi gravado
    saved_state = inspector.load_state()
    assert "Lista Teste" in saved_state["lists"]
    assert saved_state["lists"]["Lista Teste"]["last_synced_modified"] == "2026-11-23T12:30:00Z"
    assert len(saved_state["sync_history"]) == 1


def test_sync_streaming_clean_upsert_and_patch(tmp_path):
    """Valida o sincronizador de streaming: conversão canônica, inferência de escala e patch bidirecional."""
    state_file = str(tmp_path / "state.json")
    master_file = str(tmp_path / "master.json")
    clean_events_file = str(tmp_path / "sharepoint_clean_migrated_events.json")

    # Base inicial com 1 evento antigo
    initial_events = [
        {
            "id_sharepoint": "100",
            "anexos": "",
            "mes": "Novembro",
            "data": "24/11/2026",
            "horario": "17:00",
            "campeonato": "CBF - Brasileirão Série A",
            "partida": "Chapecoense x Palmeiras",
            "responsavel": "Lucieudes BL01 e Backup",
            "canal": "Cazé TV",
            "pvid": "CAZETV - PV3625",
            "status_entrega": "Pendente",
            "programado": "NÃO",
            "_sort_key": "2026-11-24_17:00"
        }
    ]
    with open(clean_events_file, "w", encoding="utf-8") as f:
        json.dump(initial_events, f)

    inspector = SharePointInspectorSync(state_file=state_file, master_data_file=master_file)
    inspector.clean_migrated_events_file = clean_events_file

    # Item do SharePoint equivalente ao Grêmio x Palmeiras (ID 37731) com campos vazios
    raw_sp_item = {
        "id": "37731",
        "fields": {
            "Title": "CBF - Copa do Brasil",
            "M_x00ea_s": "Dezembro",
            "Data": "2026-12-06T12:00:00Z",
            "Hor_x00e1_rio": "16:00",
            "Partida": "Grêmio x Palmeiras",
            "Transmiss_x00e3_o": ["Amazon Prime"],
            "BKP_x0020__x0028_Uso_x0020_Supor": None,  # Vazio no SharePoint
            "PVID": None,  # Vazio no SharePoint
            "StatusdeEntrega": "Pendente",
            "Programado_x0020_TV_x0020_BOX_x0": "NÂO"
        }
    }

    patch_called = []
    def mock_patch(item_id, responsavel, pvid):
        patch_called.append((item_id, responsavel, pvid))
        return True

    sheets_pushed = []
    def mock_push(events):
        sheets_pushed.extend(events)
        return True

    inspector._patch_sharepoint_item_streaming = mock_patch
    inspector._push_to_google_sheets = mock_push

    ins, upd = inspector._sync_streaming_clean([raw_sp_item])
    assert ins == 1
    assert upd == 0

    # 1. Valida que o SharePoint recebeu o PATCH de enriquecimento
    assert len(patch_called) == 1
    assert patch_called[0][0] == "37731"
    assert patch_called[0][1] == "Cleber BL01 e Backup"
    assert patch_called[0][2] == "Prime Video - PV3687"

    # 2. Valida que foi enviado para o Google Sheets
    assert len(sheets_pushed) == 1
    assert sheets_pushed[0]["partida"] == "Grêmio x Palmeiras"
    assert sheets_pushed[0]["data"] == "06/12/2026"
    assert sheets_pushed[0]["responsavel"] == "Cleber BL01 e Backup"

    # 3. Valida que o dataset local foi atualizado e ordenado
    with open(clean_events_file, "r", encoding="utf-8") as f:
        saved_events = json.load(f)

    assert len(saved_events) == 2
    gremio_ev = next(e for e in saved_events if e["id_sharepoint"] == "37731")
    assert gremio_ev["partida"] == "Grêmio x Palmeiras"
    assert gremio_ev["data"] == "06/12/2026"
    assert gremio_ev["horario"] == "16:00"
    assert gremio_ev["mes"] == "Dezembro"
    assert gremio_ev["responsavel"] == "Cleber BL01 e Backup"
    assert gremio_ev["pvid"] == "Prime Video - PV3687"
    assert gremio_ev["_sort_key"] == "2026-12-06_16:00"

    # Ordem cronológica mantida
    assert saved_events[0]["_sort_key"] == "2026-11-24_17:00"
    assert saved_events[1]["_sort_key"] == "2026-12-06_16:00"

