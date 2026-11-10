import os
import sys
import pytest
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_report_generator import NBAReportGenerator


def test_nba_streaming_rows_synchronized_with_gamebook():
    """Valida que o Jump Ball e Halftime nas tabelas de Streaming usam os horários reais do Game Book."""
    rep_gen = NBAReportGenerator(os.path.join(PROJECT_ROOT, "reports"))

    fake_game = {
        "id": "test_game_001",
        "away_team": "Boston Celtics",
        "home_team": "Milwaukee Bucks",
        "away_tri": "BOS",
        "home_tri": "MIL",
        "match_display": "Boston Celtics @ Milwaukee Bucks",
        "date_display": "08/11/2026",
        "time_brt": "21:30",
        "platforms": ["Disney+", "ESPN", "NBA League Pass"]
    }

    fake_parsed_gamebook = {
        "score": "113 - 107",
        "game_duration": "2:14",
        "arena": "Fiserv Forum, Milwaukee, WI",
        "attendance": "17.341",
        "officials": ["#25 Tony Brothers", "#58 Josh Tiven"],
        "milestones": [
            {"period": "1º Quarto", "type": "start", "time_brt": "21:40:00", "time_local_str": "6:40 PM"},
            {"period": "1º Quarto", "type": "end", "time_brt": "22:04:00", "time_local_str": "7:04 PM"},
            {"period": "2º Quarto", "type": "start", "time_brt": "22:07:00", "time_local_str": "7:07 PM"},
            {"period": "2º Quarto", "type": "end", "time_brt": "22:36:00", "time_local_str": "7:36 PM"},
            {"period": "3º Quarto", "type": "start", "time_brt": "22:52:00", "time_local_str": "7:52 PM"},
            {"period": "3º Quarto", "type": "end", "time_brt": "23:24:00", "time_local_str": "8:24 PM"},
            {"period": "4º Quarto", "type": "start", "time_brt": "23:27:00", "time_local_str": "8:27 PM"},
            {"period": "4º Quarto", "type": "end", "time_brt": "23:54:00", "time_local_str": "8:54 PM"}
        ]
    }

    pdf_path = rep_gen.generate_report(
        game=fake_game,
        parsed_gamebook=fake_parsed_gamebook,
        auto_generate_proofs=False
    )

    assert os.path.exists(pdf_path), "PDF do relatório não foi gerado!"
    assert os.path.getsize(pdf_path) > 5000, "PDF muito pequeno ou corrompido!"

    import pdfplumber
    with pdfplumber.open(pdf_path) as doc:
        full_text = "\n".join(page.extract_text() or "" for page in doc.pages)
        assert "21:40:00" in full_text, "Horário de Jump Ball real (21:40:00) deve estar registrado!"
        assert "22:36:00" in full_text, "Horário de término do 2T (22:36:00) deve estar registrado!"
        assert "22:52:00" in full_text, "Horário de início do 3T (22:52:00) deve estar registrado!"
        assert "23:54:00" in full_text, "Horário de término do jogo (23:54:00) deve estar registrado!"


def test_no_mock_hardcoded_times_in_streaming():
    """Garante que horários fictícios de mock (ex: 23:30:00 ou 00:30:00) não são inseridos quando o jogo começa em outro horário."""
    rep_gen = NBAReportGenerator(os.path.join(PROJECT_ROOT, "reports"))

    fake_game = {
        "id": "test_game_early",
        "away_team": "Indiana Pacers",
        "home_team": "Charlotte Hornets",
        "away_tri": "IND",
        "home_tri": "CHA",
        "match_display": "Indiana Pacers @ Charlotte Hornets",
        "date_display": "08/11/2026",
        "time_brt": "17:00",
        "platforms": ["Prime Video", "NBA League Pass"]
    }

    fake_parsed = {
        "score": "105 - 100",
        "game_duration": "2:10",
        "milestones": [
            {"period": "1º Quarto", "type": "start", "time_brt": "17:10:00"},
            {"period": "1º Quarto", "type": "end", "time_brt": "17:35:00"},
            {"period": "2º Quarto", "type": "start", "time_brt": "17:38:00"},
            {"period": "2º Quarto", "type": "end", "time_brt": "18:05:00"},
            {"period": "3º Quarto", "type": "start", "time_brt": "18:20:00"},
            {"period": "3º Quarto", "type": "end", "time_brt": "18:50:00"},
            {"period": "4º Quarto", "type": "start", "time_brt": "18:53:00"},
            {"period": "4º Quarto", "type": "end", "time_brt": "19:20:00"}
        ]
    }

    pdf_path = rep_gen.generate_report(
        game=fake_game,
        parsed_gamebook=fake_parsed,
        auto_generate_proofs=False
    )

    import pdfplumber
    with pdfplumber.open(pdf_path) as doc:
        full_text = "\n".join(page.extract_text() or "" for page in doc.pages)
        assert "23:30:00" not in full_text
        assert "00:30:00" not in full_text
        assert "02:00:00" not in full_text
        assert "17:10:00" in full_text
        assert "18:05:00" in full_text
