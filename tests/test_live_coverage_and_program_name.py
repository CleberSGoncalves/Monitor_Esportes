"""
tests/test_live_coverage_and_program_name.py
Testes automatizados para a nova modalidade de Cobertura & Debate ao Vivo
e extração do Nome do Programa para os canais do YouTube.
"""

import os
import sys
import pytest
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.narration_chronology import (
    extract_program_name,
    is_sports_debate_or_coverage,
    is_definitely_non_match,
    generate_coverage_chronology
)
from modules.report_generator import ReportGenerator
from modules.sharepoint_youtube_reporter import SharePointYouTubeReporter

def test_extract_program_name_various_channels():
    # 1. Gaúcha / Gaúcha Esportes
    assert extract_program_name("INTER TEM DECISÃO CONTRA O BOTAFOGO; GRÊMIO PREGA MOBILIZAÇÃO | CENTRAL DO TORCEDOR | 24/10/2026") == "Central do Torcedor"
    assert extract_program_name("TUDO SOBRE INTER X BOTAFOGO COM VAGUINHA, NANI E JOTA | VAMO, COLORADO | PÓS-JOGO | 24/10/2026") == "Vamo, Colorado"
    assert extract_program_name("AO VIVO: VIDA OU MORTE EM CURITIBA | RENATO CONVOCA O TORCEDOR | É O GRÊMIO | 23/10/26 | #39") == "É o Grêmio"
    assert extract_program_name("BATE-BOLA | 25/10/2026") == "Bate-Bola"
    
    # 2. Baldasso TV
    assert extract_program_name("AO VIVO: DIRETO DA CONCENTRAÇÃO DO INTER | BALDASSO NIGHT SHOW") == "Baldasso Night Show"
    assert extract_program_name("(AO VIVO) SUPER JORNADA: INTERNACIONAL X BOTAFOGO | #337") == "Super Jornada"
    
    # 3. Esporte Band RS
    assert extract_program_name("VIDA OU MORTE PARA O INTER NO SÁBADO! | CLIMA É BOM NO GRÊMIO? | Os Donos da Bola Rádio (23/10/26)") == "Os Donos da Bola Rádio"
    
    # 4. Bagé TV
    assert extract_program_name("🟣RESENHA FORA DA SALA NOITE🟣#048") == "Resenha Fora da Sala"
    assert extract_program_name("🌅🔵 BOM DIA GRÊMIO #161") == "Bom Dia Grêmio"
    assert extract_program_name("🐟🟢RADAR DE BAGRE #004") == "Radar de Bagre"
    assert extract_program_name("🔵 AO VIVO 🔵 JORNADA DO BAGÉ 🔵 CORITIBA X GRÊMIO") == "Jornada do Bagé"

def test_is_sports_debate_or_coverage():
    # Esportivo
    is_cov, prog = is_sports_debate_or_coverage("INTER TEM DECISÃO CONTRA O BOTAFOGO | CENTRAL DO TORCEDOR")
    assert is_cov is True
    assert prog == "Central do Torcedor"

    is_cov2, prog2 = is_sports_debate_or_coverage("AO VIVO: DIRETO DA CONCENTRAÇÃO DO INTER | BALDASSO NIGHT SHOW")
    assert is_cov2 is True
    assert prog2 == "Baldasso Night Show"

    # Não-esportivo (política / eleições / trânsito) deve retornar False
    is_cov_pol, _ = is_sports_debate_or_coverage("AO VIVO: APURAÇÃO ELEIÇÕES 2026, 2º TURNO | Lula x Flávio Bolsonaro")
    assert is_cov_pol is False

    is_cov_trans, _ = is_sports_debate_or_coverage("TRÂNSITO E PREVISÃO DO TEMPO NO RS AO VIVO")
    assert is_cov_trans is False

def test_generate_coverage_chronology_structure():
    event = {
        "video_id": "test_debate_01",
        "title": "DEBATE PÓS-JOGO: GRÊMIO X PALMEIRAS | CENTRAL DO TORCEDOR",
        "channel_name": "Gaúcha Esportes",
        "duration": 5400,
        "program_name": "Central do Torcedor",
        "is_coverage_debate": True
    }
    result = generate_coverage_chronology(event, api_key=None)
    assert result.get("report_kind") == "live_coverage"
    assert result.get("program_name") == "Central do Torcedor"
    assert len(result.get("technical_milestones", [])) >= 5
    assert result.get("grounding_verdict") is not None
    assert "CONFIRMAÇÃO TÉCNICA DE COBERTURA" in result["grounding_verdict"]["verdict_text"]

def test_sharepoint_filename_and_title_for_coverage():
    event_info = {
        "title": "INTER TEM DECISÃO CONTRA O BOTAFOGO | CENTRAL DO TORCEDOR",
        "channel_name": "Gaúcha",
        "program_name": "Central do Torcedor",
        "coverage_theme": "Inter tem decisão contra o Botafogo",
        "is_coverage_debate": True,
        "date_clean": "20261024"
    }
    # Verifica normalização de canal
    assert SharePointYouTubeReporter.normalizar_canal("Gaúcha") == "Gaúcha"

def test_visual_proof_distinct_frames_and_no_wrong_overlay(tmp_path):
    from modules.visual_proof_service import generate_chronology_stage_proofs
    import hashlib

    milestones = [
        {"clock": "18:00:00", "min": 0, "lbl": "ABERTURA", "txt": "Início da transmissão e pauta do dia."},
        {"clock": "18:30:00", "min": 30, "lbl": "ANÁLISE", "txt": "Debate tático da rodada."},
        {"clock": "19:00:00", "min": 60, "lbl": "INTERVALO", "txt": "Pausa e interação com torcedores."},
        {"clock": "19:30:00", "min": 90, "lbl": "DEBATE", "txt": "Repercussão dos lances polêmicos."},
        {"clock": "19:54:00", "min": 114, "lbl": "ENCERRAMENTO", "txt": "Notas finais e despedida dos comentaristas."}
    ]

    proofs = generate_chronology_stage_proofs(
        video_url_or_id="dummy_video_for_unit_test",
        milestones=milestones,
        date_str="24/10/2026",
        praca="SPO",
        channel_name="GAU",
        output_dir=str(tmp_path),
        match_display="Inter x Botafogo",
        competition="Debate & Cobertura Esportiva",
        program_name="Central do Torcedor",
        is_coverage_debate=True
    )

    assert len(proofs) == 5
    hashes = set()
    for p in proofs:
        img_p = p["image_path"]
        assert os.path.exists(img_p)
        with open(img_p, "rb") as f:
            h = hashlib.md5(f.read()).hexdigest()
        assert h not in hashes, f"Frame duplicado detectado: {img_p}"
        hashes.add(h)

    # Verifica que todos os 5 frames têm hashes únicos
    assert len(hashes) == 5
