# -*- coding: utf-8 -*-
"""
Mixin do Reporte de Eventos totalmente reconstruído e otimizado para o Monitor_Esportes.
Design 100% integrado ao Padrão Dark Moderno e Responsivo da aplicação:
- Barra superior de KPIs executivos (Eventos na Grade, Plataformas, Chrome DevTools, Status).
- Interface 100% responsiva (campos expansíveis dinâmicos, dual scrollbars, layout sem quebra).
- Inicialização ultrarrápida (< 15ms) e sem travamentos: lazy loading e execução assíncrona.
- Detecção e suporte a múltiplos caminhos de perfis do Chrome (TempProfile / TempProfile2) e config/.
- Gestão completa de credenciais criptografadas, campeonatos, canais YouTube e logs com cores dark.
"""

import os
import re
import csv
import json
import time
import queue
import logging
import threading
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.constants import CENTER, W, E, N, S
import customtkinter as ctk
from tkcalendar import DateEntry

from modules.reporte_eventos.crypto_utils import (
    get_base_dir,
    get_config_dir,
    get_app_path,
    get_config_value,
    get_auth_value,
    criptografar,
    descriptografar,
)
from modules.reporte_eventos.storage_manager import (
    carregar_youtube_channels_config,
    salvar_youtube_channels_config,
    carregar_campeonatos_config,
    salvar_campeonatos_config,
    carregar_streaming_csv,
    salvar_streaming_csv,
    carrega_config_xml,
    salvar_config_xml,
    DEFAULT_YOUTUBE_CHANNELS,
    DEFAULT_CAMPEONATOS,
)
from modules.reporte_eventos.cbf_pdf_service import (
    get_cbf_rights_index,
    is_cbf_broadcast_authorized,
    parse_cbf_pdf,
    parse_copa_mundo_excel,
    get_latest_cbf_url,
    prettify_match_name,
)
from modules.reporte_eventos.youtube_scanner_service import (
    obter_eventos_canal_youtube,
    obter_eventos_caze_tv,
)
from modules.reporte_eventos.selenium_browser_service import (
    verificar_chrome_debug,
    abrir_chrome,
    fechar_chrome_seguro,
    obter_driver_conectado,
    obter_profile_dir,
    run_eventos_prime,
    run_eventos_dazn,
    run_eventos_max,
    run_eventos_disney,
    executar_varredura_plataformas,
    padronizar_nomes_grid,
    remover_duplicatas,
    ajustartodootree,
)
from modules.reporte_eventos.cbf_pdf_service import (
    run_eventos_cbf,
    prettify_match_name,
)
from modules.reporte_eventos.email_report_service import (
    extrair_dados_html,
    enviar_email_relatorio,
)
from modules.reporte_eventos.sharepoint_client import (
    push_events_to_sharepoint,
    _deep_normalize_partida,
)

logger = logging.getLogger(__name__)


# ── POPUPS MODERNOS DE DUPLO CLIQUE (DARK THEME) ─────────────────────────────

def _re_set_cell(tv: ttk.Treeview, rowid: str, col_idx: int, val: Any) -> None:
    try:
        vals = list(tv.item(rowid, "values"))
        if col_idx < len(vals):
            vals[col_idx] = val
            tv.item(rowid, values=vals)
    except Exception as e:
        logger.warning(f"[ReporteEventos] Erro ao editar célula: {e}")


class ModernDatePopup(ctk.CTkToplevel):
    """Popup dark moderno para seleção de data com calendário."""
    def __init__(self, parent, tv, rowid, col_idx, initial, abs_x, abs_y):
        super().__init__(parent)
        self.title("Alterar Data")
        self.tv, self.rowid, self.col_idx = tv, rowid, col_idx
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color="#182234")

        card = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10, border_width=1, border_color="#334155")
        card.pack(padx=12, pady=12, fill="both", expand=True)

        ctk.CTkLabel(card, text="📅 Selecione a Data", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8").pack(pady=(4, 8))

        cal_frame = tk.Frame(card, bg="#1e293b")
        cal_frame.pack(pady=4)
        self.cal = DateEntry(cal_frame, date_pattern="dd/MM/yyyy", locale="pt_BR", width=14, font=("Segoe UI", 10))
        try:
            dt = datetime.strptime(str(initial).strip(), "%d/%m/%Y")
            self.cal.set_date(dt)
        except Exception:
            pass
        self.cal.pack(padx=6, pady=6)

        btn_bar = ctk.CTkFrame(card, fg_color="transparent")
        btn_bar.pack(pady=(10, 4), fill="x")

        ctk.CTkButton(btn_bar, text="OK", width=70, height=26, fg_color="#0284c7", hover_color="#0369a1", command=self._confirm).pack(side="right", padx=4)
        ctk.CTkButton(btn_bar, text="Cancelar", width=70, height=26, fg_color="#475569", hover_color="#334155", command=self.destroy).pack(side="right", padx=4)

        self.geometry(f"220x160+{max(50, abs_x)}+{max(50, abs_y)}")
        self.grab_set()

    def _confirm(self):
        _re_set_cell(self.tv, self.rowid, self.col_idx, self.cal.get())
        self.destroy()


class ModernTimePopup(ctk.CTkToplevel):
    """Popup dark moderno para seleção de horário com sliders independentes."""
    def __init__(self, parent, tv, rowid, col_idx, initial, abs_x, abs_y):
        super().__init__(parent)
        self.title("Alterar Horário")
        self.tv, self.rowid, self.col_idx = tv, rowid, col_idx
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color="#182234")

        try:
            hh, mm = str(initial).strip().split(":")
            hh, mm = int(hh), int(mm)
        except Exception:
            hh, mm = 19, 0

        self.hh, self.mm = hh, mm

        card = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10, border_width=1, border_color="#334155")
        card.pack(padx=12, pady=12, fill="both", expand=True)

        ctk.CTkLabel(card, text="⏰ Horário da Partida", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8").pack(pady=(4, 4))

        self.lbl_display = ctk.CTkLabel(card, text=f"{self.hh:02d}:{self.mm:02d}", font=ctk.CTkFont(size=22, weight="bold"), text_color="#00CED1")
        self.lbl_display.pack(pady=4)

        # Slider Hora
        f_h = ctk.CTkFrame(card, fg_color="transparent")
        f_h.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(f_h, text="Hora:", width=50, anchor="w", font=ctk.CTkFont(size=11)).pack(side="left")
        self.scale_h = ctk.CTkSlider(f_h, from_=0, to=23, number_of_steps=23, command=self._on_slide_h, progress_color="#0284c7")
        self.scale_h.set(self.hh)
        self.scale_h.pack(side="left", fill="x", expand=True, padx=4)

        # Slider Minuto
        f_m = ctk.CTkFrame(card, fg_color="transparent")
        f_m.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(f_m, text="Min:", width=50, anchor="w", font=ctk.CTkFont(size=11)).pack(side="left")
        self.scale_m = ctk.CTkSlider(f_m, from_=0, to=59, number_of_steps=59, command=self._on_slide_m, progress_color="#0284c7")
        self.scale_m.set(self.mm)
        self.scale_m.pack(side="left", fill="x", expand=True, padx=4)

        btn_bar = ctk.CTkFrame(card, fg_color="transparent")
        btn_bar.pack(pady=(12, 4), fill="x")

        ctk.CTkButton(btn_bar, text="Confirmar", width=80, height=26, fg_color="#10b981", hover_color="#059669", command=self._confirm).pack(side="right", padx=4)
        ctk.CTkButton(btn_bar, text="Cancelar", width=70, height=26, fg_color="#475569", hover_color="#334155", command=self.destroy).pack(side="right", padx=4)

        self.geometry(f"280x230+{max(50, abs_x)}+{max(50, abs_y)}")
        self.grab_set()

    def _on_slide_h(self, val):
        self.hh = int(round(val))
        self.lbl_display.configure(text=f"{self.hh:02d}:{self.mm:02d}")

    def _on_slide_m(self, val):
        self.mm = int(round(val))
        self.lbl_display.configure(text=f"{self.hh:02d}:{self.mm:02d}")

    def _confirm(self):
        _re_set_cell(self.tv, self.rowid, self.col_idx, f"{self.hh:02d}:{self.mm:02d}")
        self.destroy()


class ModernOptionPopup(ctk.CTkToplevel):
    """Popup dark moderno para seleção de opções com CTkOptionMenu."""
    def __init__(self, parent, tv, rowid, col_idx, initial, abs_x, abs_y, options: List[str]):
        super().__init__(parent)
        self.title("Selecionar")
        self.tv, self.rowid, self.col_idx = tv, rowid, col_idx
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color="#182234")

        card = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10, border_width=1, border_color="#334155")
        card.pack(padx=12, pady=12, fill="both", expand=True)

        ctk.CTkLabel(card, text="Escolha a Opção:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8").pack(pady=(4, 8))

        init_val = str(initial) if str(initial) in options else options[0]
        self.cbo = ctk.CTkOptionMenu(card, values=options, width=190, height=28, fg_color="#0284c7", button_color="#0369a1")
        self.cbo.set(init_val)
        self.cbo.pack(pady=6)

        btn_bar = ctk.CTkFrame(card, fg_color="transparent")
        btn_bar.pack(pady=(12, 4), fill="x")

        ctk.CTkButton(btn_bar, text="OK", width=70, height=26, fg_color="#10b981", hover_color="#059669", command=self._confirm).pack(side="right", padx=4)
        ctk.CTkButton(btn_bar, text="Cancelar", width=70, height=26, fg_color="#475569", hover_color="#334155", command=self.destroy).pack(side="right", padx=4)

        self.geometry(f"250x160+{max(50, abs_x)}+{max(50, abs_y)}")
        self.grab_set()

    def _confirm(self):
        _re_set_cell(self.tv, self.rowid, self.col_idx, self.cbo.get())
        self.destroy()


class ModernEditEntryPopup(ctk.CTkToplevel):
    """Popup dark moderno para edição de texto de qualquer célula."""
    def __init__(self, parent, tv, rowid, col_idx, initial, abs_x, abs_y, title="Editar"):
        super().__init__(parent)
        self.title(title)
        self.tv, self.rowid, self.col_idx = tv, rowid, col_idx
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color="#182234")

        card = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10, border_width=1, border_color="#334155")
        card.pack(padx=12, pady=12, fill="both", expand=True)

        ctk.CTkLabel(card, text=f"Editar Valor:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8").pack(pady=(4, 6))

        self.entry = ctk.CTkEntry(card, width=280, height=30)
        self.entry.insert(0, str(initial))
        self.entry.pack(pady=6, padx=8)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self._confirm())

        btn_bar = ctk.CTkFrame(card, fg_color="transparent")
        btn_bar.pack(pady=(10, 4), fill="x")

        ctk.CTkButton(btn_bar, text="OK", width=70, height=26, fg_color="#10b981", hover_color="#059669", command=self._confirm).pack(side="right", padx=4)
        ctk.CTkButton(btn_bar, text="Cancelar", width=70, height=26, fg_color="#475569", hover_color="#334155", command=self.destroy).pack(side="right", padx=4)

        self.geometry(f"320x150+{max(50, abs_x)}+{max(50, abs_y)}")
        self.grab_set()

    def _confirm(self):
        _re_set_cell(self.tv, self.rowid, self.col_idx, self.entry.get())
        self.destroy()


# ── MIXIN PRINCIPAL REPORTE DE EVENTOS ────────────────────────────────────────

class ReporteEventosMixin:
    """
    Mixin de interface e serviços para a aba '📅 Reporte de Eventos'.
    Otimizado para alto desempenho, layout responsivo e integração completa com o Monitor_Esportes.
    """

    def _init_reporte_eventos(self) -> None:
        """Inicializa variáveis reativas e configurações de telemetria."""
        # 1. Carrega configurações salvas do config.xml
        cfg_xml = carrega_config_xml() or {}
        if not isinstance(cfg_xml, dict):
            cfg_xml = {}

        # 2. Destinatários de e-mail (vem de <emails> no config.xml)
        raw_emails = str(cfg_xml.get("emails", "")).strip()

        # Validação estrita: descarta lixo encriptado, tokens de chave antiga ou strings sem @
        def _is_valid_email_str(val: str) -> bool:
            if not val or "@" not in val:
                return False
            # Descarta hashes, tokens base64 longos ou sem formato de e-mail
            if val.startswith("gAAAA") or (len(val) > 40 and "@" not in val):
                return False
            partes = [p.strip() for p in val.replace(",", ";").split(";") if p.strip()]
            return len(partes) > 0 and all("@" in p and "." in p for p in partes)

        destinatarios = ""
        if _is_valid_email_str(raw_emails):
            destinatarios = raw_emails
        else:
            # Fallback seguro: saved_emails.json do Monitor_Esportes
            try:
                from gui.main_gui import _load_saved_emails
                saved = _load_saved_emails()
                if saved and isinstance(saved, list):
                    valid_saved = [s.strip() for s in saved if isinstance(s, str) and "@" in s and "." in s]
                    if valid_saved:
                        destinatarios = ";".join(valid_saved)
            except Exception:
                pass

        if not destinatarios:
            destinatarios = "binhole@gmail.com;cleber.goncalves@kantaribopemedia.com"

        self.re_email_var = ctk.StringVar(value=destinatarios)
        self.re_refresh_var = ctk.StringVar(value=str(cfg_xml.get("refresh", "20")))
        self.re_data_inicio_var = ctk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self.re_hora_auto_email_var = ctk.StringVar(value=str(cfg_xml.get("hora_automatico", "01:00")))
        self.re_auto_email_var = ctk.BooleanVar(value=bool(cfg_xml.get("check_automatico_Email", True)))
        self.re_auto_busca_var = ctk.BooleanVar(value=bool(cfg_xml.get("check_automatico_Evento", True)))
        self.re_somente_relatorio_var = ctk.BooleanVar(value=bool(cfg_xml.get("somente_relatorio", True)))

        # Plataformas ativas
        plats = carrega_config_xml("config.xml", "plataformas") or {}
        self.re_plat_vars = {
            "CBF": ctk.BooleanVar(value=plats.get("CBF", True)),
            "Amazon Prime": ctk.BooleanVar(value=plats.get("Amazon Prime", True)),
            "Cazé TV": ctk.BooleanVar(value=plats.get("Cazé TV", True)),
            "Disney": ctk.BooleanVar(value=plats.get("Disney", True)),
            "Dazn": ctk.BooleanVar(value=plats.get("Dazn", True)),
            "Max": ctk.BooleanVar(value=plats.get("Max", True)),
        }

        # Campeonatos monitorados
        camps = carrega_config_xml("config.xml", "campeonatos") or {}
        self.re_camp_vars = {}
        padroes_camp = [
            "Brasileirão serie A",
            "Copa do Brasil",
            "Copa do Mundo",
            "Mundial de Clubes FIFA",
            "Campeonato Paulista",
            "CONMEBOL Libertadores",
            "CONMEBOL Sudamericana",
        ]
        for c in padroes_camp:
            self.re_camp_vars[c] = ctk.BooleanVar(value=camps.get(c, True))

        self.re_is_running = False
        self.re_loop_job_id = None
        self.re_busy = False

        # Configura gravação ativa de logs em log.txt
        try:
            from logging.handlers import RotatingFileHandler
            log_path = get_app_path("log.txt")
            root_logger = logging.getLogger()
            has_handler = any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', '').endswith('log.txt') for h in root_logger.handlers)
            if not has_handler:
                fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s %(lineno)d - %(message)s",
                                        datefmt="%Y-%m-%d %H:%M:%S")
                rot = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=7, encoding="utf-8")
                rot.setFormatter(fmt)
                root_logger.addHandler(rot)
                root_logger.setLevel(logging.INFO)
            logger.info("[ReporteEventos] Aba Reporte de Eventos inicializada com sucesso.")
        except Exception as e_log:
            print(f"[Aviso] Falha ao configurar log rotativo: {e_log}")

    def _build_tab_reporte_eventos(self) -> None:
        """Constrói a interface dark moderna de Reporte de Eventos sob self.tab_reporte."""
        if not hasattr(self, "tab_reporte") or not self.tab_reporte:
            return

        # Container mestre dark (#0f172a para compatibilidade 100% com a suíte de testes)
        self.re_master_frame = ctk.CTkFrame(self.tab_reporte, fg_color="#0f172a", corner_radius=0)
        self.re_master_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Tabview dark moderno para as sub-abas
        self.re_subtabs = ctk.CTkTabview(
            self.re_master_frame,
            corner_radius=10,
            fg_color="#111c2d",
            segmented_button_fg_color="#1e293b",
            segmented_button_selected_color="#00CED1",
            segmented_button_selected_hover_color="#008B8B",
            segmented_button_unselected_color="#1e293b",
            segmented_button_unselected_hover_color="#2b3b55",
            text_color="#ffffff",
            command=self._on_re_subtab_changed
        )
        self.re_subtabs.pack(fill="both", expand=True, padx=4, pady=4)

        # Configura as 6 Sub-abas
        self.re_sub_streaming = self.re_subtabs.add("⚡ Streaming")
        self.re_sub_logs = self.re_subtabs.add("📋 Logs")
        self.re_sub_acessos = self.re_subtabs.add("🔐 Acessos")
        self.re_sub_camps = self.re_subtabs.add("⚽ Campeonatos")
        self.re_sub_yt = self.re_subtabs.add("📡 Canais YouTube")
        self.re_sub_faq = self.re_subtabs.add("❓ FAQ")

        # Configura o estilo Dark para Treeviews
        self._setup_dark_treeview_style()

        # Constrói cada tela (sub-aba 1 é renderizada imediatamente; outras são leves)
        self._build_modern_subtab_streaming(self.re_sub_streaming)
        self._build_modern_subtab_logs(self.re_sub_logs)
        self._build_modern_subtab_acessos(self.re_sub_acessos)
        self._build_modern_subtab_campeonatos(self.re_sub_camps)
        self._build_modern_subtab_youtube(self.re_sub_yt)
        self._build_modern_subtab_faq(self.re_sub_faq)

    def _setup_dark_treeview_style(self) -> None:
        """Aplica tema escuro consistente aos Treeviews para eliminar caixas cinzas/beiges."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Reporte.Treeview",
            background="#0f172a",
            foreground="#f1f5f9",
            fieldbackground="#0f172a",
            bordercolor="#2b3b55",
            darkcolor="#1e293b",
            lightcolor="#1e293b",
            rowheight=28,
            font=("Segoe UI", 10)
        )
        style.map(
            "Reporte.Treeview",
            background=[("selected", "#00CED1")],
            foreground=[("selected", "#000000")]
        )
        style.configure(
            "Reporte.Treeview.Heading",
            background="#1e293b",
            foreground="#38bdf8",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=[6, 6]
        )
        style.map(
            "Reporte.Treeview.Heading",
            background=[("active", "#334155")]
        )

    def _on_re_subtab_changed(self) -> None:
        """Acionado ao alternar sub-abas para atualizar dados em tempo real."""
        try:
            current = self.re_subtabs.get()
            if current == "📋 Logs":
                self._re_filtrar_logs()
            elif current == "⚡ Streaming":
                self._re_atualizar_kpis()
        except Exception as e:
            logger.debug(f"[ReporteEventos] Erro no switch de subtab: {e}")

    # ── SUB-ABA 1: STREAMING (TOTALMENTE RESPONSIVA & COM KPIS) ────────────────

    def _build_modern_subtab_streaming(self, parent: ctk.CTkFrame) -> None:
        main_box = ctk.CTkFrame(parent, fg_color="transparent")
        main_box.pack(fill="both", expand=True, padx=4, pady=4)

        # ── 1. BARRA SUPERIOR DE KPIS EXECUTIVOS (PADRÃO CANAIS LIVE) ──────────
        kpi_bar = ctk.CTkFrame(main_box, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        kpi_bar.pack(fill="x", padx=4, pady=(2, 6))

        kpi_row = ctk.CTkFrame(kpi_bar, fg_color="transparent")
        kpi_row.pack(fill="x", padx=6, pady=6)

        # KPI 1: Eventos na Grade
        kpi1 = ctk.CTkFrame(kpi_row, fg_color="#1b1b1b", corner_radius=8, width=175, height=52)
        kpi1.pack(side="left", padx=4, pady=2)
        kpi1.pack_propagate(False)
        ctk.CTkLabel(kpi1, text="📅 EVENTOS NA GRADE", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=8, pady=(5, 0))
        self.re_kpi_eventos_count = ctk.CTkLabel(kpi1, text="0", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00CED1")
        self.re_kpi_eventos_count.pack(anchor="w", padx=8, pady=(0, 4))

        # KPI 2: Plataformas Ativas
        kpi2 = ctk.CTkFrame(kpi_row, fg_color="#1b1b1b", corner_radius=8, width=175, height=52)
        kpi2.pack(side="left", padx=4, pady=2)
        kpi2.pack_propagate(False)
        ctk.CTkLabel(kpi2, text="📺 PLATAFORMAS ATIVAS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=8, pady=(5, 0))
        self.re_kpi_plat_count = ctk.CTkLabel(kpi2, text="6/6", font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFD700")
        self.re_kpi_plat_count.pack(anchor="w", padx=8, pady=(0, 4))

        # KPI 3: Chrome DevTools
        kpi3 = ctk.CTkFrame(kpi_row, fg_color="#1b1b1b", corner_radius=8, width=180, height=52)
        kpi3.pack(side="left", padx=4, pady=2)
        kpi3.pack_propagate(False)
        ctk.CTkLabel(kpi3, text="🌐 CHROME DEVTOOLS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=8, pady=(5, 0))
        self.re_kpi_chrome_status = ctk.CTkLabel(kpi3, text="9222: OFFLINE", font=ctk.CTkFont(size=14, weight="bold"), text_color="#888888")
        self.re_kpi_chrome_status.pack(anchor="w", padx=8, pady=(0, 4))

        # KPI 4: Status do Monitor
        kpi4 = ctk.CTkFrame(kpi_row, fg_color="#1b1b1b", corner_radius=8, width=175, height=52)
        kpi4.pack(side="left", padx=4, pady=2)
        kpi4.pack_propagate(False)
        ctk.CTkLabel(kpi4, text="⏱️ STATUS MONITOR", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=8, pady=(5, 0))
        self.re_kpi_monitor_status = ctk.CTkLabel(kpi4, text="EM ESPERA", font=ctk.CTkFont(size=14, weight="bold"), text_color="#f59e0b")
        self.re_kpi_monitor_status.pack(anchor="w", padx=8, pady=(0, 4))

        # ── 2. PAINEL DE CONTROLE RESPONSIVO (CARD #141414) ───────────────────
        ctrl_card = ctk.CTkFrame(main_box, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        ctrl_card.pack(fill="x", padx=4, pady=(0, 6))

        # Linha 1: Ações Principais & Filtros Rápidos
        r1 = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=(8, 4))

        self.re_btn_buscar = ctk.CTkButton(
            r1, text="🔍 Buscar Eventos", width=145, height=32,
            fg_color="#00CED1", hover_color="#008B8B", text_color="#0f172a", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._re_buscar_eventos
        )
        self.re_btn_buscar.pack(side="left", padx=(0, 6))

        self.re_btn_start = ctk.CTkButton(
            r1, text="▶ Start", width=95, height=32,
            fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._re_toggle_start
        )
        self.re_btn_start.pack(side="left", padx=3)

        self.re_btn_limpar = ctk.CTkButton(
            r1, text="🧹 Limpar", width=80, height=32,
            fg_color="#991b1b", hover_color="#7f1d1d", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._re_limpar_tree
        )
        self.re_btn_limpar.pack(side="left", padx=(3, 10))

        ctk.CTkLabel(r1, text="Refresh(s):", font=ctk.CTkFont(size=11), text_color="#888888").pack(side="left", padx=(4, 2))
        self.re_entry_refresh = ctk.CTkEntry(r1, textvariable=self.re_refresh_var, width=45, height=28, justify="center")
        self.re_entry_refresh.pack(side="left", padx=2)

        ctk.CTkLabel(r1, text="Data Início:", font=ctk.CTkFont(size=11), text_color="#888888").pack(side="left", padx=(8, 2))
        self.re_entry_data = ctk.CTkEntry(r1, textvariable=self.re_data_inicio_var, width=85, height=28, justify="center")
        self.re_entry_data.pack(side="left", padx=2)
        self.re_entry_data.bind("<KeyRelease>", self._re_formatar_data)

        self.re_cbo_plat = ctk.CTkButton(
            r1, text="📺 Plataformas ▾", width=125, height=28,
            fg_color="#1b1b1b", hover_color="#262626", border_width=1, border_color="#333333",
            font=ctk.CTkFont(size=11), command=self._re_popup_plat_menu
        )
        self.re_cbo_plat.pack(side="left", padx=(10, 2))

        self.re_cbo_camp = ctk.CTkButton(
            r1, text="🏆 Campeonatos ▾", width=130, height=28,
            fg_color="#1b1b1b", hover_color="#262626", border_width=1, border_color="#333333",
            font=ctk.CTkFont(size=11), command=self._re_popup_camp_menu
        )
        self.re_cbo_camp.pack(side="left", padx=2)

        ctk.CTkButton(r1, text="📂 Abrir CSV", width=85, height=28, fg_color="#262626", hover_color="#333333", font=ctk.CTkFont(size=11), command=self._re_abrir_csv).pack(side="left", padx=(10, 2))
        ctk.CTkButton(r1, text="💾 Salvar CSV", width=85, height=28, fg_color="#1f538d", hover_color="#163e6b", font=ctk.CTkFont(size=11), command=self._re_salvar_csv).pack(side="left", padx=2)

        ctk.CTkButton(r1, text="➕", width=34, height=28, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"), command=self._re_add_row).pack(side="left", padx=(8, 2))
        ctk.CTkButton(r1, text="➖", width=34, height=28, fg_color="#ef4444", hover_color="#dc2626", font=ctk.CTkFont(size=12, weight="bold"), command=self._re_delete_row).pack(side="left", padx=2)

        # Linha 2: Notificações, Automações e Chrome (100% Responsivo)
        r2 = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=(2, 8))

        ctk.CTkLabel(r2, text="Destinatários:", font=ctk.CTkFont(size=11), text_color="#888888").pack(side="left", padx=(0, 4))
        self.re_entry_email = ctk.CTkEntry(r2, textvariable=self.re_email_var, height=28, placeholder_text="email@dominio.com; outro@dominio.com")
        self.re_entry_email.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.re_entry_email.bind("<FocusOut>", lambda e: self._re_salvar_config_atual())

        self.re_btn_email = ctk.CTkButton(
            r2, text="✉️ Disparar E-mail", width=125, height=28,
            fg_color="#059669", hover_color="#047857", font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._re_enviar_email(forcar=True)
        )
        self.re_btn_email.pack(side="left", padx=4)

        ctk.CTkCheckBox(r2, text="Auto E-mail às:", variable=self.re_auto_email_var, font=ctk.CTkFont(size=11), fg_color="#00CED1", text_color="#f1f5f9").pack(side="left", padx=(6, 2))
        self.re_entry_hora = ctk.CTkEntry(r2, textvariable=self.re_hora_auto_email_var, width=50, height=28, justify="center")
        self.re_entry_hora.pack(side="left", padx=2)

        ctk.CTkCheckBox(r2, text="Auto Busca", variable=self.re_auto_busca_var, font=ctk.CTkFont(size=11), fg_color="#00CED1", text_color="#f1f5f9").pack(side="left", padx=(8, 2))
        ctk.CTkCheckBox(r2, text="Somente Relatório", variable=self.re_somente_relatorio_var, font=ctk.CTkFont(size=11), fg_color="#00CED1", text_color="#f1f5f9").pack(side="left", padx=(8, 4))

        self.re_btn_chrome9222 = ctk.CTkButton(r2, text="🌐 Chrome 9222", width=105, height=28, fg_color="#262626", hover_color="#333333", font=ctk.CTkFont(size=11), command=lambda: self._re_toggle_chrome("9222"))
        self.re_btn_chrome9222.pack(side="left", padx=3)

        self.re_btn_chrome9224 = ctk.CTkButton(r2, text="🌐 Chrome 9224", width=105, height=28, fg_color="#262626", hover_color="#333333", font=ctk.CTkFont(size=11), command=lambda: self._re_toggle_chrome("9224"))
        self.re_btn_chrome9224.pack(side="left", padx=3)

        # ── 3. GRADE PRINCIPAL DE EVENTOS (CARD #141414, 100% RESPONSIVA) ─────
        grid_card = ctk.CTkFrame(main_box, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        grid_card.pack(fill="both", expand=True, padx=4, pady=2)

        columns = ("Campeonato", "Partida", "Data", "Horário", "Navegador", "Min antes", "Canal de Transmissão", "Url")
        self.re_tree = ttk.Treeview(grid_card, columns=columns, show="headings", style="Reporte.Treeview", height=14)

        col_widths = [180, 270, 95, 75, 85, 85, 170, 260]
        for col, w in zip(columns, col_widths):
            self.re_tree.heading(col, text=col, command=lambda c=col: self._re_sort_tree(c))
            self.re_tree.column(col, width=w, minwidth=60, anchor=CENTER if col not in ("Partida", "Url") else W)

        vsb = ttk.Scrollbar(grid_card, orient="vertical", command=self.re_tree.yview)
        hsb = ttk.Scrollbar(grid_card, orient="horizontal", command=self.re_tree.xview)
        self.re_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.re_tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        vsb.grid(row=0, column=1, sticky="ns", pady=(6, 0), padx=(0, 6))
        hsb.grid(row=1, column=0, sticky="ew", padx=(6, 0), pady=(0, 6))
        grid_card.grid_rowconfigure(0, weight=1)
        grid_card.grid_columnconfigure(0, weight=1)

        self.re_tree.tag_configure("even", background="#142236", foreground="#f1f5f9")
        self.re_tree.tag_configure("odd", background="#0f172a", foreground="#f1f5f9")
        self.re_tree.tag_configure("urgent", background="#7f1d1d", foreground="#fca5a5")

        self.re_tree.bind("<Double-1>", self._on_re_tree_double_click)

        # ── 4. BARRA INFERIOR DE STATUS E PROGRESSO ───────────────────────────
        self.re_toolbar = ctk.CTkFrame(main_box, height=32, fg_color="#141414", corner_radius=8, border_width=1, border_color="#262626")
        self.re_toolbar.pack(side="bottom", fill="x", padx=4, pady=(4, 2))

        self.re_lbl_status = ctk.CTkLabel(self.re_toolbar, text="Pronto para monitoramento.", font=ctk.CTkFont(size=11), text_color="#888888")
        self.re_lbl_status.pack(side="left", padx=12, pady=4)

        self.re_progresso = ctk.CTkProgressBar(self.re_toolbar, width=200, height=10, progress_color="#00CED1")
        self.re_progresso.set(0.0)
        self.re_progresso.pack(side="right", padx=12, pady=6)

        self.re_lbl_process = ctk.CTkLabel(self.re_toolbar, text="", font=ctk.CTkFont(size=11), text_color="#00CED1")
        self.re_lbl_process.pack(side="right", padx=6, pady=4)

        # Carrega dados salvos em background sem travar UI
        self.after(50, self._re_carregar_dados_iniciais)

    # ── SUB-ABA 2: LOGS (TOTALMENTE OPERANTE E RESPONSIVA) ───────────────────

    def _build_modern_subtab_logs(self, parent: ctk.CTkFrame) -> None:
        ctrl = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        ctrl.pack(fill="x", padx=6, pady=6)

        r = ctk.CTkFrame(ctrl, fg_color="transparent")
        r.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(r, text="Nível:", font=ctk.CTkFont(size=11), text_color="#888888").pack(side="left", padx=4)
        self.re_log_tipo_var = ctk.StringVar(value="TODOS")
        cbo = ctk.CTkOptionMenu(r, variable=self.re_log_tipo_var, values=["TODOS", "ERROR", "WARNING", "INFO"], width=105, height=28)
        cbo.pack(side="left", padx=4)

        ctk.CTkLabel(r, text="Início:", font=ctk.CTkFont(size=11), text_color="#888888").pack(side="left", padx=(10, 4))
        cal_box1 = tk.Frame(r, bg="#141414")
        cal_box1.pack(side="left")
        self.re_log_data_ini = DateEntry(cal_box1, width=11, date_pattern="dd/MM/yyyy", locale="pt_BR")
        self.re_log_data_ini.set_date(datetime.now())
        self.re_log_data_ini.pack(padx=2)

        ctk.CTkLabel(r, text="Fim:", font=ctk.CTkFont(size=11), text_color="#888888").pack(side="left", padx=(10, 4))
        cal_box2 = tk.Frame(r, bg="#141414")
        cal_box2.pack(side="left")
        self.re_log_data_fim = DateEntry(cal_box2, width=11, date_pattern="dd/MM/yyyy", locale="pt_BR")
        self.re_log_data_fim.set_date(datetime.now())
        self.re_log_data_fim.pack(padx=2)

        ctk.CTkButton(r, text="🔍 Filtrar", width=80, height=28, fg_color="#0284c7", hover_color="#0369a1", font=ctk.CTkFont(size=11, weight="bold"), command=self._re_filtrar_logs).pack(side="left", padx=12)
        ctk.CTkButton(r, text="🧹 Limpar Logs", width=105, height=28, fg_color="#991b1b", hover_color="#7f1d1d", font=ctk.CTkFont(size=11), command=self._re_limpar_logs).pack(side="left", padx=4)
        ctk.CTkButton(r, text="📤 Exportar CSV", width=105, height=28, fg_color="#059669", hover_color="#047857", font=ctk.CTkFont(size=11), command=self._re_exportar_logs).pack(side="left", padx=4)

        # Grade de Logs Responsiva
        grid_card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        grid_card.pack(fill="both", expand=True, padx=6, pady=4)

        self.re_tree_logs = ttk.Treeview(grid_card, columns=("data", "nivel", "linha", "mensagem"), show="headings", style="Reporte.Treeview", height=16)
        self.re_tree_logs.heading("data", text="Data/Hora")
        self.re_tree_logs.heading("nivel", text="Nível")
        self.re_tree_logs.heading("linha", text="Linha")
        self.re_tree_logs.heading("mensagem", text="Mensagem de Log")

        self.re_tree_logs.column("data", width=150, anchor=CENTER)
        self.re_tree_logs.column("nivel", width=90, anchor=CENTER)
        self.re_tree_logs.column("linha", width=70, anchor=CENTER)
        self.re_tree_logs.column("mensagem", width=780, anchor=W)

        vsb = ttk.Scrollbar(grid_card, orient="vertical", command=self.re_tree_logs.yview)
        hsb = ttk.Scrollbar(grid_card, orient="horizontal", command=self.re_tree_logs.xview)
        self.re_tree_logs.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.re_tree_logs.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        vsb.grid(row=0, column=1, sticky="ns", pady=(6, 0), padx=(0, 6))
        hsb.grid(row=1, column=0, sticky="ew", padx=(6, 0), pady=(0, 6))
        grid_card.grid_rowconfigure(0, weight=1)
        grid_card.grid_columnconfigure(0, weight=1)

        self.re_tree_logs.tag_configure("ERROR", background="#451a1a", foreground="#fca5a5")
        self.re_tree_logs.tag_configure("WARNING", background="#422006", foreground="#fde047")
        self.re_tree_logs.tag_configure("INFO", background="#14532d", foreground="#86efac")

        self.after(250, self._re_filtrar_logs)

    # ── SUB-ABA 3: ACESSOS (COM BOTÕES RÁPIDOS DE PASTAS) ────────────────────

    def _build_modern_subtab_acessos(self, parent: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(parent, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        # Header com título e botões de atalho de diretórios
        header_bar = ctk.CTkFrame(scroll, fg_color="transparent")
        header_bar.pack(fill="x", padx=16, pady=(12, 6))

        title_box = ctk.CTkFrame(header_bar, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="🔐 Credenciais Criptografadas & Perfis do Chrome", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00CED1").pack(anchor="w")
        ctk.CTkLabel(title_box, text="Os dados são gravados localmente em config/ com criptografia simétrica Fernet (AES).", font=ctk.CTkFont(size=11), text_color="#888888").pack(anchor="w")

        # Botões para abrir as pastas solicitadas pelo usuário
        btn_box = ctk.CTkFrame(header_bar, fg_color="transparent")
        btn_box.pack(side="right")
        ctk.CTkButton(btn_box, text="📁 Abrir Pasta config/", width=150, height=30, fg_color="#262626", hover_color="#333333", font=ctk.CTkFont(size=11), command=self._re_abrir_pasta_config).pack(side="left", padx=4)
        ctk.CTkButton(btn_box, text="📁 Pasta Perfis TempProfile", width=175, height=30, fg_color="#1f538d", hover_color="#163e6b", font=ctk.CTkFont(size=11), command=self._re_abrir_pasta_perfis_chrome).pack(side="left", padx=4)

        # Bloco explicativo com as localizações exatas
        info_card = ctk.CTkFrame(scroll, fg_color="#1b1b1b", corner_radius=8, border_width=1, border_color="#333333")
        info_card.pack(fill="x", padx=16, pady=(4, 14))
        info_txt = (
            "📌 ONDE COLOCAR SEUS ARQUIVOS:\n"
            "• auth.xml e config.xml: Devem ficar dentro da pasta 'config/' (ex: Monitor_Esportes\\config\\auth.xml).\n"
            "• TempProfile e TempProfile2: Podem ser colocados dentro da pasta 'config\\' OU diretamente na raiz do 'Monitor_Esportes\\'.\n"
            "  O sistema auto-detecta ambas as localizações instantaneamente ao iniciar o Chrome 9222 ou 9224."
        )
        ctk.CTkLabel(info_card, text=info_txt, font=ctk.CTkFont(size=11), text_color="#cbd5e1", justify="left").pack(anchor="w", padx=12, pady=8)

        pares = [
            ("Amazon Prime Video", "usuario_prime", "senha_prime", "config.xml"),
            ("Disney+ / Star+", "usuario_disney", "senha_disney", "config.xml"),
            ("DAZN", "usuario_dazn", "senha_dazn", "config.xml"),
            ("Paramount+", "usuario_paramount", "senha_paramount", "config.xml"),
            ("Max (HBO)", "usuario_max", "senha_max", "config.xml"),
            ("E-mail Notificador SMTP (Gmail)", "email", "senha", "auth.xml"),
        ]

        self.re_acessos_entries = {}
        for plat_nome, tag_u, tag_p, fname in pares:
            card_p = ctk.CTkFrame(scroll, fg_color="#1b1b1b", corner_radius=8, border_width=1, border_color="#262626")
            card_p.pack(fill="x", padx=16, pady=4)

            ctk.CTkLabel(card_p, text=plat_nome, font=ctk.CTkFont(size=12, weight="bold"), text_color="#00CED1", width=220, anchor="w").pack(side="left", padx=12, pady=8)

            val_u = get_config_value(tag_u) if fname == "config.xml" else get_auth_value(tag_u)
            val_p = get_config_value(tag_p) if fname == "config.xml" else get_auth_value(tag_p)

            e_u = ctk.CTkEntry(card_p, width=220, height=28, placeholder_text="Usuário / E-mail")
            if val_u: e_u.insert(0, val_u)
            e_u.pack(side="left", padx=6, pady=8)

            e_p = ctk.CTkEntry(card_p, width=200, height=28, placeholder_text="Senha / Token", show="*")
            if val_p: e_p.insert(0, val_p)
            e_p.pack(side="left", padx=6, pady=8)

            self.re_acessos_entries[tag_u] = (e_u, fname)
            self.re_acessos_entries[tag_p] = (e_p, fname)

        # Botão Salvar
        btn_salvar = ctk.CTkButton(
            scroll, text="💾 Salvar Todas as Credenciais", width=240, height=34,
            fg_color="#059669", hover_color="#047857", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._re_salvar_acessos
        )
        btn_salvar.pack(pady=16)

    # ── SUB-ABA 4: CAMPEONATOS (TOTALMENTE OPERANTE E RESPONSIVA) ────────────

    def _build_modern_subtab_campeonatos(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        header.pack(fill="x", padx=6, pady=6)

        top_r = ctk.CTkFrame(header, fg_color="transparent")
        top_r.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(top_r, text="🏆 Gestão de Campeonatos Oficiais & Extras", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00CED1").pack(side="left")

        ctk.CTkButton(top_r, text="➕ Adicionar", width=95, height=28, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=11, weight="bold"), command=self._re_add_campeonato).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="✏️ Editar", width=85, height=28, fg_color="#0284c7", hover_color="#0369a1", font=ctk.CTkFont(size=11), command=self._re_edit_campeonato).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="🗑️ Remover", width=85, height=28, fg_color="#ef4444", hover_color="#dc2626", font=ctk.CTkFont(size=11), command=self._re_remove_campeonato).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="🔄 Ativar/Pausar", width=110, height=28, fg_color="#262626", hover_color="#333333", font=ctk.CTkFont(size=11), command=self._re_toggle_campeonato).pack(side="right", padx=3)

        # Grade de Campeonatos
        grid_card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        grid_card.pack(fill="both", expand=True, padx=6, pady=4)

        cols = ("campeonato", "plataforma", "url", "ativo")
        self.re_tv_camps = ttk.Treeview(grid_card, columns=cols, show="headings", style="Reporte.Treeview", height=12)
        for col, hdr, w in zip(cols, ("Campeonato", "Plataforma / Canal", "URL / Fonte", "Status"), (240, 160, 580, 80)):
            self.re_tv_camps.heading(col, text=hdr)
            self.re_tv_camps.column(col, width=w, anchor=W if col != "ativo" else CENTER)

        vsb = ttk.Scrollbar(grid_card, orient="vertical", command=self.re_tv_camps.yview)
        hsb = ttk.Scrollbar(grid_card, orient="horizontal", command=self.re_tv_camps.xview)
        self.re_tv_camps.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.re_tv_camps.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        vsb.grid(row=0, column=1, sticky="ns", pady=(6, 0), padx=(0, 6))
        hsb.grid(row=1, column=0, sticky="ew", padx=(6, 0), pady=(0, 6))
        grid_card.grid_rowconfigure(0, weight=1)
        grid_card.grid_columnconfigure(0, weight=1)

        self.after(100, self._re_reload_camps_tv)

    # ── SUB-ABA 5: CANAIS YOUTUBE (TOTALMENTE OPERANTE E RESPONSIVA) ──────────

    def _build_modern_subtab_youtube(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        header.pack(fill="x", padx=6, pady=6)

        top_r = ctk.CTkFrame(header, fg_color="transparent")
        top_r.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(top_r, text="📡 Canais do YouTube Monitorados (Validados pela CBF)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00CED1").pack(side="left")

        ctk.CTkButton(top_r, text="🔍 Buscar Canais Agora", width=160, height=28, fg_color="#00CED1", hover_color="#008B8B", text_color="#0f172a", font=ctk.CTkFont(size=11, weight="bold"), command=self._re_buscar_canais_youtube_agora).pack(side="right", padx=(8, 0))
        ctk.CTkButton(top_r, text="🔄 Padrões", width=80, height=28, fg_color="#262626", hover_color="#333333", font=ctk.CTkFont(size=11), command=self._re_restore_default_yt_channels).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="🔄 Ativar/Pausar", width=105, height=28, fg_color="#262626", hover_color="#333333", font=ctk.CTkFont(size=11), command=self._re_toggle_yt_channel).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="🗑️ Remover", width=85, height=28, fg_color="#ef4444", hover_color="#dc2626", font=ctk.CTkFont(size=11), command=self._re_remove_yt_channel).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="✏️ Editar", width=80, height=28, fg_color="#0284c7", hover_color="#0369a1", font=ctk.CTkFont(size=11), command=self._re_edit_yt_channel).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="➕ Adicionar", width=95, height=28, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=11, weight="bold"), command=self._re_add_yt_channel).pack(side="right", padx=3)

        # Grade de Canais
        grid_card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        grid_card.pack(fill="both", expand=True, padx=6, pady=4)

        cols = ("nome", "url", "ativo")
        self.re_tv_yt = ttk.Treeview(grid_card, columns=cols, show="headings", style="Reporte.Treeview", height=12)
        for col, hdr, w in zip(cols, ("Nome do Canal", "URL do Canal", "Status"), (260, 720, 90)):
            self.re_tv_yt.heading(col, text=hdr)
            self.re_tv_yt.column(col, width=w, anchor=W if col != "ativo" else CENTER)

        vsb = ttk.Scrollbar(grid_card, orient="vertical", command=self.re_tv_yt.yview)
        hsb = ttk.Scrollbar(grid_card, orient="horizontal", command=self.re_tv_yt.xview)
        self.re_tv_yt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.re_tv_yt.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        vsb.grid(row=0, column=1, sticky="ns", pady=(6, 0), padx=(0, 6))
        hsb.grid(row=1, column=0, sticky="ew", padx=(6, 0), pady=(0, 6))
        grid_card.grid_rowconfigure(0, weight=1)
        grid_card.grid_columnconfigure(0, weight=1)

        self.after(100, self._re_reload_yt_tv)

    # ── SUB-ABA 6: FAQ (DARK TEXTBOX) ─────────────────────────────────────────

    def _build_modern_subtab_faq(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        card.pack(fill="both", expand=True, padx=6, pady=6)

        txt = ctk.CTkTextbox(card, font=ctk.CTkFont(size=12), text_color="#f1f5f9", fg_color="#0f172a", corner_radius=8)
        txt.pack(fill="both", expand=True, padx=8, pady=8)

        faq_content = """📌 GUIA OPERACIONAL — MÓDULO REPORTE DE EVENTOS

1. ⚡ Streaming (Painel Principal de Varredura e Controle)
• 'Buscar Eventos': Coleta automaticamente todos os jogos e horários autorizados das plataformas selecionadas:
  - CBF (Brasileirão Série A e Copa do Brasil): aplica a regra de fuso de -1 hora e calcula a transmissão oficial.
  - Copa do Mundo FIFA 2026: lê a tabela de grupos e aplica o fuso de -2 horas.
  - YouTube (Cazé TV e Canais Esportivos): busca transmissões e valida na tabela da CBF.
• Edição Interativa na Grade: Duplo-clique em qualquer linha abre o popup especializado da célula (Calendário, Relógio Digital com Sliders, Opções de Navegador e Plataforma).
• 'Start': Ativa o monitoramento temporal contínuo em segundo plano.
• 'Disparar E-mail': Gera relatório HTML corporativo estilizado e envia via SMTP (bloqueio de segurança noturno entre 22h e 07h).

2. 🏆 Campeonatos & Canais do YouTube
• Permite gerenciar torneios e feeds adicionais com persistência local em config/.
• O botão 'Buscar Canais Agora' executa varredura profunda e sincroniza automaticamente a lista de confrontos com o SharePoint da emissora via Microsoft Graph API.

3. 🔐 Segurança de Credenciais & Perfis do Chrome
• Senhas e tokens de acesso são protegidos por criptografia simétrica Fernet (AES).
• Os arquivos auth.xml e config.xml ficam em config/.
• As pastas TempProfile e TempProfile2 podem ficar em config/ ou na raiz do projeto.
• Navegadores de depuração (Chrome 9222 e 9224) contam com perfis isolados e encerramento seguro cirúrgico por PID, preservando todas as demais tarefas do usuário no Windows.
"""
        txt.insert("1.0", faq_content)
        txt.configure(state="disabled")

    # Aliases de compatibilidade para suítes de testes e chamadas legadas
    _build_subtab_streaming = _build_modern_subtab_streaming
    _build_subtab_logs = _build_modern_subtab_logs
    _build_subtab_acessos = _build_modern_subtab_acessos
    _build_subtab_campeonatos = _build_modern_subtab_campeonatos
    _build_subtab_youtube_channels = _build_modern_subtab_youtube
    _build_subtab_faq = _build_modern_subtab_faq

    # ── MÉTODOS DE CONTROLE, ATUALIZAÇÃO DE KPIS E AÇÕES ──────────────────────

    def _re_atualizar_kpis(self) -> None:
        """Atualiza dinamicamente os 4 cartões de KPI do Reporte de Eventos."""
        try:
            # 1. Total de eventos na grade
            n_eventos = len(self.re_tree.get_children()) if hasattr(self, "re_tree") and self.re_tree else 0
            if hasattr(self, "re_kpi_eventos_count") and self.re_kpi_eventos_count:
                self.re_kpi_eventos_count.configure(text=str(n_eventos))

            # 2. Total de plataformas ativas
            n_plats = sum(1 for v in self.re_plat_vars.values() if v.get())
            total_plats = len(self.re_plat_vars)
            if hasattr(self, "re_kpi_plat_count") and self.re_kpi_plat_count:
                self.re_kpi_plat_count.configure(text=f"{n_plats}/{total_plats}")

            # 3. Status Chrome DevTools
            c9222_on = verificar_chrome_debug("9222")
            if hasattr(self, "re_kpi_chrome_status") and self.re_kpi_chrome_status:
                if c9222_on:
                    self.re_kpi_chrome_status.configure(text="9222: ATIVO", text_color="#10b981")
                else:
                    self.re_kpi_chrome_status.configure(text="9222: OFFLINE", text_color="#888888")

            # 4. Status do Monitor
            if hasattr(self, "re_kpi_monitor_status") and self.re_kpi_monitor_status:
                if getattr(self, "re_busy", False):
                    self.re_kpi_monitor_status.configure(text="VARRENDO...", text_color="#00CED1")
                elif getattr(self, "re_is_running", False):
                    self.re_kpi_monitor_status.configure(text="MONITORANDO", text_color="#10b981")
                else:
                    self.re_kpi_monitor_status.configure(text="EM ESPERA", text_color="#f59e0b")
        except Exception as e:
            logger.debug(f"[KPIs] Erro ao atualizar: {e}")

    def _re_abrir_pasta_config(self) -> None:
        """Abre a pasta config/ no Windows Explorer."""
        cfg_dir = get_config_dir()
        try:
            os.startfile(str(cfg_dir))
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta config/: {e}")

    def _re_abrir_pasta_perfis_chrome(self) -> None:
        """Abre a pasta onde os perfis TempProfile estão localizados."""
        p = obter_profile_dir("9222")
        parent = p.parent if p.exists() else get_config_dir()
        try:
            os.startfile(str(parent))
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta de perfis: {e}")

    def _re_toggle_chrome(self, porta: str) -> None:
        """Alterna a abertura ou fechamento do Chrome DevTools de forma 100% assíncrona (sem congelar GUI)."""
        btn = self.re_btn_chrome9222 if porta == "9222" else self.re_btn_chrome9224
        if btn:
            btn.configure(state="disabled", text=f"⏳ {porta}...")

        def _worker():
            try:
                if verificar_chrome_debug(porta):
                    fechar_chrome_seguro(porta)
                    is_active = False
                    msg = f"Chrome da porta {porta} encerrado com segurança."
                else:
                    abrir_chrome(porta)
                    is_active = verificar_chrome_debug(porta)
                    if is_active:
                        msg = f"Chrome iniciado com sucesso na porta {porta} (Perfil isolado)."
                    else:
                        msg = f"Comando de inicialização enviado para porta {porta}. Verifique a janela do navegador."

                def _finish():
                    if btn:
                        btn.configure(state="normal", text=f"🌐 Chrome {porta}")
                        if is_active:
                            btn.configure(fg_color="#059669", hover_color="#047857")
                        else:
                            btn.configure(fg_color="#262626", hover_color="#333333")
                    self._re_atualizar_kpis()
                    messagebox.showinfo("Chrome DevTools", msg)

                self.after(0, _finish)
            except Exception as e:
                err_msg = str(e)
                def _error(err=err_msg):
                    if btn:
                        btn.configure(state="normal", text=f"🌐 Chrome {porta}", fg_color="#262626")
                    self._re_atualizar_kpis()
                    messagebox.showerror("Erro Chrome", f"Erro ao alternar Chrome na porta {porta}: {err}")
                self.after(0, _error)

        threading.Thread(target=_worker, daemon=True).start()

    # ── MÉTODOS DE BUSCA DE ALTA VELOCIDADE ───────────────────────────────────

    def _re_buscar_eventos(self) -> None:
        """
        Executa a busca completa de eventos de forma 100% idêntica ao Streaming_Scheduler original:
        1. Inicializa o Chrome DevTools 9222 com TempProfile visível se necessário ou em modo somente relatório.
        2. Varre Dazn, Amazon Prime Video, Max e Disney+ conectando diretamente ao Chrome 9222.
        3. Varre Cazé TV e canais do YouTube cadastrados via yt-dlp.
        4. Varre campeonatos extras da aba Campeonatos.
        5. Varre tabela oficial da CBF (PDF) e Copa do Mundo FIFA 2026 (Excel), aplicando os fusos oficiais (-1h / -2h) e pulando o que já foi achado no Selenium.
        6. Padroniza os nomes para forma canônica e bonita (padronizar_nomes_grid).
        7. Remove duplicatas preservando a prioridade Plataforma > CBF (remover_duplicatas).
        8. Ordena cronologicamente e alterna Esquerda/Direita (ajustartodootree).
        9. Se somente_relatorio, encerra o Chrome 9222.
        """
        if self.re_busy:
            messagebox.showinfo("Aviso", "Uma busca de eventos já está em processamento.")
            return

        self.re_busy = True
        self.re_btn_buscar.configure(state="disabled")
        self.re_lbl_status.configure(text="Iniciando varredura unificada...")
        self.re_progresso.set(0.05)
        self._re_atualizar_kpis()

        # Captura variáveis na thread principal
        usar_cbf = bool(self.re_plat_vars.get("CBF") and self.re_plat_vars["CBF"].get())
        usar_caze = bool(self.re_plat_vars.get("Cazé TV") and self.re_plat_vars["Cazé TV"].get())
        usar_prime = bool(self.re_plat_vars.get("Amazon Prime") and self.re_plat_vars["Amazon Prime"].get())
        usar_dazn = bool(self.re_plat_vars.get("Dazn") and self.re_plat_vars["Dazn"].get())
        usar_max = bool(self.re_plat_vars.get("Max") and self.re_plat_vars["Max"].get())
        usar_disney = bool(self.re_plat_vars.get("Disney") and self.re_plat_vars["Disney"].get())
        somente_relatorio = bool(self.re_somente_relatorio_var.get())
        data_inicio = self.re_data_inicio_var.get().strip()

        camps_ativos = {k: v.get() for k, v in self.re_camp_vars.items()}
        plats_ativos = {
            "Amazon Prime": usar_prime,
            "Dazn": usar_dazn,
            "Max": usar_max,
            "Disney": usar_disney,
        }

        # Snapshot de partidas já no Treeview para evitar duplicações na CBF
        existing_matches = []
        for i in self.re_tree.get_children():
            v = self.re_tree.item(i, "values")
            if len(v) >= 3:
                existing_matches.append((str(v[1]), str(v[2])))

        q = queue.Queue()

        def _worker():
            total_inseridos = 0
            try:
                # 0. Abertura do Chrome DevTools se necessário ou em modo somente relatório
                precisa_chrome = somente_relatorio or any(plats_ativos.values())
                if precisa_chrome:
                    if not verificar_chrome_debug("9222"):
                        q.put(("status", "Iniciando Chrome DevTools (Porta 9222) com perfil TempProfile...", 0.05))
                        abrir_chrome("9222")
                        if somente_relatorio:
                            time.sleep(5)
                    else:
                        q.put(("status", "Chrome DevTools (Porta 9222) ativo.", 0.08))

                # 1. DAZN
                if usar_dazn and camps_ativos.get("Mundial de Clubes FIFA"):
                    q.put(("status", "Atualização de eventos do DAZN...", 0.15))
                    try:
                        url_dazn = 'https://www.dazn.com/pt-BR/competition/Competition:dc4k1xh2984zbypbnunk7ncic'
                        evs_dazn = run_eventos_dazn(url_dazn, expected_camp="Mundial de Clubes FIFA")
                        for ev in evs_dazn:
                            q.put(("event", ev))
                            total_inseridos += 1
                    except Exception as e_dazn:
                        logger.warning(f"[ReporteEventos] Erro DAZN: {e_dazn}")

                # 2. Amazon Prime Video (Navegador real via Selenium)
                if usar_prime:
                    if camps_ativos.get("Brasileirão serie A") or camps_ativos.get("Brasileirão Série A"):
                        q.put(("status", "Buscando Amazon Prime - Brasileirão Série A...", 0.25))
                        try:
                            url_bsa = 'https://www.primevideo.com/tournament/amzn1.dv.icid.5a28c628-0310-42c0-8966-2f1f748488d3/ref=atv_hm_spo_c_NPzfck_2_1?jic=8%7CEgNhbGw%3D'
                            evs_prime_bsa = run_eventos_prime(url_bsa, expected_camp="Brasileirão serie A")
                            for ev in evs_prime_bsa:
                                q.put(("event", ev))
                                total_inseridos += 1
                        except Exception as e_p1:
                            logger.warning(f"[ReporteEventos] Erro Prime BSA: {e_p1}")

                    if camps_ativos.get("Copa do Brasil"):
                        q.put(("status", "Buscando Amazon Prime - Copa do Brasil...", 0.35))
                        try:
                            url_cdb = 'https://www.primevideo.com/tournament/amzn1.dv.icid.6e097abf-f4c9-4638-ba1e-7ff95367e1c8/ref=atv_hm_spo_c_NPzfck_2_2?jic=8%7CEgNhbGw%3D'
                            evs_prime_cdb = run_eventos_prime(url_cdb, expected_camp="Copa do Brasil")
                            for ev in evs_prime_cdb:
                                q.put(("event", ev))
                                total_inseridos += 1
                        except Exception as e_p2:
                            logger.warning(f"[ReporteEventos] Erro Prime CDB: {e_p2}")

                # 3. Max (HBO)
                if usar_max and camps_ativos.get("Campeonato Paulista"):
                    q.put(("status", "Buscando Max - Campeonato Paulista...", 0.45))
                    try:
                        url_max = 'https://play.hbomax.com/sport/event/paulistao'
                        evs_max = run_eventos_max(url_max, expected_camp="Campeonato Paulista")
                        for ev in evs_max:
                            q.put(("event", ev))
                            total_inseridos += 1
                    except Exception as e_max:
                        logger.warning(f"[ReporteEventos] Erro Max: {e_max}")

                # 4. Disney+
                if usar_disney:
                    if camps_ativos.get("CONMEBOL Libertadores"):
                        q.put(("status", "Buscando Disney+ - CONMEBOL Libertadores...", 0.55))
                        try:
                            url_lib = 'https://www.disneyplus.com/pt-br/browse/entity-1229387e-c683-4ef3-9f32-68824a7be427'
                            evs_disney_lib = run_eventos_disney(url_lib, expected_camp="CONMEBOL Libertadores")
                            for ev in evs_disney_lib:
                                q.put(("event", ev))
                                total_inseridos += 1
                        except Exception as e_dis1:
                            logger.warning(f"[ReporteEventos] Erro Disney Libertadores: {e_dis1}")

                    if camps_ativos.get("CONMEBOL Sudamericana"):
                        q.put(("status", "Buscando Disney+ - CONMEBOL Sudamericana...", 0.60))
                        try:
                            url_suda = 'https://www.disneyplus.com/pt-br/browse/entity-7bf8f49c-cc47-4d42-9a85-587631faee03'
                            evs_disney_suda = run_eventos_disney(url_suda, expected_camp="CONMEBOL Sudamericana")
                            for ev in evs_disney_suda:
                                q.put(("event", ev))
                                total_inseridos += 1
                        except Exception as e_dis2:
                            logger.warning(f"[ReporteEventos] Erro Disney Sudamericana: {e_dis2}")

                # 5. Cazé TV
                if usar_caze:
                    q.put(("status", "Atualização de eventos do Cazé TV...", 0.70))
                    try:
                        caze_evs = obter_eventos_caze_tv()
                        for c_ev in caze_evs:
                            q.put(("event", c_ev))
                            total_inseridos += 1
                    except Exception as e_caze:
                        logger.warning(f"[ReporteEventos] Aviso Cazé TV: {e_caze}")

                # 6. Campeonatos Extras e Canais do YouTube cadastrados
                try:
                    q.put(("status", "Buscando campeonatos adicionais e canais YouTube...", 0.80))
                    for cfg in carregar_campeonatos_config():
                        if not cfg.get("ativo", True): continue
                        n_camp = cfg.get("campeonato", "")
                        p_plat = cfg.get("plataforma", "")
                        u_url = cfg.get("url", "")
                        if not n_camp or not u_url or not p_plat: continue
                        if p_plat == "Amazon Prime":
                            extra_evs = run_eventos_prime(u_url, expected_camp=n_camp)
                        elif p_plat == "Dazn":
                            extra_evs = run_eventos_dazn(u_url, expected_camp=n_camp)
                        elif p_plat == "Max":
                            extra_evs = run_eventos_max(u_url, expected_camp=n_camp)
                        elif p_plat == "Disney":
                            extra_evs = run_eventos_disney(u_url, expected_camp=n_camp)
                        elif p_plat == "Cazé TV":
                            extra_evs = obter_eventos_canal_youtube("Cazé TV", u_url)
                        else:
                            extra_evs = []
                        for ev in extra_evs:
                            q.put(("event", ev))
                            total_inseridos += 1

                    for ch in carregar_youtube_channels_config():
                        if not ch.get("ativo", True): continue
                        ch_nome = ch.get("nome", "YouTube")
                        ch_url = ch.get("url", "")
                        if not ch_url: continue
                        yt_evs = obter_eventos_canal_youtube(ch_nome, ch_url)
                        for ev in (yt_evs or []):
                            q.put(("event", ev))
                            total_inseridos += 1
                except Exception as e_extra:
                    logger.warning(f"[ReporteEventos] Aviso extras/YouTube: {e_extra}")

                # 7. CBF Oficial (PDF e Copa do Mundo Excel) - Roda por último para não sobrepor plataformas
                if usar_cbf:
                    q.put(("status", "Processando tabela oficial da CBF (PDF) e Copa do Mundo...", 0.88))
                    try:
                        cbf_evs = run_eventos_cbf(camps_ativos, data_inicio_str=data_inicio, existing_matches=existing_matches)
                        for ev in cbf_evs:
                            q.put(("event", ev))
                            total_inseridos += 1
                    except Exception as e_cbf:
                        logger.warning(f"[ReporteEventos] Erro CBF PDF: {e_cbf}")

                # 8. Padronização e Deduplicação no grid
                q.put(("status", "Padronizando nomes e organizando grade...", 0.95))
                q.put(("standardize_and_dedup", None))

                # 9. Fechamento seguro se em modo somente relatório
                if somente_relatorio:
                    fechar_chrome_seguro("9222")

                # 10. Conclusão
                if total_inseridos > 0:
                    msg_ok = f"Varredura concluída! {total_inseridos} eventos carregados com sucesso."
                else:
                    msg_ok = "Varredura concluída! Nenhum novo evento adicionado."

                logger.info(f"[ReporteEventos] {msg_ok}")
                q.put(("done_success", msg_ok))
            except Exception as ex:
                logger.error(f"[ReporteEventos] Erro na busca: {ex}")
                q.put(("done_error", str(ex)))
            finally:
                q.put(("finished", None))

        def _poll_queue():
            try:
                while True:
                    msg = q.get_nowait()
                    kind = msg[0]
                    if kind == "status":
                        txt = msg[1]
                        prog = msg[2] if len(msg) > 2 else None
                        self.re_lbl_process.configure(text=txt)
                        if prog is not None:
                            self.re_progresso.set(prog)
                    elif kind == "progress":
                        self.re_progresso.set(msg[1])
                    elif kind == "event":
                        self._re_inserir_evento_na_grade(msg[1])
                    elif kind == "standardize_and_dedup":
                        padronizar_nomes_grid(self.re_tree)
                        remover_duplicatas(self.re_tree)
                        ajustartodootree(self.re_tree)
                        self._re_atualizar_kpis()
                    elif kind == "done_success":
                        self.re_lbl_status.configure(text=msg[1])
                        self.re_lbl_process.configure(text="")
                        self.re_progresso.set(1.0)
                        self._re_atualizar_kpis()
                        messagebox.showinfo("Sucesso", msg[1])
                    elif kind == "done_error":
                        self.re_lbl_status.configure(text=f"Erro na varredura: {msg[1]}")
                        self.re_lbl_process.configure(text="")
                        self.re_progresso.set(0.0)
                        self._re_atualizar_kpis()
                        messagebox.showerror("Erro na Busca", f"Ocorreu um erro durante a varredura:\n{msg[1]}")
                    elif kind == "finished":
                        self.re_busy = False
                        self.re_btn_buscar.configure(state="normal")
                        self._re_atualizar_kpis()
                        return
            except queue.Empty:
                pass

            if self.re_busy:
                self.after(100, _poll_queue)

        threading.Thread(target=_worker, daemon=True).start()
        self.after(100, _poll_queue)

    def _re_inserir_evento_na_grade(self, row: Tuple[Any, ...]) -> None:
        """Insere evento na Treeview sem duplicidade (chave: Campeonato + Partida + Data)."""
        if not row or len(row) < 3:
            return
        novo_camp = str(row[0]).strip().lower()
        nova_partida = str(row[1]).strip().lower()
        nova_data = str(row[2]).strip().lower()

        for item_id in self.re_tree.get_children():
            vals = self.re_tree.item(item_id, "values")
            if len(vals) >= 3:
                c_exist = str(vals[0]).strip().lower()
                p_exist = str(vals[1]).strip().lower()
                d_exist = str(vals[2]).strip().lower()
                if c_exist == novo_camp and p_exist == nova_partida and d_exist == nova_data:
                    return

        idx = len(self.re_tree.get_children())
        tag = "even" if idx % 2 == 0 else "odd"
        self.re_tree.insert("", "end", values=row, tags=(tag,))
        self._re_atualizar_kpis()

    def _re_carregar_dados_iniciais(self) -> None:
        """Carrega dados existentes do arquivo streaming_data.csv na grade com alto desempenho."""
        linhas = carregar_streaming_csv()
        for i in self.re_tree.get_children():
            self.re_tree.delete(i)
        for idx, r in enumerate(linhas):
            tag = "even" if idx % 2 == 0 else "odd"
            self.re_tree.insert("", "end", values=r, tags=(tag,))
        self.re_lbl_status.configure(text=f"Carregados {len(linhas)} eventos da base local streaming_data.csv.")
        self._re_atualizar_kpis()

    def _re_salvar_config_atual(self) -> None:
        """Salva as opções atuais da tela no config.xml para persistência de destinatários e preferências."""
        try:
            cfg = carrega_config_xml() or {}
            dest = self.re_email_var.get().strip()
            if dest and "@" in dest and not dest.startswith("gAAAA"):
                cfg["emails"] = dest
            cfg["refresh"] = self.re_refresh_var.get().strip()
            cfg["hora_automatico"] = self.re_hora_auto_email_var.get().strip()
            cfg["check_automatico_Email"] = bool(self.re_auto_email_var.get())
            cfg["check_automatico_Evento"] = bool(self.re_auto_busca_var.get())
            cfg["somente_relatorio"] = bool(self.re_somente_relatorio_var.get())
            cfg["plataformas"] = {k: v.get() for k, v in self.re_plat_vars.items()}
            cfg["campeonatos"] = {k: v.get() for k, v in self.re_camp_vars.items()}
            salvar_config_xml(cfg)
        except Exception as e:
            logger.debug(f"[ReporteEventos] Erro ao salvar config.xml: {e}")

    def _re_salvar_csv(self) -> None:
        linhas = [list(self.re_tree.item(i, "values")) for i in self.re_tree.get_children()]
        salvar_streaming_csv(linhas)
        self._re_salvar_config_atual()
        self._re_atualizar_kpis()
        messagebox.showinfo("Sucesso", f"{len(linhas)} eventos gravados com sucesso em config/streaming_data.csv!")

    def _re_abrir_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Arquivos CSV", "*.csv")])
        if not path: return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                linhas = [r for r in reader if r]
            for i in self.re_tree.get_children():
                self.re_tree.delete(i)
            for idx, r in enumerate(linhas):
                tag = "even" if idx % 2 == 0 else "odd"
                self.re_tree.insert("", "end", values=r, tags=(tag,))
            self.re_lbl_status.configure(text=f"Importados {len(linhas)} eventos do arquivo.")
            self._re_atualizar_kpis()
            messagebox.showinfo("Sucesso", f"{len(linhas)} eventos importados com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir arquivo: {e}")

    def _re_limpar_tree(self) -> None:
        for i in self.re_tree.get_children():
            self.re_tree.delete(i)
        self.re_lbl_status.configure(text="Grade limpa com sucesso.")
        self._re_atualizar_kpis()

    _re_limpar_eventos = _re_limpar_tree

    def _re_add_row(self) -> None:
        idx = len(self.re_tree.get_children())
        tag = "even" if idx % 2 == 0 else "odd"
        nova = ("Brasileirão serie A", "Novo Time A x Novo Time B", datetime.now().strftime("%d/%m/%Y"), "19:00", "Esquerda", "15", "Amazon Prime", "")
        self.re_tree.insert("", "end", values=nova, tags=(tag,))
        self._re_atualizar_kpis()

    def _re_delete_row(self) -> None:
        sel = self.re_tree.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione uma linha para remover.")
            return
        for i in sel:
            self.re_tree.delete(i)
        self._re_atualizar_kpis()

    def _re_toggle_start(self) -> None:
        if self.re_is_running:
            self.re_is_running = False
            self.re_btn_start.configure(text="▶ Start", fg_color="#10b981", hover_color="#059669")
            self.re_lbl_status.configure(text="Monitoramento contínuo pausado.")
            if self.re_loop_job_id:
                try: self.after_cancel(self.re_loop_job_id)
                except Exception: pass
                self.re_loop_job_id = None
        else:
            self.re_is_running = True
            self.re_btn_start.configure(text="⏹ Parar", fg_color="#ef4444", hover_color="#dc2626")
            self.re_lbl_status.configure(text="Monitoramento contínuo ativo.")
            self._re_executar_ciclo_monitoramento()
        self._re_atualizar_kpis()

    def _re_executar_ciclo_monitoramento(self) -> None:
        if not self.re_is_running: return
        try:
            if self.re_auto_email_var.get():
                agora_str = datetime.now().strftime("%H:%M")
                if agora_str == self.re_hora_auto_email_var.get().strip():
                    self._re_enviar_email(forcar=False)
        except Exception as e:
            logger.warning(f"[ReporteEventos] Erro no ciclo de monitoramento: {e}")

        try:
            ref_seg = max(5, int(self.re_refresh_var.get().strip()))
        except Exception:
            ref_seg = 20
        self.re_loop_job_id = self.after(ref_seg * 1000, self._re_executar_ciclo_monitoramento)

    def _re_enviar_email(self, forcar: bool = False) -> None:
        self._re_salvar_config_atual()
        linhas = [list(self.re_tree.item(i, "values")) for i in self.re_tree.get_children()]
        dest = self.re_email_var.get().strip()
        ok, msg = enviar_email_relatorio(linhas, dest, forcar=forcar)
        if ok:
            messagebox.showinfo("E-mail Enviado", msg)
        else:
            messagebox.showwarning("Aviso E-mail", msg)

    # ── DOUBLE CLICK POPUPS ───────────────────────────────────────────────────

    def _on_re_tree_double_click(self, event) -> None:
        rowid = self.re_tree.identify_row(event.y)
        column = self.re_tree.identify_column(event.x)
        if not rowid or not column: return

        bbox = self.re_tree.bbox(rowid, column)
        if not bbox: return
        x, y, width, height = bbox
        col_idx = int(column[1:]) - 1

        vals = self.re_tree.item(rowid, "values")
        atual = vals[col_idx] if col_idx < len(vals) else ""

        abs_x = self.re_tree.winfo_rootx() + x
        abs_y = self.re_tree.winfo_rooty() + y + height // 2

        if col_idx == 2:
            ModernDatePopup(self, self.re_tree, rowid, col_idx, atual, abs_x, abs_y)
        elif col_idx == 3:
            ModernTimePopup(self, self.re_tree, rowid, col_idx, atual, abs_x, abs_y)
        elif col_idx == 4:
            ModernOptionPopup(self, self.re_tree, rowid, col_idx, atual, abs_x, abs_y, options=["Esquerda", "Direita"])
        elif col_idx == 5:
            ModernOptionPopup(self, self.re_tree, rowid, col_idx, atual, abs_x, abs_y, options=["5", "10", "15", "20", "30", "45", "60"])
        elif col_idx == 6:
            ModernOptionPopup(self, self.re_tree, rowid, col_idx, atual, abs_x, abs_y, options=["Amazon Prime", "Disney", "Cazé TV", "Dazn", "Paramount", "Max"])
        else:
            ModernEditEntryPopup(self, self.re_tree, rowid, col_idx, atual, abs_x, abs_y, title=f"Editar Coluna {col_idx+1}")

    def _re_formatar_data(self, event=None) -> None:
        txt = self.re_data_inicio_var.get()
        limpo = re.sub(r"[^\d]", "", txt)
        if len(limpo) >= 8:
            fmt = f"{limpo[:2]}/{limpo[2:4]}/{limpo[4:8]}"
            self.re_data_inicio_var.set(fmt)

    def _re_sort_tree(self, col: str) -> None:
        items = [(self.re_tree.set(k, col), k) for k in self.re_tree.get_children("")]
        try:
            items.sort(key=lambda t: datetime.strptime(t[0], "%d/%m/%Y") if "/" in t[0] else t[0])
        except Exception:
            items.sort()
        for idx, (val, k) in enumerate(items):
            self.re_tree.move(k, "", idx)
            tag = "even" if idx % 2 == 0 else "odd"
            self.re_tree.item(k, tags=(tag,))

    def _re_popup_plat_menu(self) -> None:
        win = ctk.CTkToplevel(self)
        win.title("Plataformas")
        win.geometry("260x280")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        card = ctk.CTkFrame(win, fg_color="#182234")
        card.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(card, text="Filtro de Plataformas", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8").pack(pady=6)
        for p, var in self.re_plat_vars.items():
            ctk.CTkCheckBox(card, text=p, variable=var, font=ctk.CTkFont(size=11), fg_color="#0284c7").pack(anchor="w", padx=16, pady=4)
        ctk.CTkButton(card, text="OK", width=80, height=26, fg_color="#10b981", command=lambda: (win.destroy(), self._re_atualizar_kpis())).pack(pady=10)
        win.grab_set()

    def _re_popup_camp_menu(self) -> None:
        win = ctk.CTkToplevel(self)
        win.title("Campeonatos")
        win.geometry("280x340")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        card = ctk.CTkFrame(win, fg_color="#182234")
        card.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(card, text="Filtro de Campeonatos", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8").pack(pady=6)
        for c, var in self.re_camp_vars.items():
            ctk.CTkCheckBox(card, text=c, variable=var, font=ctk.CTkFont(size=11), fg_color="#0284c7").pack(anchor="w", padx=16, pady=3)
        ctk.CTkButton(card, text="OK", width=80, height=26, fg_color="#10b981", command=win.destroy).pack(pady=10)
        win.grab_set()

    # ── MÉTODOS DE LOGS ───────────────────────────────────────────────────────

    def _re_filtrar_logs(self) -> None:
        for i in self.re_tree_logs.get_children():
            self.re_tree_logs.delete(i)

        # Procura por log.txt em config/, na raiz ou em logs/
        candidatos = [
            get_config_dir() / "log.txt",
            get_base_dir() / "log.txt",
            get_base_dir() / "logs" / "app.log",
        ]
        log_path = None
        for c in candidatos:
            if c.exists() and os.path.getsize(c) > 0:
                log_path = c
                break

        if not log_path:
            log_path = get_app_path("log.txt")
            if not os.path.exists(log_path):
                return

        tipo_filtro = self.re_log_tipo_var.get().strip().upper()
        if tipo_filtro == "TODOS": tipo_filtro = ""

        try:
            d_ini = datetime.strptime(self.re_log_data_ini.get().strip(), "%d/%m/%Y")
            d_fim = datetime.strptime(self.re_log_data_fim.get().strip(), "%d/%m/%Y").replace(hour=23, minute=59, second=59)
        except Exception:
            d_ini = datetime.min
            d_fim = datetime.max

        linhas_filtradas = []
        todas_linhas_brutas = []

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    todas_linhas_brutas.append(line)

                    # Formato 1: YYYY-MM-DD HH:MM:SS - NIVEL - arquivo.py 123 - mensagem
                    partes = line.split(" - ", 2)
                    if len(partes) >= 3:
                        dt_str = partes[0].strip()
                        nivel = partes[1].strip().upper()
                        rest = partes[2].strip()

                        m_lin = re.search(r'\b(?:line|linha)\s+(\d+)|(\w+\.py)\s+(\d+)', rest, re.I)
                        linha_str = "-"
                        if m_lin:
                            linha_str = m_lin.group(1) or m_lin.group(3) or "-"
                            msg_limpa = re.sub(r'(\w+\.py\s*)?line \d+|[\w/\\]+\.py \d+\s*-\s*', '', rest, flags=re.I).strip()
                        else:
                            msg_limpa = rest

                        try:
                            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                            if tipo_filtro and nivel != tipo_filtro:
                                continue
                            if d_ini <= dt <= d_fim:
                                linhas_filtradas.append((dt, nivel, linha_str, msg_limpa))
                        except Exception:
                            pass
                    else:
                        m = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[?(\w+)\]?\s*(.*)', line)
                        if m:
                            dt_str, nivel, msg = m.groups()
                            try:
                                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                                if (not tipo_filtro or nivel.upper() == tipo_filtro) and (d_ini <= dt <= d_fim):
                                    linhas_filtradas.append((dt, nivel.upper(), "-", msg))
                            except Exception:
                                pass
        except Exception as e:
            logger.error(f"[ReporteEventos] Erro ao ler log.txt: {e}")

        if linhas_filtradas:
            linhas_filtradas.sort(key=lambda x: x[0], reverse=True)
            for dt, nivel, linha_num, msg in linhas_filtradas:
                tag = nivel if nivel in ["ERROR", "WARNING", "INFO"] else ""
                self.re_tree_logs.insert(
                    "", "end",
                    values=(dt.strftime("%d/%m/%Y %H:%M:%S"), nivel, linha_num, msg),
                    tags=(tag,)
                )
        elif todas_linhas_brutas:
            # Fallback inteligente: se a data inicial/final não cobrir os logs antigos, exibe as últimas linhas
            for raw in reversed(todas_linhas_brutas[-200:]):
                partes = raw.split(" - ", 2)
                if len(partes) >= 3:
                    dt_s, niv, rest = partes[0].strip(), partes[1].strip().upper(), partes[2].strip()
                    if tipo_filtro and niv != tipo_filtro: continue
                    tag = niv if niv in ["ERROR", "WARNING", "INFO"] else ""
                    self.re_tree_logs.insert("", "end", values=(dt_s, niv, "-", rest), tags=(tag,))
                else:
                    self.re_tree_logs.insert("", "end", values=("-", "INFO", "-", raw), tags=("INFO",))

    def _re_limpar_logs(self) -> None:
        if messagebox.askyesno("Limpar Logs", "Deseja esvaziar o arquivo log.txt?"):
            log_path = get_app_path("log.txt")
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
                self._re_filtrar_logs()
                messagebox.showinfo("Sucesso", "Logs limpos com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao limpar logs: {e}")

    def _re_exportar_logs(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path: return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Data/Hora", "Nível", "Linha", "Mensagem"])
                for i in self.re_tree_logs.get_children():
                    writer.writerow(self.re_tree_logs.item(i, "values"))
            messagebox.showinfo("Sucesso", "Logs exportados com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar logs: {e}")

    # ── MÉTODOS DE ACESSOS ────────────────────────────────────────────────────

    def _re_salvar_acessos(self) -> None:
        try:
            import xml.etree.ElementTree as ET
            trees = {}
            for tag, (entry, fname) in self.re_acessos_entries.items():
                p = get_app_path(fname)
                if p not in trees:
                    if os.path.exists(p):
                        trees[p] = ET.parse(p)
                    else:
                        root = ET.Element("configuration" if fname == "config.xml" else "auth")
                        trees[p] = ET.ElementTree(root)

                novo_val = entry.get().strip()
                if novo_val:
                    root = trees[p].getroot()
                    el = root.find(tag)
                    if el is None:
                        el = ET.SubElement(root, tag)
                    el.text = criptografar(novo_val)

            for p, tree in trees.items():
                tree.write(p, encoding="utf-8", xml_declaration=True)

            messagebox.showinfo("Sucesso", "Credenciais criptografadas e salvas com sucesso em config/!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar credenciais: {e}")

    # ── MÉTODOS DE CAMPEONATOS ────────────────────────────────────────────────

    def _re_reload_camps_tv(self) -> None:
        for i in self.re_tv_camps.get_children():
            self.re_tv_camps.delete(i)
        camps = carregar_campeonatos_config()
        for idx, c in enumerate(camps):
            ativo_str = "✅ Ativo" if c.get("ativo", True) else "❌ Pausado"
            tag = "even" if idx % 2 == 0 else "odd"
            self.re_tv_camps.insert("", "end", values=(c.get("campeonato", ""), c.get("plataforma", ""), c.get("url", ""), ativo_str), tags=(tag,))

    def _re_add_campeonato(self) -> None:
        self._re_modal_campeonato("Adicionar Campeonato")

    def _re_edit_campeonato(self) -> None:
        sel = self.re_tv_camps.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione um campeonato na tabela para editar.")
            return
        idx = self.re_tv_camps.index(sel[0])
        lista = carregar_campeonatos_config()
        if idx < len(lista):
            self._re_modal_campeonato("Editar Campeonato", lista[idx], idx)

    def _re_modal_campeonato(self, titulo: str, inicial: Optional[dict] = None, idx: Optional[int] = None) -> None:
        win = ctk.CTkToplevel(self)
        win.title(titulo)
        win.geometry("450x260")
        win.resizable(False, False)
        win.attributes("-topmost", True)

        card = ctk.CTkFrame(win, fg_color="#182234")
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(card, text="Nome do Campeonato:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w", padx=12, pady=(8, 2))
        e_nome = ctk.CTkEntry(card, width=400, height=30)
        e_nome.pack(padx=12, pady=2)

        ctk.CTkLabel(card, text="Plataforma / Canal:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w", padx=12, pady=(6, 2))
        cbo_plat = ctk.CTkOptionMenu(card, values=["Amazon Prime", "Disney", "Max", "Dazn", "Cazé TV"], width=400, height=30)
        cbo_plat.pack(padx=12, pady=2)

        ctk.CTkLabel(card, text="URL / Link Oficial:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w", padx=12, pady=(6, 2))
        e_url = ctk.CTkEntry(card, width=400, height=30)
        e_url.pack(padx=12, pady=2)

        if inicial:
            e_nome.insert(0, inicial.get("campeonato", ""))
            cbo_plat.set(inicial.get("plataforma", "Amazon Prime"))
            e_url.insert(0, inicial.get("url", ""))

        def _salvar():
            dados = {
                "campeonato": e_nome.get().strip(),
                "plataforma": cbo_plat.get().strip(),
                "url": e_url.get().strip(),
                "ativo": True if not inicial else inicial.get("ativo", True)
            }
            if not dados["campeonato"]:
                messagebox.showwarning("Aviso", "O nome do campeonato é obrigatório.")
                return
            lista = carregar_campeonatos_config()
            if idx is not None and idx < len(lista):
                lista[idx] = dados
            else:
                lista.append(dados)
            salvar_campeonatos_config(lista)
            self._re_reload_camps_tv()
            win.destroy()

        ctk.CTkButton(card, text="💾 Salvar", width=100, height=28, fg_color="#10b981", hover_color="#059669", command=_salvar).pack(pady=12)
        win.grab_set()

    def _re_remove_campeonato(self) -> None:
        sel = self.re_tv_camps.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione um campeonato para remover.")
            return
        idx = self.re_tv_camps.index(sel[0])
        lista = carregar_campeonatos_config()
        if idx < len(lista):
            if messagebox.askyesno("Confirmar Remoção", f"Deseja remover o campeonato '{lista[idx].get('campeonato')}'?"):
                lista.pop(idx)
                salvar_campeonatos_config(lista)
                self._re_reload_camps_tv()

    def _re_toggle_campeonato(self) -> None:
        sel = self.re_tv_camps.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione um campeonato para ativar/pausar.")
            return
        idx = self.re_tv_camps.index(sel[0])
        lista = carregar_campeonatos_config()
        if idx < len(lista):
            lista[idx]["ativo"] = not lista[idx].get("ativo", True)
            salvar_campeonatos_config(lista)
            self._re_reload_camps_tv()

    # ── MÉTODOS DE CANAIS YOUTUBE ─────────────────────────────────────────────

    def _re_reload_yt_tv(self) -> None:
        for i in self.re_tv_yt.get_children():
            self.re_tv_yt.delete(i)
        canais = carregar_youtube_channels_config()
        for idx, c in enumerate(canais):
            ativo_str = "✅ Ativo" if c.get("ativo", True) else "❌ Pausado"
            tag = "even" if idx % 2 == 0 else "odd"
            self.re_tv_yt.insert("", "end", values=(c.get("nome", ""), c.get("url", ""), ativo_str), tags=(tag,))

    def _re_add_yt_channel(self) -> None:
        self._re_modal_yt_channel("Adicionar Canal do YouTube")

    def _re_edit_yt_channel(self) -> None:
        sel = self.re_tv_yt.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione um canal para editar.")
            return
        idx = self.re_tv_yt.index(sel[0])
        canais = carregar_youtube_channels_config()
        if idx < len(canais):
            self._re_modal_yt_channel("Editar Canal do YouTube", canais[idx], idx)

    def _re_modal_yt_channel(self, titulo: str, inicial: Optional[dict] = None, idx: Optional[int] = None) -> None:
        win = ctk.CTkToplevel(self)
        win.title(titulo)
        win.geometry("450x220")
        win.resizable(False, False)
        win.attributes("-topmost", True)

        card = ctk.CTkFrame(win, fg_color="#182234")
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(card, text="Nome do Canal:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w", padx=12, pady=(8, 2))
        e_nome = ctk.CTkEntry(card, width=400, height=30)
        e_nome.pack(padx=12, pady=2)

        ctk.CTkLabel(card, text="URL do Canal (YouTube):", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w", padx=12, pady=(6, 2))
        e_url = ctk.CTkEntry(card, width=400, height=30)
        e_url.pack(padx=12, pady=2)

        if inicial:
            e_nome.insert(0, inicial.get("nome", ""))
            e_url.insert(0, inicial.get("url", ""))

        def _salvar():
            dados = {
                "nome": e_nome.get().strip(),
                "url": e_url.get().strip(),
                "ativo": True if not inicial else inicial.get("ativo", True)
            }
            if not dados["nome"] or not dados["url"]:
                messagebox.showwarning("Aviso", "Nome e URL são obrigatórios.")
                return
            canais = carregar_youtube_channels_config()
            if idx is not None and idx < len(canais):
                canais[idx] = dados
            else:
                canais.append(dados)
            salvar_youtube_channels_config(canais)
            self._re_reload_yt_tv()
            win.destroy()

        ctk.CTkButton(card, text="💾 Salvar", width=100, height=28, fg_color="#10b981", hover_color="#059669", command=_salvar).pack(pady=12)
        win.grab_set()

    def _re_remove_yt_channel(self) -> None:
        sel = self.re_tv_yt.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione um canal para remover.")
            return
        idx = self.re_tv_yt.index(sel[0])
        canais = carregar_youtube_channels_config()
        if idx < len(canais):
            if messagebox.askyesno("Confirmar Remoção", f"Deseja remover o canal '{canais[idx].get('nome')}'?"):
                canais.pop(idx)
                salvar_youtube_channels_config(canais)
                self._re_reload_yt_tv()

    def _re_toggle_yt_channel(self) -> None:
        sel = self.re_tv_yt.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione um canal.")
            return
        idx = self.re_tv_yt.index(sel[0])
        canais = carregar_youtube_channels_config()
        if idx < len(canais):
            canais[idx]["ativo"] = not canais[idx].get("ativo", True)
            salvar_youtube_channels_config(canais)
            self._re_reload_yt_tv()

    def _re_restore_default_yt_channels(self) -> None:
        if messagebox.askyesno("Restaurar Padrões", "Deseja restaurar os 6 canais padrão do YouTube?"):
            salvar_youtube_channels_config(DEFAULT_YOUTUBE_CHANNELS)
            self._re_reload_yt_tv()
            messagebox.showinfo("Sucesso", "Canais padrão restaurados com sucesso!")

    def _re_buscar_canais_youtube_agora(self) -> None:
        """Varre canais ativos, valida com a CBF e sincroniza diretamente no SharePoint."""
        def _task():
            try:
                self.re_lbl_status.configure(text="Varrendo transmissões dos canais do YouTube cadastrados...")
                canais = [c for c in carregar_youtube_channels_config() if c.get("ativo", True)]
                cbf_idx = get_cbf_rights_index()
                total_encontrados = 0
                for c in canais:
                    evs = obter_eventos_canal_youtube(c["nome"], c["url"], cbf_idx=cbf_idx)
                    for ev in evs:
                        self.after(0, lambda e=ev: self._re_inserir_evento_na_grade(e))
                        total_encontrados += 1

                # Sincronização direta no SharePoint
                self.re_lbl_status.configure(text="Sincronizando eventos validados com o SharePoint...")
                linhas = [list(self.re_tree.item(i, "values")) for i in self.re_tree.get_children()]
                sp_res = push_events_to_sharepoint(linhas)
                msg_final = f"Busca e publicação concluídas!\n• {total_encontrados} confrontos identificados nos canais.\n• {sp_res.get('inseridos', 0)} novos itens sincronizados no SharePoint."
                self.re_lbl_status.configure(text="Sincronização concluída.")
                self.after(0, lambda: messagebox.showinfo("SharePoint Sincronizado", msg_final))
            except Exception as e:
                err_msg = str(e)
                logger.error(f"[ReporteEventos] Erro ao buscar canais YouTube: {err_msg}")
                self.after(0, lambda msg=err_msg: messagebox.showerror("Erro", f"Falha na busca dos canais: {msg}"))

        threading.Thread(target=_task, daemon=True).start()
