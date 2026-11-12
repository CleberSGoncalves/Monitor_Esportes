# -*- coding: utf-8 -*-
"""
Mixin do Reporte de Eventos totalmente reconstruído para o Monitor_Esportes.
Design 100% integrado ao Padrão Dark Moderno da aplicação (CustomTkinter + Dark Treeview).
Velocidade otimizada: busca multicanal assíncrona, CBF (-1h), Copa do Mundo (-2h),
YouTube lives com validação CBF, sincronização SharePoint Graph API,
gestor de campeonatos pré-carregados, logs com cores dark e credenciais criptografadas.
"""

import os
import re
import csv
import json
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
)
from modules.reporte_eventos.email_report_service import (
    extrair_dados_html,
    enviar_email_relatorio,
)
from modules.reporte_eventos.sharepoint_client import (
    push_events_to_sharepoint,
    _deep_normalize_partida,
)
from modules.cbf_schedule_fetcher import CBFScheduleFetcher

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
        _re_set_cell(self.tv, self.rowid, self.col_idx, self.entry.get().strip())
        self.destroy()


# ── MIXIN RECONSTRUÍDO: REPORTE DE EVENTOS (DARK & ULTRA-RÁPIDO) ──────────────

class ReporteEventosMixin:
    """
    Mixin de alta performance totalmente estilizado no padrão dark do Monitor_Esportes.
    Reconstrói a aba Reporte de Eventos com visual limpo, fluido e responsivo.
    """

    def _init_reporte_eventos(self) -> None:
        """Inicializa variáveis e configurações locais."""
        cfg = carrega_config_xml()

        self.re_refresh_var = ctk.StringVar(value=cfg.get("refresh", "20"))
        self.re_data_inicio_var = ctk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self.re_email_var = ctk.StringVar(value=cfg.get("emails", ""))
        self.re_hora_auto_email_var = ctk.StringVar(value=cfg.get("hora_automatico", "09:00"))
        self.re_auto_email_var = ctk.BooleanVar(value=cfg.get("check_automatico_Email", False))
        self.re_auto_busca_var = ctk.BooleanVar(value=cfg.get("check_automatico_Evento", False))
        self.re_somente_relatorio_var = ctk.BooleanVar(value=cfg.get("somente_relatorio", False))

        # Plataformas
        self.re_plat_vars = {}
        plats = cfg.get("plataformas", {})
        for p in ["Amazon Prime", "Disney", "Cazé TV", "Dazn", "Max", "CBF"]:
            self.re_plat_vars[p] = ctk.BooleanVar(value=plats.get(p, p in ("Amazon Prime", "Cazé TV", "CBF")))

        # Campeonatos
        self.re_camp_vars = {}
        camps = cfg.get("campeonatos", {})
        padroes_camp = [
            "Brasileirão serie A", "Brasileirão serie B", "Copa do Brasil",
            "Copa do Mundo", "Mundial de Clubes FIFA", "Campeonato Paulista",
            "CONMEBOL Libertadores", "CONMEBOL Sudamericana"
        ]
        for c in padroes_camp:
            self.re_camp_vars[c] = ctk.BooleanVar(value=camps.get(c, True))

        self.re_is_running = False
        self.re_loop_job_id = None
        self.re_busy = False

    def _build_tab_reporte_eventos(self) -> None:
        """Constrói a interface dark moderna de Reporte de Eventos sob self.tab_reporte."""
        if not hasattr(self, "tab_reporte") or not self.tab_reporte:
            return

        # Container mestre dark
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
            text_color="#ffffff"
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

        # Constrói cada tela
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
            background=[("selected", "#0284c7")],
            foreground=[("selected", "#ffffff")]
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

    # ── SUB-ABA 1: STREAMING (RECONSTRUÍDA) ───────────────────────────────────

    def _build_modern_subtab_streaming(self, parent: ctk.CTkFrame) -> None:
        # Container superior de controles
        ctrl_card = ctk.CTkFrame(parent, fg_color="#182234", corner_radius=10, border_width=1, border_color="#2b3b55")
        ctrl_card.pack(fill="x", padx=6, pady=(4, 6))

        # Linha 1: Start/Stop, Refresh, Data Início, Abrir/Salvar, Filtros, Buscar e Limpar
        r1 = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=(8, 4))

        self.re_btn_start = ctk.CTkButton(
            r1, text="▶ Start", width=95, height=32,
            fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._re_toggle_start
        )
        self.re_btn_start.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(r1, text="Refresh(s):", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(side="left", padx=(4, 2))
        self.re_entry_refresh = ctk.CTkEntry(r1, textvariable=self.re_refresh_var, width=45, height=28, justify="center")
        self.re_entry_refresh.pack(side="left", padx=2)

        ctk.CTkLabel(r1, text="Data Início:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(side="left", padx=(8, 2))
        self.re_entry_data = ctk.CTkEntry(r1, textvariable=self.re_data_inicio_var, width=90, height=28, justify="center")
        self.re_entry_data.pack(side="left", padx=2)
        self.re_entry_data.bind("<KeyRelease>", self._re_formatar_data)

        ctk.CTkButton(r1, text="📂 Abrir CSV", width=85, height=28, fg_color="#334155", hover_color="#475569", command=self._re_abrir_csv).pack(side="left", padx=(10, 2))
        ctk.CTkButton(r1, text="💾 Salvar CSV", width=85, height=28, fg_color="#0284c7", hover_color="#0369a1", command=self._re_salvar_csv).pack(side="left", padx=2)

        self.re_cbo_plat = ctk.CTkButton(
            r1, text="📺 Plataformas ▾", width=125, height=28,
            fg_color="#1e293b", hover_color="#334155", border_width=1, border_color="#475569",
            command=self._re_popup_plat_menu
        )
        self.re_cbo_plat.pack(side="left", padx=(10, 2))

        self.re_cbo_camp = ctk.CTkButton(
            r1, text="🏆 Campeonatos ▾", width=130, height=28,
            fg_color="#1e293b", hover_color="#334155", border_width=1, border_color="#475569",
            command=self._re_popup_camp_menu
        )
        self.re_cbo_camp.pack(side="left", padx=2)

        # Botão Buscar Eventos com Destaque
        self.re_btn_buscar = ctk.CTkButton(
            r1, text="🔍 Buscar Eventos", width=140, height=32,
            fg_color="#00CED1", hover_color="#008B8B", text_color="#0f172a", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._re_buscar_eventos
        )
        self.re_btn_buscar.pack(side="left", padx=(12, 4))

        ctk.CTkButton(r1, text="Limpar", width=65, height=32, fg_color="#ef4444", hover_color="#dc2626", command=self._re_limpar_tree).pack(side="left", padx=2)

        # Linha 2: E-mails, automações, navegadores e linha +/-
        r2 = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=(2, 8))

        ctk.CTkLabel(r2, text="Destinatários:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(side="left", padx=(0, 2))
        self.re_entry_email = ctk.CTkEntry(r2, textvariable=self.re_email_var, width=230, height=28)
        self.re_entry_email.pack(side="left", padx=2)

        ctk.CTkButton(r2, text="✉️ Disparar E-mail", width=115, height=28, fg_color="#059669", hover_color="#047857", command=lambda: self._re_enviar_email(forcar=True)).pack(side="left", padx=(4, 8))

        ctk.CTkCheckBox(r2, text="Auto E-mail às:", variable=self.re_auto_email_var, font=ctk.CTkFont(size=11), fg_color="#0284c7").pack(side="left", padx=(6, 2))
        ctk.CTkEntry(r2, textvariable=self.re_hora_auto_email_var, width=50, height=28, justify="center").pack(side="left", padx=2)

        ctk.CTkCheckBox(r2, text="Auto Busca", variable=self.re_auto_busca_var, font=ctk.CTkFont(size=11), fg_color="#0284c7").pack(side="left", padx=(10, 2))
        ctk.CTkCheckBox(r2, text="Somente Relatório", variable=self.re_somente_relatorio_var, font=ctk.CTkFont(size=11), fg_color="#0284c7").pack(side="left", padx=(8, 2))

        ctk.CTkButton(r2, text="🌐 Chrome 9222", width=100, height=28, fg_color="#334155", hover_color="#475569", command=lambda: self._re_toggle_chrome("9222")).pack(side="left", padx=(10, 2))
        ctk.CTkButton(r2, text="🌐 Chrome 9224", width=100, height=28, fg_color="#334155", hover_color="#475569", command=lambda: self._re_toggle_chrome("9224")).pack(side="left", padx=2)

        ctk.CTkButton(r2, text="➕", width=32, height=28, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"), command=self._re_add_row).pack(side="left", padx=(10, 2))
        ctk.CTkButton(r2, text="➖", width=32, height=28, fg_color="#ef4444", hover_color="#dc2626", font=ctk.CTkFont(size=12, weight="bold"), command=self._re_delete_row).pack(side="left", padx=2)

        # Grade Principal de Eventos (Dark Treeview)
        grid_card = ctk.CTkFrame(parent, fg_color="#182234", corner_radius=10, border_width=1, border_color="#2b3b55")
        grid_card.pack(fill="both", expand=True, padx=6, pady=4)

        columns = ("Campeonato", "Partida", "Data", "Horário", "Navegador", "Min antes", "Canal de Transmissão", "Url")
        self.re_tree = ttk.Treeview(grid_card, columns=columns, show="headings", style="Reporte.Treeview", height=14)

        col_widths = [180, 270, 95, 75, 85, 85, 170, 260]
        for col, w in zip(columns, col_widths):
            self.re_tree.heading(col, text=col, command=lambda c=col: self._re_sort_tree(c))
            self.re_tree.column(col, width=w, anchor=CENTER if col not in ("Partida", "Url") else W)

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

        # Toolbar Inferior de Telemetria e Progresso
        self.re_toolbar = ctk.CTkFrame(parent, height=32, fg_color="#182234", corner_radius=8, border_width=1, border_color="#2b3b55")
        self.re_toolbar.pack(side="bottom", fill="x", padx=6, pady=(4, 2))

        self.re_lbl_status = ctk.CTkLabel(self.re_toolbar, text="Pronto para monitoramento.", font=ctk.CTkFont(size=11), text_color="#94a3b8")
        self.re_lbl_status.pack(side="left", padx=12, pady=4)

        self.re_progresso = ctk.CTkProgressBar(self.re_toolbar, width=200, height=10, progress_color="#00CED1")
        self.re_progresso.set(0.0)
        self.re_progresso.pack(side="right", padx=12, pady=6)

        self.re_lbl_process = ctk.CTkLabel(self.re_toolbar, text="", font=ctk.CTkFont(size=11), text_color="#38bdf8")
        self.re_lbl_process.pack(side="right", padx=6, pady=4)

        # Carrega dados salvos com pequeno delay
        self.after(200, self._re_carregar_dados_iniciais)

    # ── SUB-ABA 2: LOGS ───────────────────────────────────────────────────────

    def _build_modern_subtab_logs(self, parent: ctk.CTkFrame) -> None:
        ctrl = ctk.CTkFrame(parent, fg_color="#182234", corner_radius=10, border_width=1, border_color="#2b3b55")
        ctrl.pack(fill="x", padx=6, pady=6)

        r = ctk.CTkFrame(ctrl, fg_color="transparent")
        r.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(r, text="Nível:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(side="left", padx=4)
        self.re_log_tipo_var = ctk.StringVar(value="TODOS")
        cbo = ctk.CTkOptionMenu(r, variable=self.re_log_tipo_var, values=["TODOS", "ERROR", "WARNING", "INFO"], width=100, height=28)
        cbo.pack(side="left", padx=4)

        ctk.CTkLabel(r, text="Início:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(side="left", padx=(10, 4))
        cal_box1 = tk.Frame(r, bg="#182234")
        cal_box1.pack(side="left")
        self.re_log_data_ini = DateEntry(cal_box1, width=11, date_pattern="dd/MM/yyyy", locale="pt_BR")
        self.re_log_data_ini.set_date(datetime.now())
        self.re_log_data_ini.pack(padx=2)

        ctk.CTkLabel(r, text="Fim:", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(side="left", padx=(10, 4))
        cal_box2 = tk.Frame(r, bg="#182234")
        cal_box2.pack(side="left")
        self.re_log_data_fim = DateEntry(cal_box2, width=11, date_pattern="dd/MM/yyyy", locale="pt_BR")
        self.re_log_data_fim.set_date(datetime.now())
        self.re_log_data_fim.pack(padx=2)

        ctk.CTkButton(r, text="🔍 Filtrar", width=80, height=28, fg_color="#0284c7", hover_color="#0369a1", command=self._re_filtrar_logs).pack(side="left", padx=12)
        ctk.CTkButton(r, text="🧹 Limpar Logs", width=105, height=28, fg_color="#ef4444", hover_color="#dc2626", command=self._re_limpar_logs).pack(side="left", padx=4)
        ctk.CTkButton(r, text="📤 Exportar CSV", width=105, height=28, fg_color="#059669", hover_color="#047857", command=self._re_exportar_logs).pack(side="left", padx=4)

        # Grade de Logs
        grid_card = ctk.CTkFrame(parent, fg_color="#182234", corner_radius=10, border_width=1, border_color="#2b3b55")
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
        self.re_tree_logs.configure(yscrollcommand=vsb.set)
        self.re_tree_logs.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        vsb.pack(side="right", fill="y", padx=(0, 6), pady=6)

        self.re_tree_logs.tag_configure("ERROR", background="#451a1a", foreground="#fca5a5")
        self.re_tree_logs.tag_configure("WARNING", background="#422006", foreground="#fde047")
        self.re_tree_logs.tag_configure("INFO", background="#14532d", foreground="#86efac")

        self.after(300, self._re_filtrar_logs)

    # ── SUB-ABA 3: ACESSOS (RECONSTRUÍDA COM VISUAL DARK) ─────────────────────

    def _build_modern_subtab_acessos(self, parent: ctk.CTkFrame) -> None:
        scroll = ctk.CTkScrollableFrame(parent, fg_color="#182234", corner_radius=10, border_width=1, border_color="#2b3b55")
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(scroll, text="🔐 Credenciais Criptografadas de Plataformas & SMTP", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkLabel(scroll, text="Os dados são gravados localmente em config/ com criptografia simétrica Fernet (AES).", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w", padx=16, pady=(0, 16))

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
            card_p = ctk.CTkFrame(scroll, fg_color="#1e293b", corner_radius=8, border_width=1, border_color="#334155")
            card_p.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(card_p, text=plat_nome, font=ctk.CTkFont(size=12, weight="bold"), text_color="#00CED1", width=220, anchor="w").pack(side="left", padx=12, pady=10)

            val_u = get_config_value(tag_u) if fname == "config.xml" else get_auth_value(tag_u)
            val_p = get_config_value(tag_p) if fname == "config.xml" else get_auth_value(tag_p)

            e_u = ctk.CTkEntry(card_p, width=220, height=28, placeholder_text="Usuário / E-mail")
            if val_u: e_u.insert(0, val_u)
            e_u.pack(side="left", padx=6, pady=10)

            e_p = ctk.CTkEntry(card_p, width=200, height=28, placeholder_text="Senha / Token", show="*")
            if val_p: e_p.insert(0, val_p)
            e_p.pack(side="left", padx=6, pady=10)

            self.re_acessos_entries[tag_u] = (e_u, fname)
            self.re_acessos_entries[tag_p] = (e_p, fname)

        # Botão Salvar
        btn_salvar = ctk.CTkButton(
            scroll, text="💾 Salvar Todas as Credenciais", width=240, height=36,
            fg_color="#059669", hover_color="#047857", font=ctk.CTkFont(size=13, weight="bold"),
            command=self._re_salvar_acessos
        )
        btn_salvar.pack(pady=20)

    # ── SUB-ABA 4: CAMPEONATOS (PRÉ-CARREGADOS & OPERANTES) ───────────────────

    def _build_modern_subtab_campeonatos(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color="#182234", corner_radius=10, border_width=1, border_color="#2b3b55")
        header.pack(fill="x", padx=6, pady=6)

        top_r = ctk.CTkFrame(header, fg_color="transparent")
        top_r.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(top_r, text="🏆 Gestão de Campeonatos Oficiais & Extras", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8").pack(side="left")

        ctk.CTkButton(top_r, text="➕ Adicionar", width=95, height=28, fg_color="#10b981", hover_color="#059669", command=self._re_add_campeonato).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="✏️ Editar", width=85, height=28, fg_color="#0284c7", hover_color="#0369a1", command=self._re_edit_campeonato).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="🗑️ Remover", width=85, height=28, fg_color="#ef4444", hover_color="#dc2626", command=self._re_remove_campeonato).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="🔄 Ativar/Pausar", width=110, height=28, fg_color="#334155", hover_color="#475569", command=self._re_toggle_campeonato).pack(side="right", padx=3)

        # Grade de Campeonatos
        grid_card = ctk.CTkFrame(parent, fg_color="#182234", corner_radius=10, border_width=1, border_color="#2b3b55")
        grid_card.pack(fill="both", expand=True, padx=6, pady=4)

        cols = ("campeonato", "plataforma", "url", "ativo")
        self.re_tv_camps = ttk.Treeview(grid_card, columns=cols, show="headings", style="Reporte.Treeview", height=12)
        for col, hdr, w in zip(cols, ("Campeonato", "Plataforma / Canal", "URL / Fonte", "Status"), (240, 160, 580, 80)):
            self.re_tv_camps.heading(col, text=hdr)
            self.re_tv_camps.column(col, width=w, anchor=W if col != "ativo" else CENTER)

        vsb = ttk.Scrollbar(grid_card, orient="vertical", command=self.re_tv_camps.yview)
        self.re_tv_camps.configure(yscrollcommand=vsb.set)
        self.re_tv_camps.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        vsb.pack(side="right", fill="y", padx=(0, 6), pady=6)

        self.after(200, self._re_reload_camps_tv)

    # ── SUB-ABA 5: CANAIS YOUTUBE (PRÉ-CARREGADOS & OPERANTES) ─────────────────

    def _build_modern_subtab_youtube(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color="#182234", corner_radius=10, border_width=1, border_color="#2b3b55")
        header.pack(fill="x", padx=6, pady=6)

        top_r = ctk.CTkFrame(header, fg_color="transparent")
        top_r.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(top_r, text="📡 Canais do YouTube Monitorados (Validados pela CBF)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8").pack(side="left")

        ctk.CTkButton(top_r, text="🔍 Buscar Canais Agora", width=155, height=28, fg_color="#00CED1", hover_color="#008B8B", text_color="#0f172a", font=ctk.CTkFont(size=11, weight="bold"), command=self._re_buscar_canais_youtube_agora).pack(side="right", padx=(8, 0))
        ctk.CTkButton(top_r, text="🔄 Padrões", width=80, height=28, fg_color="#334155", hover_color="#475569", command=self._re_restore_default_yt_channels).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="🔄 Ativar/Pausar", width=105, height=28, fg_color="#334155", hover_color="#475569", command=self._re_toggle_yt_channel).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="🗑️ Remover", width=85, height=28, fg_color="#ef4444", hover_color="#dc2626", command=self._re_remove_yt_channel).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="✏️ Editar", width=80, height=28, fg_color="#0284c7", hover_color="#0369a1", command=self._re_edit_yt_channel).pack(side="right", padx=3)
        ctk.CTkButton(top_r, text="➕ Adicionar", width=95, height=28, fg_color="#10b981", hover_color="#059669", command=self._re_add_yt_channel).pack(side="right", padx=3)

        # Grade de Canais
        grid_card = ctk.CTkFrame(parent, fg_color="#182234", corner_radius=10, border_width=1, border_color="#2b3b55")
        grid_card.pack(fill="both", expand=True, padx=6, pady=4)

        cols = ("nome", "url", "ativo")
        self.re_tv_yt = ttk.Treeview(grid_card, columns=cols, show="headings", style="Reporte.Treeview", height=12)
        for col, hdr, w in zip(cols, ("Nome do Canal", "URL do Canal", "Status"), (260, 720, 90)):
            self.re_tv_yt.heading(col, text=hdr)
            self.re_tv_yt.column(col, width=w, anchor=W if col != "ativo" else CENTER)

        vsb = ttk.Scrollbar(grid_card, orient="vertical", command=self.re_tv_yt.yview)
        self.re_tv_yt.configure(yscrollcommand=vsb.set)
        self.re_tv_yt.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        vsb.pack(side="right", fill="y", padx=(0, 6), pady=6)

        self.after(200, self._re_reload_yt_tv)

    # ── SUB-ABA 6: FAQ (DARK TEXTBOX) ─────────────────────────────────────────

    def _build_modern_subtab_faq(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, fg_color="#182234", corner_radius=10, border_width=1, border_color="#2b3b55")
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
• O botão 'Buscar Canais Agora' executa varredura profunda e sincroniza automaticamente a lista de itens com o SharePoint da emissora via Microsoft Graph API.

3. 🔐 Segurança de Credenciais & Portas
• Senhas e tokens de acesso são protegidos por criptografia simétrica Fernet.
• Navegadores de depuração (Chrome 9222 e 9224) contam com perfis isolados em profiles_chrome/ e encerramento seguro cirúrgico por PID, preservando todas as demais tarefas do usuário no Windows.
"""
        txt.insert("1.0", faq_content)
        txt.configure(state="disabled")

    # Aliases de compatibilidade
    _build_subtab_streaming = _build_modern_subtab_streaming
    _build_subtab_logs = _build_modern_subtab_logs
    _build_subtab_acessos = _build_modern_subtab_acessos
    _build_subtab_campeonatos = _build_modern_subtab_campeonatos
    _build_subtab_youtube_channels = _build_modern_subtab_youtube
    _build_subtab_faq = _build_modern_subtab_faq

    # ── MÉTODOS DE AÇÃO E BUSCA DE ALTA VELOCIDADE ───────────────────────────

    def _re_buscar_eventos(self) -> None:
        """Executa a busca unificada de eventos de forma assíncrona, robusta e ultrarrápida."""
        if self.re_busy:
            messagebox.showinfo("Aviso", "Uma busca de eventos já está em processamento.")
            return

        self.re_busy = True
        self.re_btn_buscar.configure(state="disabled")
        self.re_lbl_status.configure(text="Iniciando varredura unificada...")
        self.re_progresso.set(0.1)

        # Captura variáveis na thread principal
        usar_cbf = bool(self.re_plat_vars.get("CBF") and self.re_plat_vars["CBF"].get())
        usar_copa = bool(self.re_camp_vars.get("Copa do Mundo") and self.re_camp_vars["Copa do Mundo"].get())
        usar_caze = bool(self.re_plat_vars.get("Cazé TV") and self.re_plat_vars["Cazé TV"].get())

        q = queue.Queue()

        def _worker():
            total_inseridos = 0
            try:
                # 1. Carrega CBF Schedule Oficial de alta velocidade via CBFScheduleFetcher
                if usar_cbf:
                    q.put(("status", "Carregando calendário oficial da CBF...", 0.2))
                    try:
                        fetcher = CBFScheduleFetcher()
                        matches = fetcher.get_upcoming_matches()
                        for m in matches:
                            t1 = m.get("team1") or m.get("home_team") or ""
                            t2 = m.get("team2") or m.get("away_team") or ""
                            if not t1 or not t2: continue
                            jogo = prettify_match_name(f"{t1} x {t2}")
                            camp = m.get("comp") or "Brasileirão serie A"
                            data = m.get("date") or datetime.now().strftime("%d/%m/%Y")
                            hora = m.get("time") or "19:00"
                            tv = m.get("broadcaster") or m.get("platform") or "Amazon Prime"
                            url = m.get("url") or ""
                            tup = (camp, jogo, data, hora, "Esquerda", "15", tv, url)
                            q.put(("event", tup))
                            total_inseridos += 1
                    except Exception as e_cbf:
                        logger.warning(f"[ReporteEventos] Aviso CBF Fetcher: {e_cbf}")
                    q.put(("progress", 0.4))

                # 2. Copa do Mundo FIFA 2026 (Planilha Excel com -2 Horas)
                if usar_copa:
                    q.put(("status", "Lendo planilha da Copa do Mundo FIFA 2026...", 0.5))
                    try:
                        xls_p = get_app_path("Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx")
                        if os.path.exists(xls_p):
                            copa_evs = parse_copa_mundo_excel(xls_p)
                            for c_ev in copa_evs:
                                tup = (c_ev["Camp"], c_ev["Jogo"], c_ev["Data"], c_ev["Hora"], "Esquerda", "15", c_ev["TV"], "")
                                q.put(("event", tup))
                                total_inseridos += 1
                    except Exception as e_copa:
                        logger.warning(f"[ReporteEventos] Aviso Copa do Mundo: {e_copa}")
                    q.put(("progress", 0.7))

                # 3. Varredura rápida de canais YouTube ativos
                if usar_caze:
                    q.put(("status", "Varrendo canal Cazé TV...", 0.8))
                    try:
                        caze_evs = obter_eventos_caze_tv()
                        for c_ev in caze_evs:
                            q.put(("event", c_ev))
                            total_inseridos += 1
                    except Exception as e_caze:
                        logger.warning(f"[ReporteEventos] Aviso Cazé TV: {e_caze}")

                msg_ok = f"Varredura concluída! {total_inseridos} eventos carregados com sucesso."
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
                    elif kind == "done_success":
                        self.re_progresso.set(1.0)
                        self.re_lbl_status.configure(text=msg[1])
                        messagebox.showinfo("Varredura Concluída", msg[1])
                    elif kind == "done_error":
                        messagebox.showerror("Erro", f"Falha na busca de eventos: {msg[1]}")
                    elif kind == "finished":
                        self.re_busy = False
                        self.re_btn_buscar.configure(state="normal")
                        self.re_lbl_process.configure(text="")
                        return
            except queue.Empty:
                pass
            if self.re_busy:
                self.after(50, _poll_queue)

        threading.Thread(target=_worker, daemon=True).start()
        self.after(50, _poll_queue)

    def _re_inserir_evento_na_grade(self, ev_tuple: tuple) -> None:
        """Insere tupla na grade evitando duplicatas por confronto e data."""
        partida = str(ev_tuple[1]).strip()
        data = str(ev_tuple[2]).strip()
        for item in self.re_tree.get_children():
            vals = self.re_tree.item(item, "values")
            if len(vals) >= 3 and str(vals[1]).strip() == partida and str(vals[2]).strip() == data:
                return
        idx = len(self.re_tree.get_children())
        tag = "even" if idx % 2 == 0 else "odd"
        self.re_tree.insert("", "end", values=ev_tuple, tags=(tag,))

    def _re_carregar_dados_iniciais(self) -> None:
        """Carrega dados existentes do arquivo streaming_data.csv na grade."""
        linhas = carregar_streaming_csv()
        for i in self.re_tree.get_children():
            self.re_tree.delete(i)
        for idx, r in enumerate(linhas):
            tag = "even" if idx % 2 == 0 else "odd"
            self.re_tree.insert("", "end", values=r, tags=(tag,))
        self.re_lbl_status.configure(text=f"Carregados {len(linhas)} eventos da base local streaming_data.csv.")

    def _re_salvar_csv(self) -> None:
        linhas = [list(self.re_tree.item(i, "values")) for i in self.re_tree.get_children()]
        salvar_streaming_csv(linhas)
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
            messagebox.showinfo("Sucesso", f"{len(linhas)} eventos importados com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir arquivo: {e}")

    def _re_limpar_tree(self) -> None:
        if messagebox.askyesno("Limpar Grade", "Deseja realmente limpar todos os eventos exibidos na grade?"):
            for i in self.re_tree.get_children():
                self.re_tree.delete(i)
            self.re_lbl_status.configure(text="Grade de eventos limpa.")

    _re_limpar_eventos = _re_limpar_tree

    def _re_add_row(self) -> None:
        hoje = datetime.now().strftime("%d/%m/%Y")
        nova_linha = ["Brasileirão serie A", "Novo Time A x Novo Time B", hoje, "19:00", "Esquerda", "15", "Amazon Prime", ""]
        tag = "even" if len(self.re_tree.get_children()) % 2 == 0 else "odd"
        self.re_tree.insert("", "end", values=nova_linha, tags=(tag,))

    def _re_delete_row(self) -> None:
        sel = self.re_tree.selection()
        if not sel: return
        for item in sel:
            self.re_tree.delete(item)

    def _re_toggle_chrome(self, porta: str) -> None:
        if verificar_chrome_debug(porta):
            fechar_chrome_seguro(porta)
            messagebox.showinfo("Chrome DevTools", f"Chrome da porta {porta} encerrado com segurança.")
        else:
            abrir_chrome(porta)
            messagebox.showinfo("Chrome DevTools", f"Chrome iniciado com porta de depuração {porta} ativa.")

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
        ctk.CTkButton(card, text="OK", width=80, height=26, fg_color="#10b981", command=win.destroy).pack(pady=10)
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

        log_path = get_app_path("log.txt")
        if not os.path.exists(log_path): return

        tipo_filtro = self.re_log_tipo_var.get().strip().upper()
        if tipo_filtro == "TODOS": tipo_filtro = ""

        try:
            d_ini = datetime.strptime(self.re_log_data_ini.get().strip(), "%d/%m/%Y")
            d_fim = datetime.strptime(self.re_log_data_fim.get().strip(), "%d/%m/%Y").replace(hour=23, minute=59, second=59)
        except Exception:
            d_ini = datetime.min
            d_fim = datetime.max

        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                m = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[?(\w+)\]?\s*(.*)', line)
                if m:
                    dt_str, nivel, msg = m.groups()
                    try:
                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                        if not (d_ini <= dt <= d_fim): continue
                    except Exception: pass
                    if tipo_filtro and nivel.upper() != tipo_filtro: continue
                    m_lin = re.search(r'\b(?:line|linha)\s+(\d+)', msg, re.I)
                    linha_str = m_lin.group(1) if m_lin else "-"
                    self.re_tree_logs.insert("", "end", values=(dt_str, nivel.upper(), linha_str, msg), tags=(nivel.upper(),))

    def _re_limpar_logs(self) -> None:
        if messagebox.askyesno("Limpar Logs", "Deseja esvaziar o arquivo log.txt?"):
            log_path = get_app_path("log.txt")
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
                self._re_filtrar_logs()
                messagebox.showinfo("Sucesso", "Logs esvaziados.")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao limpar logs: {e}")

    def _re_exportar_logs(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path: return
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Data/Hora", "Tipo", "Linha", "Mensagem"])
                for i in self.re_tree_logs.get_children():
                    w.writerow(self.re_tree_logs.item(i, "values"))
            messagebox.showinfo("Sucesso", f"Logs exportados com sucesso para:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na exportação: {e}")

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
                        rt = "auth" if fname == "auth.xml" else "credenciais"
                        root = ET.Element(rt)
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
                logger.error(f"[ReporteEventos] Erro ao buscar canais YouTube: {e}")
                self.after(0, lambda: messagebox.showerror("Erro", f"Falha na busca dos canais: {e}"))

        threading.Thread(target=_task, daemon=True).start()
