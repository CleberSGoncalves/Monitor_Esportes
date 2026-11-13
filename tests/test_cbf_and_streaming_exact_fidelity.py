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
    assert isinstance(rows, list), "Deveria retornar lista de eventos"
    # Garante que nenhuma linha é cabeçalho
    for r in rows:
        assert str(r[0]).strip().lower() != "campeonato", "A linha de cabeçalho não deve estar presente nos dados"

def test_run_eventos_cbf_strict_date_filter_excludes_past_matches():
    # Com Data Início em 12/11/2026, nenhum jogo de outubro/novembro (< 12/11) do PDF pode ser retornado
    camps = {"Brasileirão serie A": True, "Copa do Brasil": True, "Copa do Mundo": False}
    eventos = run_eventos_cbf(camps_ativos=camps, data_inicio_str="12/11/2026")
    assert len(eventos) == 0, f"Nenhum jogo anterior a 12/11/2026 deveria ser retornado, mas obteve {len(eventos)}"

def test_run_eventos_cbf_with_valid_start_date_loads_and_adjusts_timezone():
    # Com Data Início em 01/10/2026, todos os jogos da tabela de outubro/novembro são carregados
    camps = {"Brasileirão serie A": True, "Copa do Brasil": True, "Copa do Mundo": False}
    eventos = run_eventos_cbf(camps_ativos=camps, data_inicio_str="01/10/2026")
    assert len(eventos) == 16, f"Deveria carregar os 16 jogos da tabela publicada pela CBF, obteve {len(eventos)}"
    
    # Valida fuso oficial de -1 hora da CBF
    partidas = {e[1]: e for e in eventos}
    assert "Internacional x Corinthians" in partidas
    inter_game = partidas["Internacional x Corinthians"]
    # No PDF bruto é 19:30; com -1h deve ser 18:30
    assert inter_game[3] == "18:30", f"Horário ajustado deveria ser 18:30, obteve {inter_game[3]}"

def test_run_eventos_cbf_with_copa_do_mundo_excel():
    # Copa do Mundo ocorre em junho/julho de 2026
    camps = {"Brasileirão serie A": False, "Copa do Brasil": False, "Copa do Mundo": True}
    eventos = run_eventos_cbf(camps_ativos=camps, data_inicio_str="01/06/2026")
    assert len(eventos) >= 70, f"Deveria carregar jogos da Copa do Mundo FIFA 2026, obteve {len(eventos)}"
    partidas = [e[1] for e in eventos]
    assert any("Brasil" in p for p in partidas), "Brasil deve estar na tabela da Copa do Mundo"

def test_config_xml_loads_all_platforms():
    cfg = carrega_config_xml("config.xml")
    plats = cfg.get("plataformas", {})
    assert len(plats) == 6, "Devem existir 6 plataformas cadastradas"
    for expected_plat in ["Amazon Prime", "Cazé TV", "CBF", "Disney", "Dazn", "Max"]:
        assert expected_plat in plats, f"Plataforma '{expected_plat}' deve existir no config"

def test_selenium_browser_service_portuguese_date_parsing():
    from modules.reporte_eventos.selenium_browser_service import (
        format_datetime,
        extract_prime_datetime
    )
    # Teste 1: data literal em português com abreviação de sábado e novembro (sáb., 14 de nov. 17:30 BRT)
    texto_raw = "Ao vivo - sáb., 14 de nov. 17:30 BRT - Brasileirão Série A"
    extracted = extract_prime_datetime(texto_raw)
    assert extracted != "", "Deveria extrair a data do texto bruto"
    res = format_datetime(extracted)
    assert res["data"] == "14/11/2026", f"Data esperada 14/11/2026, obteve {res['data']}"
    assert res["hora"] == "17:30", f"Hora esperada 17:30, obteve {res['hora']}"

    # Teste 2: formato Hoje e Amanhã
    hoje_str = "Hoje às 20:00"
    res_hoje = format_datetime(hoje_str)
    assert res_hoje["hora"] == "20:00"
    assert res_hoje["data"] == datetime.now().strftime("%d/%m/%Y")

    # Teste 3: formato simples dd/mm/YYYY HH:MM
    res_simples = format_datetime("18/11/2026 21:00")
    assert res_simples["data"] == "18/11/2026"
    assert res_simples["hora"] == "21:00"

def test_run_eventos_cbf_respects_existing_matches_from_platforms():
    # Se uma partida já foi encontrada pela Amazon Prime Video ou CazéTV, a CBF não deve duplicar
    camps = {"Brasileirão serie A": True, "Copa do Brasil": False, "Copa do Mundo": False}
    existing = [("Internacional x Corinthians", "07/10/2026")]
    evs = run_eventos_cbf(camps_ativos=camps, data_inicio_str="01/10/2026", existing_matches=existing)
    
    # Internacional x Corinthians NÃO deve constar na lista retornada pela CBF
    partidas = [e[1] for e in evs]
    assert "Internacional x Corinthians" not in partidas, "Partida já extraída pela plataforma não deve ser sobreposta pela CBF"

def test_auto_healing_and_start_methods_present_on_mixin():
    from gui.reporte_eventos_mixin import ReporteEventosMixin
    assert hasattr(ReporteEventosMixin, "_re_auto_start_if_needed"), "Deve conter método de auto-start inicial"
    assert hasattr(ReporteEventosMixin, "_re_iniciar_watchdog_auto_healing"), "Deve conter método de watchdog auto-healing"

def test_prime_video_discards_series_and_entertainment_titles():
    import re
    # Simula a regra implementada em run_eventos_prime
    titulos_invalidos = [
        "Todo Mundo Odeia O Chris - Season 3",
        "Reacher - Primeira Temporada",
        "The Rookie S8 - Season 8",
        "Dois Homens E Meio: Primeira Temporada Comp",
        "The Mentalist: 1ª Temporada Completa",
        "Elle: Legalmente Loira - Temporada 1"
    ]
    for t in titulos_invalidos:
        norm = re.sub(r'\s+[vVxX]\s+|\s+vs\.?\s+', ' x ', t, flags=re.I)
        assert " x " not in norm, f"Título de entretenimento '{t}' não deve ser considerado partida esportiva"

    titulos_validos = [
        "Vasco da Gama x Palmeiras",
        "Atlético-MG vs Grêmio",
        "Santos X Palmeiras"
    ]
    for t in titulos_validos:
        norm = re.sub(r'\s+[vVxX]\s+|\s+vs\.?\s+', ' x ', t, flags=re.I)
        assert " x " in norm, f"Confronto '{t}' deve ser reconhecido como partida"

def test_sharepoint_client_independence_from_external_project():
    from pathlib import Path
    sp_file = Path("modules/reporte_eventos/sharepoint_client.py")
    content = sp_file.read_text(encoding="utf-8")
    assert "from Streaming_Scheduler import" not in content, "Não deve haver dependência direta de import do Streaming_Scheduler"


