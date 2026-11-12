# -*- coding: utf-8 -*-
"""
Suíte de Testes Automatizados E2E / Validação de GUI para a aba '📅 Reporte de Eventos'.
Valida de ponta a ponta:
1. Padrão Dark Moderno (#0f172a / #111c2d / #182234 / #00CED1 / #1e293b / #38bdf8).
2. CTkTabview moderno com 6 sub-abas (⚡ Streaming, 📋 Logs, 🔐 Acessos, ⚽ Campeonatos, 📡 Canais YouTube, ❓ FAQ).
3. Dark Treeview (Reporte.Treeview) sem nenhum elemento bege ou branco cru (Win95/XP).
4. Tabela de Campeonatos pré-carregada com 8 campeonatos oficiais e operantes.
5. Tabela de Canais do YouTube pré-carregada com os 6 canais padrão.
6. Busca assíncrona de eventos (_re_buscar_eventos) com scrapers oficiais e run_eventos_cbf sem travar GUI.
7. Todos os botões e ações da interface (_re_toggle_start, _re_add_campeonato, _re_toggle_campeonato, _re_salvar_csv, _re_abrir_csv, _re_limpar_tree / _re_limpar_eventos).
8. Popups modernos de duplo clique (ModernDatePopup, ModernTimePopup, ModernOptionPopup, ModernEditEntryPopup).
9. Integração com a classe MonitorApp.
"""

import os
import sys
import time
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

from gui.reporte_eventos_mixin import (
    ReporteEventosMixin,
    ModernDatePopup,
    ModernTimePopup,
    ModernOptionPopup,
    ModernEditEntryPopup,
)
from gui.main_gui import MonitorApp
from modules.reporte_eventos.storage_manager import (
    DEFAULT_CAMPEONATOS,
    DEFAULT_YOUTUBE_CHANNELS,
    carregar_campeonatos_config,
    carregar_youtube_channels_config,
)


class DummyReporteApp(ReporteEventosMixin, ctk.CTk):
    """Aplicação de teste isolada que inicializa e renderiza o ReporteEventosMixin."""
    def __init__(self):
        super().__init__()
        self.withdraw()  # Não exibe janela no desktop durante teste automatizado
        self.geometry("1200x800")
        self.tab_reporte = ctk.CTkFrame(self, fg_color="#0f172a")
        self.tab_reporte.pack(fill="both", expand=True)
        self._init_reporte_eventos()
        self._build_tab_reporte_eventos()
        self.update()


@pytest.fixture(scope="module")
def app_instance():
    """Cria e encerra a instância de teste do Reporte de Eventos."""
    ctk.set_appearance_mode("Dark")
    app = DummyReporteApp()
    yield app
    try:
        if app.re_loop_job_id:
            try:
                app.after_cancel(app.re_loop_job_id)
            except Exception:
                pass
        app.destroy()
    except Exception:
        pass


class TestReporteEventosTabviewAndDarkTheme:
    """Validação 1: CTkTabview Moderno e Paleta Dark (#0f172a / #182234 / #00CED1)."""

    def test_ctktabview_exists_and_has_6_tabs(self, app_instance):
        assert hasattr(app_instance, "re_subtabs"), "Widget re_subtabs não foi instanciado!"
        assert isinstance(app_instance.re_subtabs, ctk.CTkTabview), "re_subtabs deve ser ctk.CTkTabview!"

        # Abas oficiais exigidas
        expected_tabs = [
            "⚡ Streaming",
            "📋 Logs",
            "🔐 Acessos",
            "⚽ Campeonatos",
            "📡 Canais YouTube",
            "❓ FAQ"
        ]
        loaded_tabs = app_instance.re_subtabs._segmented_button._value_list
        assert len(loaded_tabs) == 6, f"Esperado 6 abas, encontrado {len(loaded_tabs)}: {loaded_tabs}"
        for tab in expected_tabs:
            assert tab in loaded_tabs, f"Sub-aba obrigatória '{tab}' ausente no CTkTabview!"

    def test_dark_palette_and_styling(self, app_instance):
        # Frame mestre dark
        master_fg = app_instance.re_master_frame.cget("fg_color")
        assert master_fg.lower() == "#0f172a", f"Fundo mestre incorreto: {master_fg}"

        # CTkTabview estilo moderno
        tab_fg = app_instance.re_subtabs.cget("fg_color")
        assert tab_fg.lower() in ("#111c2d", "#0f172a"), f"Cor de fundo do Tabview inválida: {tab_fg}"
        
        # Segmented button fg & selected color
        seg_fg = app_instance.re_subtabs._segmented_button.cget("fg_color")
        assert seg_fg.lower() == "#1e293b", f"Segmented button fg incorreto: {seg_fg}"
        seg_sel = app_instance.re_subtabs._segmented_button.cget("selected_color")
        assert seg_sel.lower() == "#00ced1", f"Cor de seleção ciano deve ser #00CED1, obtido: {seg_sel}"

    def test_dark_treeview_style_configuration(self, app_instance):
        style = ttk.Style()
        tv_bg = style.lookup("Reporte.Treeview", "background")
        tv_fg = style.lookup("Reporte.Treeview", "foreground")
        tv_fbg = style.lookup("Reporte.Treeview", "fieldbackground")
        hdr_bg = style.lookup("Reporte.Treeview.Heading", "background")
        hdr_fg = style.lookup("Reporte.Treeview.Heading", "foreground")

        # Verifica se o tema escuro foi injetado (elimina visual cinza/bege Win95)
        assert tv_bg.lower() == "#0f172a", f"Fundo Treeview não é dark #0f172a: {tv_bg}"
        assert tv_fg.lower() == "#f1f5f9", f"Texto Treeview não é claro #f1f5f9: {tv_fg}"
        assert tv_fbg.lower() == "#0f172a", f"Fieldbackground não é dark #0f172a: {tv_fbg}"
        assert hdr_bg.lower() == "#1e293b", f"Cabeçalho Treeview não é dark slate #1e293b: {hdr_bg}"
        assert hdr_fg.lower() == "#38bdf8", f"Texto do cabeçalho não é ciano celeste #38bdf8: {hdr_fg}"

    def test_treeview_row_tags_alternation_dark(self, app_instance):
        even_bg = app_instance.re_tree.tag_configure("even", "background")
        odd_bg = app_instance.re_tree.tag_configure("odd", "background")
        urgent_bg = app_instance.re_tree.tag_configure("urgent", "background")

        assert str(even_bg).lower() == "#142236", f"Tag even deve ser dark azul-petróleo #142236, obtido: {even_bg}"
        assert str(odd_bg).lower() == "#0f172a", f"Tag odd deve ser dark slate profundo #0f172a, obtido: {odd_bg}"
        assert str(urgent_bg).lower() == "#7f1d1d", f"Tag urgent deve ser vermelho dark #7f1d1d, obtido: {urgent_bg}"


class TestCampeonatosPreloadedAndOperations:
    """Validação 2: Campeonatos pré-carregados (8 oficiais) e gestão funcional."""

    def test_campeonatos_table_preloaded_not_empty(self, app_instance):
        app_instance._re_reload_camps_tv()
        children = app_instance.re_tv_camps.get_children()
        assert len(children) >= 8, f"Tabela de campeonatos deve ter no mínimo 8 itens pré-carregados, obtido: {len(children)}"

    def test_all_8_official_championships_registered(self, app_instance):
        children = app_instance.re_tv_camps.get_children()
        titulos_registrados = [str(app_instance.re_tv_camps.item(c, "values")[0]) for c in children]

        padroes = [
            "Brasileirão Série A",
            "Brasileirão Série B",
            "Copa do Brasil",
            "Copa do Mundo FIFA 2026",
            "Mundial de Clubes FIFA",
            "Campeonato Paulista",
            "CONMEBOL Libertadores",
            "CONMEBOL Sudamericana",
        ]
        for padrao in padroes:
            found = any(padrao.lower() in t.lower() for t in titulos_registrados)
            assert found, f"Campeonato oficial '{padrao}' não encontrado na tabela: {titulos_registrados}"

    def test_toggle_campeonato_status(self, app_instance):
        children = app_instance.re_tv_camps.get_children()
        assert len(children) > 0
        first_id = children[0]
        app_instance.re_tv_camps.selection_set(first_id)

        # Status inicial
        val_ini = app_instance.re_tv_camps.item(first_id, "values")
        status_ini = val_ini[3]

        # Alterna status
        app_instance._re_toggle_campeonato()
        children_depois = app_instance.re_tv_camps.get_children()
        val_novo = app_instance.re_tv_camps.item(children_depois[0], "values")
        status_novo = val_novo[3]
        assert status_novo != status_ini, f"Status não alternou: era {status_ini}, permaneceu {status_novo}"

        # Restaura status original
        app_instance.re_tv_camps.selection_set(children_depois[0])
        app_instance._re_toggle_campeonato()
        children_rest = app_instance.re_tv_camps.get_children()
        val_restaurado = app_instance.re_tv_camps.item(children_rest[0], "values")
        assert val_restaurado[3] == status_ini


class TestEventSearchAsyncAndTreeInsertion:
    """Validação 3: Varredura unificada assíncrona com scrapers de streaming e run_eventos_cbf e inserção na grade."""

    def test_inserir_evento_na_grade_and_deduplication(self, app_instance):
        evento = ("Brasileirão serie A", "Flamengo x Palmeiras Teste E2E", "20/11/2026", "20:00", "Esquerda", "15", "Amazon Prime", "https://primevideo.com")
        
        # Insere primeiro
        total_antes = len(app_instance.re_tree.get_children())
        app_instance._re_inserir_evento_na_grade(evento)
        total_depois = len(app_instance.re_tree.get_children())
        assert total_depois == total_antes + 1, "Evento não foi inserido na grade!"

        # Insere duplicado (mesmo confronto e data)
        app_instance._re_inserir_evento_na_grade(evento)
        total_duplicado = len(app_instance.re_tree.get_children())
        assert total_duplicado == total_depois, "Deduplicação falhou: evento duplicado foi inserido!"

    def test_async_event_search_with_platform_scrapers_and_cbf(self, app_instance):
        mock_prime_evs = [
            ("Brasileirão serie A", "Flamengo x Fluminense", "22/11/2026", "16:00", "Esquerda", "10", "Amazon Prime", "https://primevideo.com")
        ]
        mock_cbf_evs = [
            ("CBF - Brasileirão Série A", "Corinthians x São Paulo", "23/11/2026", "16:00", "Direita", "15", "Cazé TV", "https://cbf.com.br")
        ]

        with patch("gui.reporte_eventos_mixin.run_eventos_prime", return_value=mock_prime_evs) as mock_prime, \
             patch("gui.reporte_eventos_mixin.run_eventos_cbf", return_value=mock_cbf_evs) as mock_cbf, \
             patch("gui.reporte_eventos_mixin.obter_eventos_caze_tv", return_value=[]), \
             patch("gui.reporte_eventos_mixin.obter_eventos_canal_youtube", return_value=[]), \
             patch("gui.reporte_eventos_mixin.carregar_campeonatos_config", return_value=[]), \
             patch("gui.reporte_eventos_mixin.carregar_youtube_channels_config", return_value=[]), \
             patch("gui.reporte_eventos_mixin.verificar_chrome_debug", return_value=True), \
             patch("gui.reporte_eventos_mixin.abrir_chrome", return_value=True), \
             patch("gui.reporte_eventos_mixin.fechar_chrome_seguro") as mock_close, \
             patch("gui.reporte_eventos_mixin.messagebox.showinfo") as mock_info:

            # Dispara busca assíncrona
            app_instance._re_buscar_eventos()
            assert app_instance.re_busy is True, "re_busy deve ser True durante a varredura!"
            assert app_instance.re_btn_buscar.cget("state") == "disabled", "Botão Buscar deve estar desabilitado!"

            # Aguarda a conclusão da thread com processamento da fila de eventos Tk
            timeout = 5.0
            start_t = time.time()
            while app_instance.re_busy and (time.time() - start_t) < timeout:
                app_instance.update()
                time.sleep(0.05)

            app_instance.update()
            assert app_instance.re_busy is False, "A busca assíncrona não finalizou no tempo limite!"
            assert app_instance.re_btn_buscar.cget("state") == "normal", "Botão Buscar deve ser reabilitado após a varredura!"

            # Valida presença dos jogos retornados pelas plataformas e CBF
            jogos = [str(app_instance.re_tree.item(item, "values")[1]) for item in app_instance.re_tree.get_children()]
            assert any("Flamengo x Fluminense" in j for j in jogos), f"Jogo Prime Video não encontrado na grade: {jogos}"
            assert any("Corinthians x São Paulo" in j for j in jogos), f"Jogo CBF não encontrado na grade: {jogos}"


class TestControlButtonsAndActions:
    """Validação 4: Resposta funcional de todos os botões e comandos."""

    def test_toggle_start_stop(self, app_instance):
        assert app_instance.re_is_running is False
        assert app_instance.re_btn_start.cget("text") == "▶ Start"

        # Inicia monitoramento
        app_instance._re_toggle_start()
        assert app_instance.re_is_running is True
        assert app_instance.re_btn_start.cget("text") == "⏹ Parar"
        assert app_instance.re_btn_start.cget("fg_color") == "#ef4444"

        # Pausa monitoramento
        app_instance._re_toggle_start()
        assert app_instance.re_is_running is False
        assert app_instance.re_btn_start.cget("text") == "▶ Start"
        assert app_instance.re_btn_start.cget("fg_color") == "#10b981"

    def test_add_and_delete_row(self, app_instance):
        antes = len(app_instance.re_tree.get_children())
        app_instance._re_add_row()
        depois = len(app_instance.re_tree.get_children())
        assert depois == antes + 1, "Linha manual não foi adicionada!"

        # Seleciona e deleta a linha recém-adicionada
        ultima = app_instance.re_tree.get_children()[-1]
        app_instance.re_tree.selection_set(ultima)
        app_instance._re_delete_row()
        assert len(app_instance.re_tree.get_children()) == antes, "Linha não foi deletada!"

    def test_salvar_csv_and_abrir_csv(self, app_instance):
        with patch("gui.reporte_eventos_mixin.salvar_streaming_csv") as mock_salvar, \
             patch("gui.reporte_eventos_mixin.messagebox.showinfo"):
            app_instance._re_salvar_csv()
            assert mock_salvar.called, "salvar_streaming_csv não foi chamado pelo botão!"

        with patch("gui.reporte_eventos_mixin.filedialog.askopenfilename", return_value=""):
            # Cancela diálogo
            app_instance._re_abrir_csv()

    def test_limpar_tree_and_limpar_eventos_alias(self, app_instance):
        app_instance._re_add_row()
        assert len(app_instance.re_tree.get_children()) > 0

        # Testa limpeza confirmada
        with patch("gui.reporte_eventos_mixin.messagebox.askyesno", return_value=True):
            app_instance._re_limpar_tree()
            assert len(app_instance.re_tree.get_children()) == 0, "Grade de eventos não foi limpa!"

            # Testa alias _re_limpar_eventos
            app_instance._re_add_row()
            assert len(app_instance.re_tree.get_children()) > 0
            app_instance._re_limpar_eventos()
            assert len(app_instance.re_tree.get_children()) == 0, "Alias _re_limpar_eventos falhou!"


class TestModernPopups:
    """Validação 5: Popups modernos de duplo clique e edição interativa."""

    def test_modern_date_popup(self, app_instance):
        app_instance._re_add_row()
        row_id = app_instance.re_tree.get_children()[-1]
        popup = ModernDatePopup(app_instance, app_instance.re_tree, row_id, 2, "10/11/2026", 100, 100)
        assert hasattr(popup, "cal")
        popup._confirm()
        val = app_instance.re_tree.item(row_id, "values")[2]
        assert val is not None and len(val) >= 8

    def test_modern_time_popup(self, app_instance):
        row_id = app_instance.re_tree.get_children()[-1]
        popup = ModernTimePopup(app_instance, app_instance.re_tree, row_id, 3, "21:30", 100, 100)
        popup.scale_h.set(20)
        popup._on_slide_h(20)
        popup.scale_m.set(45)
        popup._on_slide_m(45)
        popup._confirm()
        val = app_instance.re_tree.item(row_id, "values")[3]
        assert val == "20:45"

    def test_modern_option_popup(self, app_instance):
        row_id = app_instance.re_tree.get_children()[-1]
        popup = ModernOptionPopup(app_instance, app_instance.re_tree, row_id, 4, "Esquerda", 100, 100, ["Esquerda", "Direita"])
        popup.cbo.set("Direita")
        popup._confirm()
        val = app_instance.re_tree.item(row_id, "values")[4]
        assert val == "Direita"

    def test_modern_edit_entry_popup(self, app_instance):
        row_id = app_instance.re_tree.get_children()[-1]
        popup = ModernEditEntryPopup(app_instance, app_instance.re_tree, row_id, 1, "Antigo", 100, 100)
        popup.entry.delete(0, "end")
        popup.entry.insert(0, "Novo Confronto Editado")
        popup._confirm()
        val = app_instance.re_tree.item(row_id, "values")[1]
        assert val == "Novo Confronto Editado"


class TestYouTubeChannelsPreloadedAndOperations:
    """Validação 6: Canais do YouTube pré-carregados (6 oficiais) e operações."""

    def test_youtube_channels_preloaded(self, app_instance):
        app_instance._re_reload_yt_tv()
        children = app_instance.re_tv_yt.get_children()
        assert len(children) >= 6, f"Esperado ao menos 6 canais padrão, encontrado: {len(children)}"

        nomes = [str(app_instance.re_tv_yt.item(c, "values")[0]) for c in children]
        for padrao in ["Gaúcha", "Gaúcha Esportes", "Atlântida TV", "Baldasso TV", "Bagé TV", "Esporte Band RS"]:
            assert any(padrao.lower() in n.lower() for n in nomes), f"Canal YouTube '{padrao}' não encontrado: {nomes}"

    def test_toggle_youtube_channel_status(self, app_instance):
        children = app_instance.re_tv_yt.get_children()
        first_id = children[0]
        app_instance.re_tv_yt.selection_set(first_id)

        status_ini = app_instance.re_tv_yt.item(first_id, "values")[2]
        app_instance._re_toggle_yt_channel()
        children_depois = app_instance.re_tv_yt.get_children()
        status_novo = app_instance.re_tv_yt.item(children_depois[0], "values")[2]
        assert status_novo != status_ini, "Status do canal YouTube não alternou!"

        # Restaura
        app_instance.re_tv_yt.selection_set(children_depois[0])
        app_instance._re_toggle_yt_channel()
        children_rest = app_instance.re_tv_yt.get_children()
        assert app_instance.re_tv_yt.item(children_rest[0], "values")[2] == status_ini


class TestMonitorAppInheritanceAndIntegration:
    """Validação 7: MonitorApp herda e integra perfeitamente o ReporteEventosMixin."""

    def test_monitor_app_has_all_reporte_methods(self):
        assert issubclass(MonitorApp, ReporteEventosMixin), "MonitorApp deve herdar de ReporteEventosMixin!"
        metodos = [
            "_init_reporte_eventos",
            "_build_tab_reporte_eventos",
            "_setup_dark_treeview_style",
            "_build_modern_subtab_streaming",
            "_build_modern_subtab_logs",
            "_build_modern_subtab_acessos",
            "_build_modern_subtab_campeonatos",
            "_build_modern_subtab_youtube",
            "_build_modern_subtab_faq",
            "_re_buscar_eventos",
            "_re_inserir_evento_na_grade",
            "_re_salvar_csv",
            "_re_abrir_csv",
            "_re_limpar_tree",
            "_re_limpar_eventos",
            "_re_toggle_start",
            "_re_toggle_chrome",
            "_re_atualizar_kpis",
            "_re_abrir_pasta_config",
            "_re_abrir_pasta_perfis_chrome",
            "_re_reload_camps_tv",
            "_re_reload_yt_tv",
            "_re_filtrar_logs",
        ]
        for m in metodos:
            assert hasattr(MonitorApp, m), f"Método {m} não encontrado na classe MonitorApp!"


class TestResponsivenessAndKPIs:
    """Validação 8: Barra de KPIs no padrão Canais Live e layout responsivo dinâmico."""

    def test_kpi_widgets_exist_and_update(self, app_instance):
        assert hasattr(app_instance, "re_kpi_eventos_count"), "KPI de eventos não instanciado!"
        assert hasattr(app_instance, "re_kpi_plat_count"), "KPI de plataformas não instanciado!"
        assert hasattr(app_instance, "re_kpi_chrome_status"), "KPI do Chrome não instanciado!"
        assert hasattr(app_instance, "re_kpi_monitor_status"), "KPI do status não instanciado!"

        # Testa chamada de atualização de KPIs
        app_instance._re_atualizar_kpis()
        assert app_instance.re_kpi_eventos_count.cget("text") is not None
        assert "/" in app_instance.re_kpi_plat_count.cget("text")

    def test_responsive_email_entry_and_treeview(self, app_instance):
        # Entry de e-mail deve ter expansão horizontal para preencher tela
        pack_info = app_instance.re_entry_email.pack_info()
        assert pack_info.get("fill") == "x" or pack_info.get("expand") in (True, "1", 1), "Entry de e-mail deve expandir responsivamente!"

        # Treeview deve ter rowconfigure e columnconfigure com peso
        grid_info = app_instance.re_tree.grid_info()
        assert set(grid_info.get("sticky")) == set("nsew"), f"Treeview deve ter sticky nsew para preencher a grade, obtido: {grid_info.get('sticky')}"

    def test_folder_helpers_exist(self, app_instance):
        assert hasattr(app_instance, "_re_abrir_pasta_config"), "Helper _re_abrir_pasta_config ausente!"
        assert hasattr(app_instance, "_re_abrir_pasta_perfis_chrome"), "Helper _re_abrir_pasta_perfis_chrome ausente!"

    def test_recipient_email_sanitization_and_no_cipher_leak(self, app_instance):
        # O campo de destinatários NUNCA deve conter hash criptografado ou tokens ilegíveis
        val = app_instance.re_email_var.get()
        assert "@" in val, f"Destinatário deve conter endereço de e-mail válido, obtido: {val}"
        assert not val.startswith("gAAAA"), f"Hash Fernet vazou no campo de destinatário: {val}"
        assert not val.startswith("eJG8"), f"Token criptografado vazou no campo de destinatário: {val}"


