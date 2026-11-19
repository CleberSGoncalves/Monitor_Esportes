#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes Automatizados para a Integração Google Chat e API REST do Portal Google.
Valida:
1. Geração de Cards v2 do Google Chat com filtro de jogos Hoje e Amanhã.
2. Correspondência exata com o modelo de Agenda de Transmissões do Teams.
3. Execução do script PowerShell de envio.
4. Estrutura do payload de Cards v2 e texto de fallback.
"""

import os
import sys
import json
import subprocess
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.send_google_chat_agenda import (
    carregar_eventos_streaming,
    filtrar_eventos_por_datas,
    montar_payload_google_chat,
    formatar_data_br
)

def test_carregamento_eventos_streaming():
    """Garante que a base de eventos possui registros de streaming migrados."""
    events = carregar_eventos_streaming()
    assert isinstance(events, list)
    assert len(events) >= 800, f"Esperado ao menos 800 eventos, obtido {len(events)}"
    
    first = events[0]
    assert "partida" in first or "Title" in first
    assert "data" in first

def test_filtro_jogos_hoje_e_amanha_screenshot_usuario():
    """
    Testa o filtro usando exatamente a data do print anexado pelo usuário:
    Hoje: 07/11/2026 -> Atlético x Grêmio (17:00, Marcos BL01 e Backup, Prime Video - PV3687)
    Amanhã: 08/11/2026 -> Vasco da Gama x Palmeiras (16:00, Marcos BL01 e Backup, Prime Video - PV3687)
    """
    events = carregar_eventos_streaming()
    hoje_str = "07/11/2026"
    amanha_str = "08/11/2026"
    
    jogos_hoje, jogos_amanha = filtrar_eventos_por_datas(events, hoje_str, amanha_str)
    
    assert len(jogos_hoje) >= 1, "Deveria encontrar ao menos 1 jogo para 07/11/2026"
    assert len(jogos_amanha) >= 1, "Deveria encontrar ao menos 1 jogo para 08/11/2026"
    
    # Validar jogo de hoje
    jogo_hoje = jogos_hoje[0]
    assert "Atletico" in jogo_hoje["partida"] or "Grêmio" in jogo_hoje["partida"] or "Gremio" in jogo_hoje["partida"]
    assert jogo_hoje["horario"] == "17:00"
    assert "Marcos" in jogo_hoje["responsavel"]
    assert "PV3687" in jogo_hoje["pvid"]
    
    # Validar jogo de amanhã
    jogo_amanha = jogos_amanha[0]
    assert "Vasco" in jogo_amanha["partida"] or "Palmeiras" in jogo_amanha["partida"]
    assert jogo_amanha["horario"] == "16:00"
    assert "Marcos" in jogo_amanha["responsavel"]
    assert "PV3687" in jogo_amanha["pvid"]

def test_montagem_payload_google_chat_cards_v2():
    """Valida a estrutura do JSON Cards v2 gerado para o Google Chat."""
    events = carregar_eventos_streaming()
    hoje_str = "07/11/2026"
    amanha_str = "08/11/2026"
    
    jogos_hoje, jogos_amanha = filtrar_eventos_por_datas(events, hoje_str, amanha_str)
    payload = montar_payload_google_chat(hoje_str, jogos_hoje, amanha_str, jogos_amanha)
    
    # Validar campos raiz
    assert "cardsV2" in payload
    assert "text" in payload
    assert len(payload["cardsV2"]) == 1
    
    card_obj = payload["cardsV2"][0]["card"]
    assert card_obj["header"]["title"] == "Agenda de Transmissões"
    assert "hoje e amanhã" in card_obj["header"]["subtitle"].lower()
    
    sections = card_obj["sections"]
    assert len(sections) == 2
    
    # Seção 1 (Hoje)
    sec_hoje = sections[0]
    assert f"Hoje - {hoje_str}" in sec_hoje["header"]
    assert len(sec_hoje["widgets"]) >= 1
    w_hoje = sec_hoje["widgets"][0]["decoratedText"]
    assert "17:00" in w_hoje["topLabel"]
    assert "PV3687" in w_hoje["bottomLabel"]
    
    # Seção 2 (Amanhã)
    sec_amanha = sections[1]
    assert f"Amanhã - {amanha_str}" in sec_amanha["header"]
    assert len(sec_amanha["widgets"]) >= 1
    w_amanha = sec_amanha["widgets"][0]["decoratedText"]
    assert "16:00" in w_amanha["topLabel"]
    assert "PV3687" in w_amanha["bottomLabel"]

def test_powershell_enviar_agenda_script():
    """Valida a execução do script PowerShell em modo simulação."""
    ps_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "enviar_agenda_google_chat.ps1")
    assert os.path.exists(ps_script), "Script PowerShell não encontrado"
    
    cmd = [
        "powershell",
        "-ExecutionPolicy", "Bypass",
        "-File", ps_script,
        "-DataBase", "07/11/2026"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0, f"PowerShell falhou com erro: {res.stderr}"
    assert "AGENDA DE TRANSMISSÕES - GOOGLE CHAT" in res.stdout
    assert "Atletico" in res.stdout or "Grêmio" in res.stdout or "Gremio" in res.stdout
    assert "Vasco da Gama" in res.stdout
    assert "cardsV2" in res.stdout
