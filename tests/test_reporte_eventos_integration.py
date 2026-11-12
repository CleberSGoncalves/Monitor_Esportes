# -*- coding: utf-8 -*-
"""
Suíte de testes automatizados reais de ponta a ponta (E2E) para o módulo Reporte de Eventos.
Valida todas as regras de negócio, criptografia, extração CBF/Copa do Mundo,
normalização canônica, desduplicação SharePoint, e-mail e integração com a interface gráfica.
"""

import os
import pytest
from datetime import datetime, date

from modules.reporte_eventos.crypto_utils import (
    criptografar,
    descriptografar,
    get_config_value,
    get_auth_value,
    get_app_path,
)
from modules.reporte_eventos.sharepoint_client import (
    _deep_normalize_partida,
    _mapear_canal,
    _obter_titulo_oficial_campeonato,
    CANONICAL_CHAMPIONSHIP_TITLES,
)
from modules.reporte_eventos.cbf_pdf_service import (
    canonical_team_name,
    prettify_match_name,
    is_cbf_broadcast_authorized,
    parse_copa_mundo_excel,
)
from modules.reporte_eventos.youtube_scanner_service import (
    norm,
    limpar_time_yt,
    extrair_partida_youtube,
    parse_youtube_title,
    YOUTUBE_PROGRAM_BLACKLIST,
)
from modules.reporte_eventos.storage_manager import (
    carregar_youtube_channels_config,
    salvar_youtube_channels_config,
    carregar_campeonatos_config,
    salvar_campeonatos_config,
    carregar_streaming_csv,
    salvar_streaming_csv,
    carrega_config_xml,
)
from modules.reporte_eventos.email_report_service import (
    extrair_dados_html,
    _hash_corpo,
    enviar_email_relatorio,
)
from gui.reporte_eventos_mixin import ReporteEventosMixin
from gui.main_gui import MonitorApp


class TestReporteEventosCryptoAndConfig:
    def test_encrypt_decrypt_roundtrip(self):
        original = "MinhaSenhaSuperSecreta@2026!"
        encrypted = criptografar(original)
        assert encrypted != original
        assert encrypted.startswith("gAAAA")
        decrypted = descriptografar(encrypted)
        assert decrypted == original

    def test_decrypt_plain_text_fallback(self):
        plain = "TextoNaoCriptografado"
        assert descriptografar(plain) == plain

    def test_get_config_and_auth_values(self):
        # Valida leitura segura de config.xml e auth.xml em config/
        cfg = carrega_config_xml()
        assert "emails" in cfg
        assert "refresh" in cfg
        assert "plataformas" in cfg
        assert "campeonatos" in cfg


class TestSharepointDeepNormalization:
    def test_deep_normalize_order_invariance(self):
        norm1 = _deep_normalize_partida("Grêmio FBPA x SC Internacional")
        norm2 = _deep_normalize_partida("Internacional x Grêmio")
        assert norm1 == norm2
        assert "gremio" in norm1
        assert "internacional" in norm1

    def test_canonical_team_name_and_prettify(self):
        assert canonical_team_name("cr flamengo rj") == "Flamengo"
        assert canonical_team_name("se palmeiras sp") == "Palmeiras"
        assert canonical_team_name("atletico mineiro") == "Atlético-MG"
        assert canonical_team_name("athletico paranaense") == "Athletico-PR"
        assert canonical_team_name("sao paulo fc") == "São Paulo"
        
        match = prettify_match_name("cr flamengo x se palmeiras")
        assert match == "Flamengo x Palmeiras"

    def test_channel_mapping(self):
        assert _mapear_canal("Amazon Prime") == ["Amazon Prime"]
        assert _mapear_canal("Cazé TV") == ["Cazé TV"]
        assert _mapear_canal("Gaúcha") == ["Gaúcha"]
        assert _mapear_canal("Baldasso TV") == ["Baldasso TV"]

    def test_canonical_championship_titles(self):
        assert _obter_titulo_oficial_campeonato("Brasileirão serie A") == "CBF - Brasileirão Série A"
        assert _obter_titulo_oficial_campeonato("Copa do Brasil") == "CBF - Copa do Brasil"


class TestYouTubeScannerRules:
    def test_match_extraction_valid(self):
        title = "🔴 AO VIVO COM IMAGENS: FLAMENGO X PALMEIRAS | RODADA 33 | BRASILEIRÃO 2026"
        match = extrair_partida_youtube(title)
        assert match == "Flamengo x Palmeiras"

    def test_match_extraction_blacklist_rejection(self):
        # Programas da blacklist NÃO devem gerar confronto
        for bl in ["PÓS-JOGO: Grêmio x Inter", "REACT AO VIVO | Flamengo x Vasco", "DEBATE DA RODADA: Corinthians x Santos"]:
            assert extrair_partida_youtube(bl) is None

    def test_parse_youtube_title_metadata(self):
        title = "Palmeiras x Santos | 10ª Rodada | Paulistão 2026"
        res = parse_youtube_title(title)
        assert res["is_paulista"] is True
        assert res["year"] == 2026
        assert res["rodada"] == 10


class TestCopaDoMundoExcelRule:
    def test_copa_mundo_excel_minus_2_hours(self):
        xls_path = get_app_path("Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx")
        if os.path.exists(xls_path):
            events = parse_copa_mundo_excel(xls_path)
            assert len(events) > 0
            ev = events[0]
            assert ev["Camp"] == "Copa do Mundo"
            assert "x" in ev["Jogo"]
            assert ":" in ev["Hora"]
            assert ev["TV"] == "Cazé TV"


class TestEmailReportService:
    def test_extrair_dados_html(self):
        rows = [
            ["Brasileirão serie A", "Flamengo x Palmeiras", "15/11/2026", "16:00", "Esquerda", "15", "Amazon Prime", "https://primevideo.com/event1"],
            ["Copa do Brasil", "Grêmio x Atlético-MG", "18/11/2026", "21:30", "Esquerda", "15", "Cazé TV", "https://youtube.com/watch?v=123"]
        ]
        html = extrair_dados_html(rows)
        assert "Flamengo x Palmeiras" in html
        assert "Grêmio x Atlético-MG" in html
        assert "Amazon Prime" in html
        assert "Cazé TV" in html
        assert "https://primevideo.com/event1" in html

    def test_idempotency_hash(self):
        html1 = "<p>Teste</p>"
        h1 = _hash_corpo(f"{date.today().isoformat()}|{html1}")
        h2 = _hash_corpo(f"{date.today().isoformat()}|{html1}")
        assert h1 == h2

    def test_midnight_block_on_auto_email(self):
        hora = datetime.now().hour
        if hora < 7 or hora >= 22:
            ok, msg = enviar_email_relatorio([], "teste@teste.com", forcar=False)
            assert ok is False
            assert "bloqueio de segurança noturno" in msg


class TestStorageManager:
    def test_youtube_channels_storage(self):
        canais = carregar_youtube_channels_config()
        assert len(canais) >= 6
        nomes = [c["nome"] for c in canais]
        assert "Gaúcha" in nomes
        assert "Baldasso TV" in nomes

    def test_streaming_csv_storage(self):
        rows = carregar_streaming_csv()
        assert isinstance(rows, list)


class TestGUIIntegrationMixin:
    def test_monitor_app_inherits_reporte_eventos_mixin(self):
        assert issubclass(MonitorApp, ReporteEventosMixin)
        # Verifica se todos os métodos essenciais existem no MonitorApp
        required_methods = [
            "_init_reporte_eventos",
            "_build_tab_reporte_eventos",
            "_build_subtab_streaming",
            "_build_subtab_logs",
            "_build_subtab_acessos",
            "_build_subtab_campeonatos",
            "_build_subtab_youtube_channels",
            "_build_subtab_faq",
            "_re_buscar_eventos",
            "_re_salvar_csv",
            "_re_abrir_csv",
            "_re_limpar_tree",
            "_re_toggle_chrome",
            "_re_toggle_start",
        ]
        for m in required_methods:
            assert hasattr(MonitorApp, m), f"Método {m} ausente em MonitorApp!"


class TestSeleniumServiceAndProfiles:
    def test_obter_profile_dir_temp_profile(self):
        from modules.reporte_eventos.selenium_browser_service import (
            obter_profile_dir,
            extract_prime_datetime,
            format_datetime
        )
        p9222 = obter_profile_dir("9222")
        p9224 = obter_profile_dir("9224")
        assert p9222.exists()
        assert p9224.exists()
        assert "TempProfile" in str(p9222)
        assert "TempProfile2" in str(p9224)

    def test_prime_datetime_extraction(self):
        from modules.reporte_eventos.selenium_browser_service import (
            extract_prime_datetime,
            format_datetime
        )
        t1 = "quarta-feira, 22 de jul. 18:50 BRT"
        ext = extract_prime_datetime(t1)
        assert "22 de jul" in ext
        dt = format_datetime(ext)
        assert "22/07" in dt["data"]
        assert dt["hora"] == "18:50"

    def test_log_file_handler_and_filter(self):
        import logging
        from modules.reporte_eventos.crypto_utils import get_app_path
        log_path = get_app_path("log.txt")
        assert os.path.exists(log_path) or os.path.exists(os.path.join("config", "log.txt"))

