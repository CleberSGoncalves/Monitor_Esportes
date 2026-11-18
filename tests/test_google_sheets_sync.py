# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch, MagicMock
from modules.reporte_eventos.google_sheets_sync_service import (
    converter_evento_para_schema_google_sheets,
    mapear_pvid_por_canal,
    formatar_data_para_google_sheets,
    sync_events_to_google_sheets,
    request_format_all_google_sheets
)

def test_mapear_pvid_por_canal():
    assert mapear_pvid_por_canal("Cazé TV") == "CAZETV - PV3623"
    assert mapear_pvid_por_canal("Amazon Prime") == "Prime Video - PV3687"
    assert mapear_pvid_por_canal("Netflix") == "Netflix - PV3679"
    assert mapear_pvid_por_canal("SporTV") == "SporTV - PV3101"
    assert mapear_pvid_por_canal("Premiere") == "Premiere - PV3102"
    assert mapear_pvid_por_canal("TNT") == "TNT - 316"
    assert mapear_pvid_por_canal("Outro", "CUSTOM-123") == "CUSTOM-123"

def test_formatar_data_para_google_sheets():
    assert formatar_data_para_google_sheets("2026-11-25T19:00:00Z") == "25/11/2026"
    assert formatar_data_para_google_sheets("25/11/2026") == "25/11/2026"
    assert formatar_data_para_google_sheets("") == ""

def test_converter_evento_para_schema():
    ev = {
        "Partida": "Flamengo x Fluminense",
        "Campeonato": "Carioca",
        "Data": "2026-03-15T18:00:00Z",
        "Horário": "18:00",
        "Canal de Transmissão": "Cazé TV",
        "Responsavel gravação": "Cleber BL01 e Backup",
        "Status de Entrega": "Pendente",
        "Programado": "NÃO"
    }
    conv = converter_evento_para_schema_google_sheets(ev)
    assert conv["partida"] == "Flamengo x Fluminense"
    assert conv["campeonato"] == "Carioca"
    assert conv["data"] == "15/03/2026"
    assert conv["mes"] == "Março"
    assert conv["canal"] == "Cazé TV"
    assert conv["pvid"] == "CAZETV - PV3623"
    assert conv["status"] == "Pendente"
    assert conv["programado"] == "NÃO"

@patch("requests.post")
def test_sync_events_to_google_sheets(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        headers={"Content-Type": "application/json"},
        text='{"status":"success","inseridos":1}',
        json=lambda: {"status": "success", "inseridos": 1}
    )
    res = sync_events_to_google_sheets([{"partida": "Time A x Time B", "canal": "Cazé TV"}], webhook_url="http://fake.test/exec")
    assert res["status"] == "success"
    assert res["inseridos"] == 1

@patch("requests.post")
def test_request_format_all_google_sheets(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        text='{"status":"success","linhas_formatadas":862}',
        json=lambda: {"status": "success", "linhas_formatadas": 862}
    )
    res = request_format_all_google_sheets(webhook_url="http://fake.test/exec")
    assert res["status"] == "success"
    assert res["linhas_formatadas"] == 862
