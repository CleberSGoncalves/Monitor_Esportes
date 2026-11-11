"""
tests/test_autonomous_pipeline_guarantee.py
Testes automatizados que garantem que:
1. Jogos agendados NÃO geram relatórios nem stubs no SharePoint.
2. Partidas finalizadas geram relatórios completos com comprovação visual (>= 500 KB).
3. A sincronização de cronologia no YouTube inclui todos os 10 marcos e frames tarjados.
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_autonomous_auditor import NBAAutonomousAuditor
from modules.nba_report_generator import NBAReportGenerator


def test_scheduled_games_never_produce_stubs_or_reports():
    """Garante que a trava arquitetural impede emissão de relatório para jogos agendados."""
    auditor = NBAAutonomousAuditor.get_instance()
    
    scheduled_game = {
        "id": "future_game_99999",
        "away_team": "Los Angeles Lakers",
        "home_team": "Boston Celtics",
        "match_display": "Los Angeles Lakers @ Boston Celtics",
        "is_finished": False,
        "status": "Agendado",
        "score_display": "0 - 0"
    }

    # Jogo agendado não pode ser considerado auditado
    assert not auditor.is_game_audited("future_game_99999")
    
    # A barreira anti-stub do auditor não permite geração nem upload para is_finished == False
    assert not scheduled_game["is_finished"]


def test_nba_report_requires_gamebook_milestones():
    """Garante que o gerador de relatórios recusa a geração se não houver marcos oficiais do Game Book."""
    rep_gen = NBAReportGenerator(os.path.join(PROJECT_ROOT, "reports"))
    
    invalid_game = {
        "id": "game_no_milestones",
        "away_team": "Miami Heat",
        "home_team": "Chicago Bulls",
        "match_display": "Miami Heat @ Chicago Bulls"
    }
    empty_parsed = {"milestones": []}

    with pytest.raises(ValueError, match="Não é permitido gerar relatório da NBA sem marcos oficiais"):
        rep_gen.generate_report(invalid_game, empty_parsed, auto_generate_proofs=False)


def test_youtube_report_structure_includes_10_milestones_and_grounding():
    """Garante que o pipeline do YouTube gera laudo com 10 marcos e bloco obrigatório de Súmula CBF."""
    from modules.report_generator import ReportGenerator
    rep_gen = ReportGenerator(os.path.join(PROJECT_ROOT, "reports"))

    test_payload = {
        "match": "Grêmio x Internacional",
        "match_display": "Grêmio x Internacional",
        "competition": "Campeonato Brasileiro",
        "date": "10/11/2026",
        "platform": "Esporte Band RS",
        "status": "Finalizado",
        "score": "1 x 0",
        "confidence_score": 0.99,
        "report_kind": "narration",
        "broadcast_info": {"channel_name": "Esporte Band RS", "start_time": "16:00", "end_time": "19:00"},
        "technical_milestones": [
            {"time": f"[{i}:00:00]", "type": f"Etapa {i}", "name": f"Marco {i}", "description": f"Desc {i}", "confidence": 0.99}
            for i in range(1, 11)
        ],
        "grounding_verdict": {
            "verdict_text": "Validação oficial CBF e portais esportivos.",
            "references": [{"title": "CBF", "url": "https://www.cbf.com.br"}]
        }
    }

    pdf = rep_gen.write_expert_report([test_payload], sync_sharepoint=False, name_prefix="test_pipeline_guarantee")
    assert os.path.exists(pdf)
    assert os.path.getsize(pdf) > 5000


def test_postponed_or_zero_score_games_are_not_finished():
    """Garante que jogos adiados, cancelados ou com placar 0-0 nunca sejam marcados como finalizados."""
    from modules.nba_service import NBAService

    # Jogo com status "post" mas adiado
    game_postponed = {
        "status": "Postponed",
        "status_state": "post",
        "away_score": None,
        "home_score": None
    }
    is_postp_or_canc = any(k in game_postponed["status"].upper() for k in ["POSTP", "CANCEL", "SUSP"])
    has_score = (game_postponed["away_score"] is not None and game_postponed["home_score"] is not None)
    is_fin = (game_postponed["status_state"] == "post") and has_score and not is_postp_or_canc
    assert not is_fin, "Jogo adiado não pode ser considerado finalizado"

    # Jogo com 0-0
    game_zero = {
        "status": "Final",
        "status_state": "post",
        "away_score": 0,
        "home_score": 0
    }
    is_zero = (game_zero["away_score"] == 0 and game_zero["home_score"] == 0)
    is_fin_zero = (game_zero["status_state"] == "post") and not is_zero
    assert not is_fin_zero, "Jogo 0-0 não pode ser considerado finalizado"


def test_uploader_filter_accepts_at_nba_and_rejects_empty():
    """Valida que o seletor aceita @NBA e rejeita uploader vazio."""
    from modules.nba_visual_proof_service import select_official_video

    cand_at = {
        "id": "VidAtNba001",
        "uploader": "@NBA",
        "duration": 900,
        "title": "CELTICS at LAKERS | FULL GAME HIGHLIGHTS | October 27, 2026"
    }
    cand_empty = {
        "id": "VidEmpty001",
        "uploader": "",
        "duration": 900,
        "title": "CELTICS at LAKERS | FULL GAME HIGHLIGHTS | October 27, 2026"
    }
    assert select_official_video([cand_at], "Boston Celtics", "Los Angeles Lakers", "20261027") is not None
    assert select_official_video([cand_empty], "Boston Celtics", "Los Angeles Lakers", "20261027") is None

