"""
tests/test_stage_visual_proof_and_grounding.py
Validação automatizada das diretrizes de engenharia:
1. Comprovação visual para CADA etapa da cronologia com carimbo oficial.
2. Presença obrigatória da Seção de Pesquisa Esportiva / Súmula na página final do relatório.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import pytest
from datetime import datetime
from modules.visual_proof_service import generate_chronology_stage_proofs, stamp_audit_banner, get_channel_sigla
from modules.report_generator import ReportGenerator

def test_get_channel_sigla():
    assert get_channel_sigla("Rádio Gaúcha") == "GAU"
    assert get_channel_sigla("CazéTV") == "CZE"
    assert get_channel_sigla("Bagé TV") == "BGE"
    assert get_channel_sigla("Amazon Prime") == "PRM"

def test_generate_chronology_stage_proofs():
    milestones = [
        {"type": "INÍCIO PRÉ-JOGO / TRANSMISSÃO", "time": "17:00:00", "description": "Abertura do sinal"},
        {"type": "APITO INICIAL (1T)", "time": "17:30:00", "description": "Início da partida"},
        {"type": "GOL DO GRÊMIO", "time": "17:51:20", "description": "Gol aos 21 min"},
        {"type": "APITO FINAL", "time": "19:24:00", "description": "Fim da partida"}
    ]
    
    proofs = generate_chronology_stage_proofs(
        video_url_or_id="",
        milestones=milestones,
        date_str="01/11/2026",
        stream_start_dt=datetime(2026, 11, 1, 17, 0, 0),
        praca="SPO",
        channel_name="GAU"
    )
    
    assert len(proofs) == 4
    for i, p in enumerate(proofs):
        assert p["index"] == i + 1
        assert "01/11/2026" in p["timestamp_str"]
        assert os.path.exists(p["image_path"])

def test_report_includes_milestone_proofs_and_grounding():
    milestones = [
        {"type": "INÍCIO PRÉ-JOGO / TRANSMISSÃO", "time": "17:00:00", "description": "Abertura"},
        {"type": "APITO INICIAL (1T)", "time": "17:30:00", "description": "Bola rolando"},
        {"type": "FIM DO 1º TEMPO", "time": "18:18:00", "description": "Intervalo"},
        {"type": "APITO FINAL", "time": "19:24:00", "description": "Apito final"}
    ]
    
    proofs = generate_chronology_stage_proofs(
        video_url_or_id="",
        milestones=milestones,
        date_str="01/11/2026",
        stream_start_dt=datetime(2026, 11, 1, 17, 0, 0),
        praca="SPO",
        channel_name="GAU"
    )
    
    result_data = {
        "match_display": "Grêmio x Atlético-MG",
        "team1": "Grêmio",
        "team2": "Atlético-MG",
        "competition": "Copa do Brasil 2026",
        "date": "01/11/2026",
        "platform": "Rádio Gaúcha",
        "confidence_score": 0.99,
        "report_title": "Relatório Consolidado de Cronologia Técnica (Expert)",
        "report_kind": "narration",
        "duration": "02h 45min 00s",
        "live_start_time": "17:00:00",
        "live_end_time": "19:45:00",
        "technical_milestones": milestones,
        "milestone_proofs": proofs,
        "grounding_verdict": {
            "verdict_text": "CONFIRMAÇÃO OFICIAL DE TRANSMISSÃO & DADOS DE SÚMULA:\n\n• Partida Grêmio x Atlético-MG realizada em 01/11/2026.",
            "references": [{"title": "Súmula CBF", "url": "https://cbf.com.br"}]
        }
    }
    
    reporter = ReportGenerator(reports_dir="reports")
    pdf_p = reporter.write_expert_report([result_data], sync_sharepoint=False, name_prefix="test_multi_stage")
    assert os.path.exists(pdf_p)
    
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf_p)
    assert len(doc) >= 3 # P1 resumo, P2+ visual proofs, P_final grounding
    
    # Valida presença da seção de comprovação técnica visual
    all_text = " ".join([page.get_textpage().get_text_range() for page in doc])
    assert "COMPROVAÇÃO TÉCNICA VISUAL DE CADA ETAPA DA CRONOLOGIA" in all_text
    assert "CONFIRMAÇÃO DE HORÁRIOS NA TRANSMISSÃO OFICIAL & COBERTURA ESPORTIVA" in all_text
