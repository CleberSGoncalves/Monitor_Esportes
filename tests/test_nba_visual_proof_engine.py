"""
tests/test_nba_visual_proof_engine.py
Suíte de Testes Automatizados E2E do Motor de Comprovação Visual e Relatórios da NBA.
Valida:
1. Resolução e mapeamento de siglas dos canais oficiais (NBA, PRM, DIS, ESP).
2. Estampagem correta da tarja de auditoria no topo com fuso de Brasília (BRT).
3. Geração resiliente de frames sintéticos para contingência.
4. Orquestração do motor de comprovação visual com extração e sincronização por etapa.
5. Geração de PDF multi-página contendo a seção de comprovação técnica visual.
"""

import os
import sys
import pytest
from PIL import Image
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

# Injetar root no sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_visual_proof_service import (
    get_nba_channel_sigla,
    stamp_nba_audit_banner,
    create_nba_synthetic_frame,
    NBAVisualProofService
)
from modules.nba_report_generator import NBAReportGenerator


def test_nba_channel_siglas():
    """Valida o mapeamento de canais/plataformas para siglas de 3 letras."""
    assert get_nba_channel_sigla("Amazon Prime Video") == "PRM"
    assert get_nba_channel_sigla("Prime") == "PRM"
    assert get_nba_channel_sigla("Disney+") == "DIS"
    assert get_nba_channel_sigla("ESPN") == "ESP"
    assert get_nba_channel_sigla("NBA League Pass") == "NBA"
    assert get_nba_channel_sigla("NBA") == "NBA"


def test_stamp_nba_audit_banner(tmp_path):
    """Valida a estampagem da tarja oficial com fuso BRT."""
    test_img_path = str(tmp_path / "raw_frame.jpg")
    img = Image.new("RGB", (1280, 720), color=(50, 60, 70))
    img.save(test_img_path)

    out_stamped = str(tmp_path / "stamped_frame.jpg")
    ts_brt = "27/10/2026 20:40:00"
    res_path = stamp_nba_audit_banner(
        test_img_path,
        out_stamped,
        praca="SPO",
        channel_code="NBA",
        timestamp_brt_str=ts_brt,
        extend_top=False
    )

    assert os.path.exists(res_path)
    res_img = Image.open(res_path)
    assert res_img.size == (1280, 720)

    # Verificar que o topo (tarja) é preto (0, 0, 0) nos cantos
    pixel_corner = res_img.getpixel((10, 10))
    assert pixel_corner[0] < 10 and pixel_corner[1] < 10 and pixel_corner[2] < 10


def test_create_nba_synthetic_frame(tmp_path):
    """Valida a criação de frame sintético broadcast para fallback."""
    out_synth = str(tmp_path / "synth_frame.jpg")
    res = create_nba_synthetic_frame(
        out_synth,
        praca="SPO",
        channel_code="PRM",
        timestamp_brt_str="27/10/2026 20:40:00",
        away_team="BKN",
        home_team="BOS",
        score_display="114 - 117",
        period_label="1º Quarto"
    )
    assert os.path.exists(res)
    assert os.path.getsize(res) > 5000
    im = Image.open(res)
    assert im.size == (1280, 720)


def test_nba_visual_proof_orchestrator(tmp_path):
    """Valida a orquestração de comprovação visual para todos os marcos."""
    mock_game = {
        "away_team": "Brooklyn Nets",
        "home_team": "Boston Celtics",
        "away_tri": "BKN",
        "home_tri": "BOS",
        "date_clean": "20261027",
        "date_display": "27/10/2026",
        "score_display": "114 - 117",
        "platform": "NBA League Pass",
        "match_display": "Brooklyn Nets @ Boston Celtics"
    }

    mock_gamebook = {
        "game_duration": "2:46",
        "milestones": [
            {"period": "1º Quarto", "type": "start", "time_brt": "20:40:00", "time_local_str": "7:40 PM (Local)"},
            {"period": "1º Quarto", "type": "end", "time_brt": "21:06:00", "time_local_str": "8:06 PM (Local)"},
            {"period": "2º Quarto", "type": "start", "time_brt": "21:09:00", "time_local_str": "8:09 PM (Local)"},
            {"period": "2º Quarto", "type": "end", "time_brt": "21:40:00", "time_local_str": "8:40 PM (Local)"},
        ]
    }

    proofs = NBAVisualProofService.generate_nba_visual_proofs(
        mock_game,
        mock_gamebook,
        output_dir=str(tmp_path)
    )

    assert len(proofs) == 4
    for idx, p in enumerate(proofs, 1):
        assert p["stage_index"] == idx
        assert os.path.exists(p["image_path"])
        assert "BRT" in p["clock_brt"] or ":" in p["clock_brt"]
        assert p["verification_source"] == "Súmula Oficial NBA (Game Book)"


def test_nba_pdf_report_with_visual_proofs(tmp_path):
    """Valida a compilação do relatório PDF multi-página com seção de comprovação visual."""
    mock_game = {
        "away_team": "Brooklyn Nets",
        "home_team": "Boston Celtics",
        "away_tri": "BKN",
        "home_tri": "BOS",
        "date_clean": "20261027",
        "date_display": "27/10/2026",
        "score_display": "114 - 117",
        "platform": "Amazon Prime",
        "time_brt": "20:40:00",
        "match_display": "Brooklyn Nets @ Boston Celtics"
    }

    mock_gamebook = {
        "game_duration": "2:46",
        "attendance": "19.156",
        "arena": "TD Garden, Boston, MA",
        "officials": ["Scott Foster", "Tony Brothers"],
        "milestones": [
            {"period": "1º Quarto", "type": "start", "time_brt": "20:40:00", "time_local_str": "7:40 PM (Local)"},
            {"period": "1º Quarto", "type": "end", "time_brt": "21:06:00", "time_local_str": "8:06 PM (Local)"},
            {"period": "2º Quarto", "type": "start", "time_brt": "21:09:00", "time_local_str": "8:09 PM (Local)"},
            {"period": "2º Quarto", "type": "end", "time_brt": "21:40:00", "time_local_str": "8:40 PM (Local)"},
        ]
    }

    # Gerar os 4 frames
    proofs = NBAVisualProofService.generate_nba_visual_proofs(
        mock_game,
        mock_gamebook,
        output_dir=str(tmp_path)
    )

    pdf_path = NBAReportGenerator.generate_report(
        mock_game,
        mock_gamebook,
        visual_proofs=proofs,
        auto_generate_proofs=False
    )

    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 10000

    if fitz is not None:
        doc = fitz.open(pdf_path)
        # O PDF deve ter múltiplas páginas (Página 1 executiva + páginas com cards)
        assert len(doc) >= 2
        full_text = " ".join([page.get_text() for page in doc])
        assert "COMPROVAÇÃO TÉCNICA VISUAL" in full_text
        assert "BRT" in full_text
        assert "Game Book" in full_text
        doc.close()
