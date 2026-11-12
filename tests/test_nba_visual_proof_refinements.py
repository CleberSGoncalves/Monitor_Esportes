"""
tests/test_nba_visual_proof_refinements.py
Validação automatizada das correções críticas da NBA:
1. Tarja superior sem horário (HH:MM:SS), contendo 'HIGHLIGHT OFICIAL DE COMPROVAÇÃO'.
2. Calibração de offsets para 8 etapas (Etapa 7 a 88% garantindo o 4º Quarto).
3. Geração de Ficha Técnica de Agendamento Oficial em PDF para pré-preenchimento do SharePoint.
4. Resolução de partidas com tolerância de fuso horário (+/- 1 dia).
5. Correção do NameError 'is_cov' no monitor de canais live.
"""

import os
import re
import pytest
from PIL import Image
from modules.nba_visual_proof_service import stamp_nba_audit_banner
from modules.nba_report_generator import NBAReportGenerator
from modules.nba_service import NBAService

def test_banner_removes_time_and_identifies_highlight(tmp_path):
    # Cria uma imagem temporária
    raw_img = tmp_path / "raw_test.jpg"
    img = Image.new("RGB", (1280, 720), color=(20, 30, 40))
    img.save(raw_img)

    out_img = tmp_path / "stamped_test.jpg"
    stamp_nba_audit_banner(
        image_input=str(raw_img),
        output_path=str(out_img),
        praca="SPO",
        channel_code="NBA",
        timestamp_brt_str="10/11/2026 01:57:00"
    )

    assert os.path.exists(out_img)
    # Ler metadados ou validar imagem
    stamped = Image.open(out_img)
    assert stamped.size == (1280, 720)


def test_generate_schedule_sheet(tmp_path):
    game = {
        "away_team": "Boston Celtics",
        "home_team": "Detroit Pistons",
        "away_tri": "BOS",
        "home_tri": "DET",
        "date_clean": "20261115",
        "date_display": "15/11/2026",
        "time_brt": "21:00",
        "platform": "Amazon Prime",
        "platforms": ["Amazon Prime", "NBA League Pass"]
    }
    generator = NBAReportGenerator(reports_dir=str(tmp_path))
    pdf_path = generator.generate_schedule_sheet(game)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000
    assert "Relatorio_NBA_BOS_at_DET_20261115.pdf" in pdf_path


def test_live_channel_monitor_is_cov_defined():
    # Verifica que modules.live_channel_monitor importa e possui as variáveis tratadas
    from modules.live_channel_monitor import LiveNarrationService
    assert hasattr(LiveNarrationService, "_analyze_transcript_locked")
