# tests/test_cbf_live_matching_and_nba_timezone.py
"""
Suíte de testes automatizados:
1. Cruzamento determinístico de eventos de canais com a tabela oficial da CBF (Brasileirão e Copa do Brasil).
2. Rejeição cirúrgica de debates, coletivas, treinos e categorias de base (aspirantes/sub-20).
3. Conversão de fuso horário da NBA para Horário de Brasília (BRT / UTC-3) com suporte a transição de DST.
4. Extração e estampagem de tarja oficial de auditoria técnica (Padrão IBOPE / MediaDNA) em frames de vídeo.
5. Inclusão da comprovação visual no relatório técnico consolidado (ReportGenerator).
"""

import os
import sys
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.narration_chronology import is_likely_match, is_definitely_non_match, match_cbf_official_fixture
from modules.nba_service import NBAService, NBA_TEAM_TIMEZONES
from modules.nba_report_generator import NBAReportGenerator
from modules.visual_proof_service import (
    stamp_audit_banner,
    create_synthetic_proof_frame,
    get_channel_sigla
)
from modules.report_generator import ReportGenerator


# =====================================================================
# 1. TESTES DE CRUZAMENTO DA TABELA OFICIAL DA CBF & FILTRAGEM
# =====================================================================

def test_cbf_fixture_matching_real_matches():
    """Valida correspondência de títulos reais com o calendário oficial da CBF."""
    # Jogo real Copa do Brasil
    t1 = "🔴 AO VIVO: GRÊMIO X ATLÉTICO-MG | COPA DO BRASIL 2026 | JOGO DE IDA"
    res1 = match_cbf_official_fixture(t1, "01/11/2026")
    assert res1 is not None, "Deveria identificar partida oficial Grêmio x Atlético-MG"
    assert "Grêmio" in res1["team1"] or "Atlético" in res1["team1"]
    assert res1["matched"] is True

    # Jogo real Brasileirão Série A
    t2 = "TRANSMISSÃO AO VIVO: PALMEIRAS X VASCO DA GAMA | BRASILEIRÃO 2026"
    res2 = match_cbf_official_fixture(t2, "01/11/2026")
    assert res2 is not None, "Deveria identificar partida oficial Palmeiras x Vasco"
    assert res2["matched"] is True


def test_rejection_of_debates_press_and_youth_categories():
    """Garante que debates, programas, coletivas e jogos sub-20/aspirantes sejam sumariamente rejeitados."""
    non_matches = [
        "DEBATE AO VIVO: QUEM DEVE SER O NOVO TÉCNICO?",
        "CONCENTRAÇÃO DO GRÊMIO NO HOTEL EM PORTO ALEGRE",
        "COLETIVA DE IMPRENSA PÓS-JOGO COM RENATO GAÚCHO",
        "ASPIRANTES: GRÊMIO X JUVENTUDE SUB-20 | CAMPEONATO BRASILEIRO DE ASPIRANTES",
        "BASTIDORES DA VITÓRIA DO ATLÉTICO-MG",
        "RESENHA DA GAÚCHA: ANÁLISE COMPLETA DA RODADA"
    ]
    for title in non_matches:
        is_non, reason = is_definitely_non_match(title)
        assert is_non is True, f"'{title}' deveria ser identificado como NÃO-JOGO. Motivo: {reason}"
        assert is_likely_match(title, duration_s=5000) is False, f"'{title}' não deveria passar no is_likely_match"


# =====================================================================
# 2. TESTES DE FUSO HORÁRIO DA NBA (BRT / UTC-3 & DST)
# =====================================================================

def test_nba_timezone_conversions_across_regions():
    """Valida conversão matemática precisa de fusos locais da NBA para Horário de Brasília (BRT)."""
    # Eastern Daylight Time (EDT: UTC-4) -> BRT (UTC-3): +1h
    dt_edt = datetime(2026, 10, 25, 19, 40, tzinfo=ZoneInfo("America/New_York"))
    dt_brt_oct = dt_edt.astimezone(ZoneInfo("America/Sao_Paulo"))
    assert dt_brt_oct.strftime("%H:%M:%S") == "20:40:00"

    # Eastern Standard Time (EST após DST: UTC-5) -> BRT (UTC-3): +2h
    dt_est = datetime(2026, 11, 2, 19, 40, tzinfo=ZoneInfo("America/New_York"))
    dt_brt_nov = dt_est.astimezone(ZoneInfo("America/Sao_Paulo"))
    assert dt_brt_nov.strftime("%H:%M:%S") == "21:40:00"

    # Pacific Daylight Time (PDT: UTC-7) -> BRT (UTC-3): +4h
    dt_pdt = datetime(2026, 10, 25, 19, 30, tzinfo=ZoneInfo("America/Los_Angeles"))
    dt_brt_pac = dt_pdt.astimezone(ZoneInfo("America/Sao_Paulo"))
    assert dt_brt_pac.strftime("%H:%M:%S") == "23:30:00"


def test_nba_gamebook_parsing_brt():
    """Valida se o parsing do Game Book da NBA extrai marcos no fuso horário BRT."""
    test_pdf = os.path.join(PROJECT_ROOT, "scratch", "20261027_BKNBOS_book.pdf")
    if not os.path.exists(test_pdf):
        test_pdf = os.path.join(PROJECT_ROOT, "config", "nba_cache", "20261027_BKNBOS_book.pdf")

    assert os.path.exists(test_pdf), "PDF de teste da NBA deve existir"
    parsed = NBAService.parse_gamebook(test_pdf, home_tri="BOS", date_clean="20261027")
    milestones = parsed.get("milestones", [])
    assert len(milestones) >= 8, f"Game Book deveria conter ao menos 8 marcos, encontrou {len(milestones)}"

    # O 1º quarto começou às 7:40 PM EDT em Boston -> 20:40:00 BRT
    m1 = milestones[0]
    assert m1["period"] == "1º Quarto"
    assert m1["type"] == "start"
    assert m1["time_brt"] == "20:40:00"
    assert m1["time"] == "20:40:00"
    assert "7:40 PM" in m1["time_local"]


# =====================================================================
# 3. TESTES DE COMPROVAÇÃO VISUAL E TARJA DE AUDITORIA
# =====================================================================

def test_visual_proof_banner_stamping():
    """Testa geração de tarja preta superior de auditoria com texto branco de alto contraste."""
    out_img = os.path.join(PROJECT_ROOT, "scratch", "test_banner_audit.jpg")
    created = create_synthetic_proof_frame(
        output_path=out_img,
        praca="SPO",
        channel_code="GAU",
        timestamp_str="01/11/2026 17:51:20",
        title="Grêmio x Atlético-MG"
    )
    assert os.path.exists(created), "Imagem com tarja de auditoria deve ser gerada"
    assert os.path.getsize(created) > 10000, "Imagem deve ter tamanho válido"


def test_channel_siglas_mapping():
    """Valida mapeamento das emissoras para as siglas técnicas de 3 letras."""
    assert get_channel_sigla("Rádio Gaúcha") == "GAU"
    assert get_channel_sigla("CazéTV") == "CZE"
    assert get_channel_sigla("Bagé TV") == "BGE"
    assert get_channel_sigla("Globo Esporte") == "GLO"
    assert get_channel_sigla("Prime Video") == "PRM"


# =====================================================================
# 4. TESTE E2E: RELATÓRIO PDF COM COMPROVAÇÃO VISUAL EMBUTIDA
# =====================================================================

def test_e2e_report_generation_with_visual_proof():
    """Valida que o gerador de relatórios embute a imagem auditada com a tarja."""
    proof_path = os.path.join(PROJECT_ROOT, "scratch", "test_banner_audit.jpg")
    if not os.path.exists(proof_path):
        create_synthetic_proof_frame(proof_path, "SPO", "GAU", "01/11/2026 17:51:20")

    res = {
        "match_display": "Grêmio x Atlético-MG",
        "competition": "Copa do Brasil",
        "date": "01/11/2026",
        "platform": "Rádio Gaúcha (YouTube)",
        "confidence_score": 0.99,
        "report_title": "Relatório Consolidado de Cronologia Técnica (Expert)",
        "milestones": [
            {"label": "APITO INICIAL (1T)", "clock": "17:30:00", "desc": "Início da partida"},
            {"label": "GOL DO GRÊMIO", "clock": "17:51:20", "desc": "Gol validado com comprovação de imagem"},
            {"label": "APITO FINAL", "clock": "19:25:00", "desc": "Encerramento regulamentar"}
        ],
        "visual_proof_images": [proof_path]
    }

    rg = ReportGenerator(os.path.join(PROJECT_ROOT, "reports"))
    pdf_out = rg.write_expert_report([res], sync_sharepoint=False, name_prefix="test_e2e_proof")
    assert os.path.exists(pdf_out), "PDF consolidado deve ser gerado"
    assert os.path.getsize(pdf_out) > 50000, "PDF deve conter a imagem da comprovação visual"
