import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.expert_assistant import ExpertAssistant

def test_calibrate_chronology_milestones():
    # Cenário: cronologia preliminar começou às 17:30, mas o jogo real começou às 18:30
    res = {
        "first_half_start": "17:30:00",
        "match_end": "19:24:00",
        "technical_milestones": [
            {"minute": 0, "type": "INÍCIO PRÉ-JOGO / TRANSMISSÃO", "clock": "17:00:00"},
            {"minute": 26, "type": "HINO NACIONAL E PROTOCOLO", "clock": "17:26:00"},
            {"minute": 0, "type": "APITO INICIAL (1T)", "clock": "17:30:00"},
            {"minute": 21, "type": "GOL DO GRÊMIO (1 x 0)", "clock": "17:51:00"},
            {"minute": 48, "type": "FIM DO 1º TEMPO", "clock": "18:18:00"},
            {"minute": 45, "type": "APITO INICIAL (2T)", "clock": "18:34:00"},
            {"minute": 83, "type": "GOL DO GRÊMIO (2 x 0)", "clock": "19:12:00"},
            {"minute": 95, "type": "APITO FINAL", "clock": "19:24:00"},
            {"minute": 100, "type": "PÓS-JOGO", "clock": "19:35:00"},
            {"minute": 115, "type": "ENCERRAMENTO", "clock": "19:50:00"}
        ]
    }

    # Executa a recalibração com o horário oficial real confirmado (18:30:00 e término 20:24:00)
    ExpertAssistant.calibrate_chronology_milestones(res, official_start="18:30:00", official_end="20:24:00")

    ms = res["technical_milestones"]
    clocks = {m["type"]: m["clock"] for m in ms}

    # Validações estritas dos horários corrigidos:
    assert clocks["INÍCIO PRÉ-JOGO / TRANSMISSÃO"] == "18:00:00"
    assert clocks["HINO NACIONAL E PROTOCOLO"] == "18:26:00"
    assert clocks["APITO INICIAL (1T)"] == "18:30:00"
    assert clocks["GOL DO GRÊMIO (1 x 0)"] == "18:51:00"
    assert clocks["FIM DO 1º TEMPO"] == "19:18:00"
    assert clocks["APITO INICIAL (2T)"] == "19:34:00"
    assert clocks["GOL DO GRÊMIO (2 x 0)"] == "20:12:00"
    assert clocks["APITO FINAL"] == "20:24:00"
    assert clocks["PÓS-JOGO"] == "20:35:00"
    assert clocks["ENCERRAMENTO"] == "20:50:00"
    print("Todos os 10 marcos foram calibrados com precisão cirúrgica para as 18:30!")
