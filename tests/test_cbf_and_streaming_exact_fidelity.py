# -*- coding: utf-8 -*-
"""
Teste de fidelidade estrita entre Reporte de Eventos e Streaming_Scheduler original:
1. Carregamento inicial de streaming_data.csv / data.csv sem linha de cabeçalho.
2. Extração CBF oficial em 12/11/2026 sem descarte indevido da última rodada publicada.
3. Extração da Copa do Mundo FIFA 2026 via planilha Excel oficial.
4. Padrão de 6/6 plataformas ativas por padrão no config.xml.
"""

import os
import pytest
from datetime import datetime

from modules.reporte_eventos.storage_manager import (
    carregar_streaming_csv,
    salvar_streaming_csv,
    carrega_config_xml
)
from modules.reporte_eventos.cbf_pdf_service import run_eventos_cbf

def test_carregar_streaming_csv_loads_data_and_skips_header():
    rows = carregar_streaming_csv()
    assert len(rows) >= 80, f"Deveria carregar pelo menos 80 eventos da base local, obteve {len(rows)}"
    # Garante que nenhuma linha é cabeçalho
    for r in rows:
        assert str(r[0]).strip().lower() != "campeonato", "A linha de cabeçalho não deve estar presente nos dados"

def test_run_eventos_cbf_with_today_date_preserves_published_rounds():
    # Testa com data de hoje (12/11/2026) onde todos os jogos do PDF da CBF terminaram em 08/11/2026
    camps = {"Brasileirão serie A": True, "Copa do Brasil": True, "Copa do Mundo": False}
    eventos = run_eventos_cbf(camps_ativos=camps, data_inicio_str="12/11/2026")
    assert len(eventos) == 16, f"Deveria carregar os 16 jogos da tabela publicada pela CBF, obteve {len(eventos)}"
    
    # Valida fuso oficial de -1 hora da CBF
    partidas = {e[1]: e for e in eventos}
    assert "Internacional x Corinthians" in partidas
    inter_game = partidas["Internacional x Corinthians"]
    # No PDF bruto é 19:30; com -1h deve ser 18:30
    assert inter_game[3] == "18:30", f"Horário ajustado deveria ser 18:30, obteve {inter_game[3]}"

def test_run_eventos_cbf_with_copa_do_mundo_excel():
    camps = {"Brasileirão serie A": False, "Copa do Brasil": False, "Copa do Mundo": True}
    eventos = run_eventos_cbf(camps_ativos=camps, data_inicio_str="12/11/2026")
    assert len(eventos) >= 70, f"Deveria carregar jogos da Copa do Mundo FIFA 2026, obteve {len(eventos)}"
    partidas = [e[1] for e in eventos]
    assert any("Brasil" in p for p in partidas), "Brasil deve estar na tabela da Copa do Mundo"

def test_config_xml_defaults_all_platforms_active():
    cfg = carrega_config_xml("config.xml")
    plats = cfg.get("plataformas", {})
    assert len(plats) == 6, "Devem existir 6 plataformas cadastradas"
    for p_name, p_active in plats.items():
        assert p_active is True, f"Plataforma '{p_name}' deveria vir ativa (True) por padrão"
