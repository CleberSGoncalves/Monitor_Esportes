import os
import sys
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.abspath("."))
from modules.sharepoint_youtube_reporter import SharePointYouTubeReporter
from modules.live_channel_monitor import LiveNarrationService
from modules.report_generator import ReportGenerator


def test_sharepoint_youtube_reporter_drive_id():
    """Valida se o Drive ID dedicado para Relatorio Jogos Youtube está configurado."""
    assert SharePointYouTubeReporter._cached_yt_drive_id == "b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuB9cyT1xIdlTLVA1lg-2mHZ"


def test_sharepoint_youtube_reporter_sync_mock(tmp_path):
    """Valida o fluxo completo de upload e envio de metadados para Relatorio Jogos Youtube."""
    fake_pdf = tmp_path / "teste_gremio_live.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 mock content")

    event_info = {
        "match_display": "Grêmio x Atlético-MG",
        "channel_name": "Rádio Gaúcha",
        "competition": "Copa do Brasil",
        "video_url": "https://www.youtube.com/watch?v=hHoSwXKrkZw",
        "live_duration": "02h 45min 00s",
        "score": "Grêmio 2 x 0 Atlético-MG",
        "inicio_transmissao": "17:00:00",
        "apito_inicial": "17:30:00",
        "apito_final": "19:24:00",
        "fim_transmissao": "19:45:00",
        "date": "01/11/2026",
    }

    mock_resp_put = MagicMock()
    mock_resp_put.status_code = 201
    mock_resp_put.json.return_value = {"id": "item_mock_12345"}

    mock_resp_patch = MagicMock()
    mock_resp_patch.status_code = 200
    mock_resp_patch.json.return_value = {"id": "item_mock_12345"}

    with patch("modules.sharepoint_reporter.SharePointReporter.obter_token_graph", return_value="fake_token"), \
         patch("modules.sharepoint_reporter.SharePointReporter.request_with_retry") as mock_req:

        # Simula PUT bem sucedido e PATCH bem sucedido
        mock_req.side_effect = [mock_resp_put, mock_resp_patch]

        ok = SharePointYouTubeReporter.sync_youtube_report(str(fake_pdf), event_info, confianca="99.0%")
        assert ok is True

        # Verifica se o upload foi direcionado para a rota correta do Drive YouTube
        upload_call = mock_req.call_args_list[0]
        assert upload_call[0][0] == "PUT"
        assert SharePointYouTubeReporter._cached_yt_drive_id in upload_call[0][1]

        # Verifica se os metadados canônicos foram enviados no PATCH (idêntico a Relatorios_de_Jogos)
        patch_call = mock_req.call_args_list[1]
        assert patch_call[0][0] == "PATCH"
        payload = patch_call[1]["json"]
        assert payload["Partida"] == "Grêmio x Atlético-MG"
        assert payload["Canal"] == "Gaúcha"
        assert payload["Campeonato"] == "Copa do Brasil"
        assert "Data_Jogo" in payload
        assert payload["Confianca"] == "99.0%"
        assert payload["Auditado"] is True


def test_sharepoint_youtube_reporter_auto_repair(tmp_path):
    """Valida o auto-reparo e resiliência se algum campo ainda não tiver sido criado no SharePoint."""
    fake_pdf = tmp_path / "teste_auto_repair.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 mock content")

    event_info = {
        "match_display": "Palmeiras x Vasco",
        "channel_name": "CazéTV",
        "competition": "Brasileirão Série A",
    }

    mock_resp_put = MagicMock()
    mock_resp_put.status_code = 201
    mock_resp_put.json.return_value = {"id": "item_mock_repair"}

    # 1ª tentativa falha porque campo 'Status' não existe no SharePoint
    mock_resp_patch_err = MagicMock()
    mock_resp_patch_err.status_code = 400
    mock_resp_patch_err.text = "Field 'Status' is not recognized"

    # 2ª tentativa tem sucesso após remover 'Status'
    mock_resp_patch_ok = MagicMock()
    mock_resp_patch_ok.status_code = 200

    with patch("modules.sharepoint_reporter.SharePointReporter.obter_token_graph", return_value="fake_token"), \
         patch("modules.sharepoint_reporter.SharePointReporter.request_with_retry") as mock_req:

        mock_req.side_effect = [mock_resp_put, mock_resp_patch_err, mock_resp_patch_ok]

        ok = SharePointYouTubeReporter.sync_youtube_report(str(fake_pdf), event_info)
        assert ok is True
        assert mock_req.call_count == 3


def test_live_narration_service_sync(tmp_path):
    """Valida se LiveNarrationService.sync_event_to_sharepoint chama o reporter do YouTube."""
    fake_pdf = tmp_path / "narracao_teste.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 mock")

    service = LiveNarrationService(reporter=MagicMock(), config_provider=lambda: {})
    fake_event = {
        "id": "vid_xyz123",
        "channel_name": "GZH",
        "match_display": "Internacional x Fluminense",
        "last_pdf_path": str(fake_pdf)
    }

    with patch.object(service, "get_event", return_value=fake_event), \
         patch("modules.sharepoint_youtube_reporter.SharePointYouTubeReporter.sync_youtube_report", return_value=True) as mock_sync:
        res = service.sync_event_to_sharepoint("vid_xyz123")
        assert res is True
        mock_sync.assert_called_once_with(str(fake_pdf), fake_event)
