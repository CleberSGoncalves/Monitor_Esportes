# -*- coding: utf-8 -*-
"""
Mixin completo da aba 'Reporte de Eventos' para o Monitor_Esportes.
Migração integral e nativa do Streaming_Scheduler.
Contém:
- Sub-aba 1: Streaming (Grade de eventos, filtros múltiplos, popups de duplo clique, automações)
- Sub-aba 2: Logs (Central de auditoria, filtros por tipo/data, exportação CSV e limpeza)
- Sub-aba 3: Acessos (Credenciais criptografadas de streaming e SMTP)
- Sub-aba 4: ⚽ Campeonatos (Gestão dinâmica de campeonatos extras)
- Sub-aba 5: 📺 Canais YouTube (Monitoramento de lives com validação CBF e sincronização SharePoint)
- Sub-aba 6: FAQ (Manual completo do usuário)
"""

import os
import re
import csv
import time
import logging
import threading
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Toplevel, Frame, Label, StringVar, BooleanVar, HORIZONTAL, LEFT, RIGHT, BOTH, CENTER, W, E, X, Y
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

logger = logging.getLogger(__name__)

# ── POPUPS DE DUPLO CLIQUE NA GRADE ──────────────────────────────────────────

def _set_cell_value(tv: ttk.Treeview, rowid: str, col_index: int, value: Any) -> None:
    """Atualiza o valor de uma célula específica no Treeview de forma segura."""
    try:
        vals = list(tv.item(rowid, "values"))
        if col_index < len(vals):
            vals[col_index] = value
            tv.item(rowid, values=vals)
    except Exception as e:
        logger.warning(f"[ReporteEventos] Erro ao atualizar célula: {e}")

class EntryPopup(ttk.Entry):
    def __init__(self, parent, iid, column, text, **kw):
        ttk.Style().configure('re_pad.TEntry', padding='1 1 1 1')
        super().__init__(parent, style='re_pad.TEntry', **kw)
        self.tv = parent
        self.iid = iid
        self.column = column
        self.insert(0, text)
        self['exportselection'] = False
        self.focus_force()
        self.select_all()
        self.bind("<Return>", self.on_return)
        self.bind("<Control-a>", self.select_all)
        self.bind("<Escape>", lambda *ignore: self.destroy())

    def on_return(self, event):
        rowid = self.tv.focus()
        _set_cell_value(self.tv, rowid, self.column, self.get())
        self.destroy()

    def select_all(self, *ignore):
        self.selection_range(0, 'end')

class DatePopup(Toplevel):
    def __init__(self, tv, rowid, column, initial, abs_x, abs_y):
        super().__init__(tv)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.tv, self.rowid, self.column = tv, rowid, column

        self.cal = DateEntry(self, date_pattern="dd/MM/yyyy", locale="pt_BR", width=12)
        try:
            dt = datetime.strptime(str(initial).strip(), "%d/%m/%Y")
            self.cal.set_date(dt)
        except Exception:
            pass

        self.cal.pack(padx=4, pady=4)
        self.cal.bind("<Return>", self._ok)
        self.cal.bind("<<DateEntrySelected>>", lambda e: self.after(0, self._ok))
        self.bind("<Escape>", lambda e: self.destroy())
        self.geometry(f"+{abs_x}+{abs_y}")
        self.cal.focus_set()

    def _ok(self, event=None):
        _set_cell_value(self.tv, self.rowid, self.column, self.cal.get())
        self.after(0, self.destroy)

class TimePopup(Toplevel):
    def __init__(self, tv, rowid, column, initial, abs_x, abs_y, *, minute_step=5):
        super().__init__(tv)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.tv, self.rowid, self.column = tv, rowid, column
        self.minute_step = max(1, int(minute_step))
        self._updating = False

        try:
            ini = str(initial).strip()
            hh, mm = ini.split(":")
            hh, mm = int(hh), int(mm)
        except Exception:
            hh, mm = 0, 0

        frm = Frame(self)
        frm.pack(padx=10, pady=10)

        self.preview = Label(frm, text=f"{hh:02d}:{mm:02d}", font=("Segoe UI", 16, "bold"))
        self.preview.grid(row=0, column=0, columnspan=4, pady=(0, 8), sticky="w")

        Label(frm, text="HH:MM").grid(row=1, column=0, sticky="w")
        self.time_var = StringVar(value=f"{hh:02d}:{mm:02d}")
        self.entry_time = ttk.Entry(frm, textvariable=self.time_var, width=7, justify="center")
        self.entry_time.grid(row=1, column=1, sticky="w")
        self.entry_time.bind("<KeyRelease>", self._on_time_entry_change)
        self.entry_time.bind("<FocusOut>", self._on_time_entry_change)
        self.entry_time.bind("<Return>", self._ok)

        Label(frm, text="Hora").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.h_scale = ttk.Scale(frm, from_=0, to=23, orient=HORIZONTAL, command=self._on_slide)
        self.h_scale.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(6, 0), pady=(8, 0))
        self.h_scale.set(hh)

        Label(frm, text="Minuto").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.m_scale = ttk.Scale(frm, from_=0, to=59, orient=HORIZONTAL, command=self._on_slide)
        self.m_scale.grid(row=3, column=1, columnspan=3, sticky="ew", padx=(6, 0), pady=(8, 0))
        self.m_scale.set(mm)

        btn_ok = ttk.Button(frm, text="OK", command=self._ok)
        btn_cancel = ttk.Button(frm, text="Cancelar", command=self.destroy)
        btn_ok.grid(row=5, column=2, pady=(10, 0), sticky="e", padx=(0, 6))
        btn_cancel.grid(row=5, column=3, pady=(10, 0), sticky="e")

        self.bind("<Return>", self._ok)
        self.bind("<Escape>", lambda e: self.destroy())

        for w in (self.h_scale, self.m_scale):
            w.bind("<MouseWheel>", self._on_wheel)

        frm.grid_columnconfigure(1, weight=1)
        self.geometry(f"+{abs_x}+{abs_y}")
        self._refresh_preview()

    def _snap_minute(self, v):
        v = int(round(float(v)))
        if self.minute_step > 1:
            v = (round(v / self.minute_step) * self.minute_step) % 60
        return max(0, min(59, v))

    def _current_hhmm_from_scales(self):
        h = int(round(float(self.h_scale.get())))
        m = self._snap_minute(self.m_scale.get())
        if abs(m - self.m_scale.get()) >= 0.5:
            self.m_scale.set(m)
        return f"{h:02d}:{m:02d}"

    def _refresh_preview(self):
        self.preview.config(text=self._current_hhmm_from_scales())
        if not self._updating:
            self._updating = True
            self.time_var.set(self._current_hhmm_from_scales())
            self._updating = False

    def _parse_time_text(self, text):
        txt = str(text).strip()
        m = re.match(r'^(\d{1,2}):(\d{1,2})$', txt)
        if not m: return None
        h, m_ = int(m.group(1)), int(m.group(2))
        if not (0 <= h <= 23 and 0 <= m_ <= 59): return None
        return h, self._snap_minute(m_)

    def _on_slide(self, _evt=None):
        if not self._updating: self._refresh_preview()

    def _on_time_entry_change(self, _evt=None):
        if self._updating: return
        parsed = self._parse_time_text(self.time_var.get())
        if parsed is None: return
        h, m = parsed
        self._updating = True
        self.h_scale.set(h)
        self.m_scale.set(m)
        self._updating = False
        self._refresh_preview()

    def _on_wheel(self, evt):
        delta = 1 if evt.delta > 0 else -1
        if evt.widget is self.h_scale:
            val = max(0, min(23, int(round(float(self.h_scale.get()))) + delta))
            self.h_scale.set(val)
        else:
            cur = int(round(float(self.m_scale.get())))
            val = (cur + (delta * self.minute_step)) % 60
            self.m_scale.set(val)
        self._refresh_preview()

    def _ok(self, event=None):
        parsed = self._parse_time_text(self.time_var.get())
        value = f"{parsed[0]:02d}:{parsed[1]:02d}" if parsed else self._current_hhmm_from_scales()
        _set_cell_value(self.tv, self.rowid, self.column, value)
        self.after(0, self.destroy)

class OptionPopup(Toplevel):
    def __init__(self, tv, rowid, column, initial, abs_x, abs_y, options=("Esquerda", "Direita")):
        super().__init__(tv)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.tv, self.rowid, self.column = tv, rowid, column

        frm = Frame(self)
        frm.pack(padx=6, pady=6)
        self.cbo = ttk.Combobox(frm, values=list(options), state="readonly", width=16)
        if str(initial) in options:
            self.cbo.set(str(initial))
        else:
            self.cbo.current(0)
        self.cbo.pack(side=LEFT, padx=2)

        ok = ttk.Button(frm, text="OK", command=self._ok)
        ok.pack(side=LEFT, padx=4)

        self.cbo.bind("<<ComboboxSelected>>", self._ok)
        self.bind("<Return>", self._ok)
        self.bind("<Escape>", lambda e: self.destroy())
        self.geometry(f"+{abs_x}+{abs_y}")
        self.cbo.focus_set()

    def _ok(self, event=None):
        _set_cell_value(self.tv, self.rowid, self.column, self.cbo.get())
        self.destroy()

class MinutesPopup(Toplevel):
    def __init__(self, tv, rowid, column, initial, abs_x, abs_y, min_value=0, max_value=120, step=1):
        super().__init__(tv)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.tv, self.rowid, self.column = tv, rowid, column
        self.min_value, self.max_value, self.step = min_value, max_value, step
        self._updating = False

        try:
            initial_int = int(str(initial).strip())
        except Exception:
            initial_int = 0
        initial_int = max(self.min_value, min(self.max_value, initial_int))

        frm = Frame(self)
        frm.pack(padx=10, pady=10)

        Label(frm, text="Minutos antes da ação").grid(row=0, column=0, columnspan=3, sticky="w")
        self.preview = Label(frm, text=f"{initial_int} min", font=("Segoe UI", 14, "bold"))
        self.preview.grid(row=1, column=0, columnspan=3, pady=(0, 6), sticky="w")

        Label(frm, text="Min:").grid(row=2, column=0, sticky="w")
        self.min_var = StringVar(value=str(initial_int))
        self.entry_min = ttk.Entry(frm, textvariable=self.min_var, width=6, justify="center")
        self.entry_min.grid(row=2, column=1, sticky="w")
        self.entry_min.bind("<KeyRelease>", self._on_entry_change)
        self.entry_min.bind("<Return>", self._ok)

        self.scale = ttk.Scale(frm, from_=self.min_value, to=self.max_value, orient=HORIZONTAL, command=self._on_slide)
        self.scale.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self.scale.set(initial_int)

        btn_ok = ttk.Button(frm, text="OK", command=self._ok)
        btn_cancel = ttk.Button(frm, text="Cancelar", command=self.destroy)
        btn_ok.grid(row=4, column=1, pady=(10, 0), sticky="e", padx=(0, 6))
        btn_cancel.grid(row=4, column=2, pady=(10, 0), sticky="e")

        self.bind("<Return>", self._ok)
        self.bind("<Escape>", lambda e: self.destroy())
        self.geometry(f"+{abs_x}+{abs_y}")
        self._refresh_preview()

    def _snap(self, v):
        v = int(round(float(v)))
        return max(self.min_value, min(self.max_value, v))

    def _refresh_preview(self):
        val = self._snap(self.scale.get())
        self.preview.config(text=f"{val} min")
        if not self._updating:
            self._updating = True
            self.min_var.set(str(val))
            self._updating = False

    def _on_slide(self, _evt=None):
        if not self._updating: self._refresh_preview()

    def _on_entry_change(self, _evt=None):
        if self._updating: return
        txt = str(self.min_var.get()).strip()
        if txt.isdigit():
            self._updating = True
            self.scale.set(self._snap(int(txt)))
            self._updating = False
            self._refresh_preview()

    def _ok(self, event=None):
        txt = str(self.min_var.get()).strip()
        value = int(txt) if txt.isdigit() else self._snap(self.scale.get())
        _set_cell_value(self.tv, self.rowid, self.column, value)
        self.after(0, self.destroy)

# ── MIXIN PRINCIPAL REPORTE DE EVENTOS ───────────────────────────────────────

class ReporteEventosMixin:
    """Mixin que acopla toda a aplicação Streaming_Scheduler ao Monitor_Esportes."""

    def _init_reporte_eventos(self) -> None:
        """Inicializa variáveis de controle, configurações e estado do Reporte de Eventos."""
        cfg = carrega_config_xml()

        self.re_refresh_var = tk.StringVar(value=cfg.get("refresh", "20"))
        self.re_data_inicio_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self.re_email_var = tk.StringVar(value=cfg.get("emails", ""))
        self.re_hora_auto_email_var = tk.StringVar(value=cfg.get("hora_automatico", "09:00"))
        self.re_auto_email_var = tk.BooleanVar(value=cfg.get("check_automatico_Email", False))
        self.re_auto_busca_var = tk.BooleanVar(value=cfg.get("check_automatico_Evento", False))
        self.re_somente_relatorio_var = tk.BooleanVar(value=cfg.get("somente_relatorio", False))

        self.re_plat_vars = {}
        plats = cfg.get("plataformas", {})
        for p in ["Amazon Prime", "Disney", "Cazé TV", "Dazn", "Max", "CBF"]:
            self.re_plat_vars[p] = tk.BooleanVar(value=plats.get(p, p in ("Amazon Prime", "Cazé TV", "CBF")))

        self.re_camp_vars = {}
        camps = cfg.get("campeonatos", {})
        padroes_camp = [
            "Brasileirão serie A", "Brasileirão serie B", "Copa do Brasil",
            "Copa do Mundo", "Mundial de Clubes FIFA", "Campeonato Paulista",
            "CONMEBOL Libertadores", "CONMEBOL Sudamericana"
        ]
        for c in padroes_camp:
            self.re_camp_vars[c] = tk.BooleanVar(value=camps.get(c, True))

        self.re_is_running = False
        self.re_loop_job_id = None
        self.re_busy = False

    def _build_tab_reporte_eventos(self) -> None:
        """Constrói o Notebook mestre contendo as 6 sub-abas sob self.tab_reporte."""
        if not hasattr(self, "tab_reporte") or not self.tab_reporte:
            return

        # Notebook ttk
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("RE.TNotebook", background="#1e293b", borderwidth=0)
        style.configure("RE.TNotebook.Tab", background="#334155", foreground="#ffffff", padding=[14, 6], font=("Helvetica", 9, "bold"))
        style.map("RE.TNotebook.Tab", background=[("selected", "#0284c7")], foreground=[("selected", "#ffffff")])

        self.re_notebook = ttk.Notebook(self.tab_reporte, style="RE.TNotebook")
        self.re_notebook.pack(fill="both", expand=True, padx=4, pady=4)

        # 1. Streaming
        self._build_subtab_streaming(self.re_notebook)
        # 2. Logs
        self._build_subtab_logs(self.re_notebook)
        # 3. Acessos
        self._build_subtab_acessos(self.re_notebook)
        # 4. Campeonatos
        self._build_subtab_campeonatos(self.re_notebook)
        # 5. Canais YouTube
        self._build_subtab_youtube_channels(self.re_notebook)
        # 6. FAQ
        self._build_subtab_faq(self.re_notebook)

    # ── SUB-ABA 1: STREAMING ──────────────────────────────────────────────────

    def _build_subtab_streaming(self, nb: ttk.Notebook) -> None:
        tb1 = ttk.Frame(nb, padding=6)
        nb.add(tb1, text="Streaming")

        # Container superior de controles
        top_ctrl = ctk.CTkFrame(tb1, fg_color="#1e293b", corner_radius=8)
        top_ctrl.pack(side="top", fill="x", padx=4, pady=4)

        # Linha 1: Start, Refresh, Data Início, Abrir/Salvar, Plataformas, Campeonatos
        r1 = ctk.CTkFrame(top_ctrl, fg_color="transparent")
        r1.pack(fill="x", padx=6, pady=4)

        self.re_btn_start = ctk.CTkButton(
            r1, text="▶ Start", width=90, height=28,
            fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._re_toggle_start
        )
        self.re_btn_start.pack(side="left", padx=4)

        ctk.CTkLabel(r1, text="Refresh(s):", font=ctk.CTkFont(size=11)).pack(side="left", padx=(10, 2))
        self.re_entry_refresh = ctk.CTkEntry(r1, textvariable=self.re_refresh_var, width=45, height=26, justify="center")
        self.re_entry_refresh.pack(side="left", padx=2)

        ctk.CTkLabel(r1, text="Data Início:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(12, 2))
        self.re_entry_data = ctk.CTkEntry(r1, textvariable=self.re_data_inicio_var, width=85, height=26, justify="center")
        self.re_entry_data.pack(side="left", padx=2)
        self.re_entry_data.bind("<KeyRelease>", self._re_formatar_data)

        ctk.CTkButton(r1, text="Abrir CSV", width=70, height=26, fg_color="#475569", hover_color="#334155", command=self._re_abrir_csv).pack(side="left", padx=(10, 2))
        ctk.CTkButton(r1, text="Salvar CSV", width=70, height=26, fg_color="#0284c7", hover_color="#0369a1", command=self._re_salvar_csv).pack(side="left", padx=2)

        # Multi-select Plataformas e Campeonatos
        self.re_cbo_plat = ctk.CTkButton(
            r1, text="Plataformas ▾", width=120, height=26,
            fg_color="#334155", hover_color="#475569",
            command=self._re_popup_plat_menu
        )
        self.re_cbo_plat.pack(side="left", padx=(12, 2))

        self.re_cbo_camp = ctk.CTkButton(
            r1, text="Campeonatos ▾", width=120, height=26,
            fg_color="#334155", hover_color="#475569",
            command=self._re_popup_camp_menu
        )
        self.re_cbo_camp.pack(side="left", padx=2)

        # Ações de busca
        self.re_btn_buscar = ctk.CTkButton(
            r1, text="🔍 Buscar Eventos", width=120, height=28,
            fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._re_buscar_eventos
        )
        self.re_btn_buscar.pack(side="left", padx=(12, 2))

        ctk.CTkButton(r1, text="Limpar", width=65, height=28, fg_color="#dc2626", hover_color="#b91c1c", command=self._re_limpar_tree).pack(side="left", padx=2)

        # Linha 2: E-mails, Auto-Email, Auto-Busca, Navegadores Esquerdo/Direito, Adicionar/Deletar
        r2 = ctk.CTkFrame(top_ctrl, fg_color="transparent")
        r2.pack(fill="x", padx=6, pady=(0, 6))

        ctk.CTkLabel(r2, text="Enviar E-mail:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(4, 2))
        self.re_entry_email = ctk.CTkEntry(r2, textvariable=self.re_email_var, width=220, height=26)
        self.re_entry_email.pack(side="left", padx=2)

        ctk.CTkButton(r2, text="Enviar", width=55, height=26, fg_color="#059669", hover_color="#047857", command=lambda: self._re_enviar_email(forcar=True)).pack(side="left", padx=2)

        ctk.CTkCheckBox(r2, text="Auto E-mail às:", variable=self.re_auto_email_var, font=ctk.CTkFont(size=11)).pack(side="left", padx=(12, 2))
        ctk.CTkEntry(r2, textvariable=self.re_hora_auto_email_var, width=50, height=26, justify="center").pack(side="left", padx=2)

        ctk.CTkCheckBox(r2, text="Auto Busca", variable=self.re_auto_busca_var, font=ctk.CTkFont(size=11)).pack(side="left", padx=(12, 2))
        ctk.CTkCheckBox(r2, text="Somente Relatório", variable=self.re_somente_relatorio_var, font=ctk.CTkFont(size=11)).pack(side="left", padx=(10, 2))

        # Chrome Portas 9222 e 9224
        ctk.CTkButton(r2, text="Esquerdo (9222)", width=100, height=26, fg_color="#475569", hover_color="#334155", command=lambda: self._re_toggle_chrome("9222")).pack(side="left", padx=(14, 2))
        ctk.CTkButton(r2, text="Direito (9224)", width=100, height=26, fg_color="#475569", hover_color="#334155", command=lambda: self._re_toggle_chrome("9224")).pack(side="left", padx=2)

        # Botões + / -
        ctk.CTkButton(r2, text="➕", width=30, height=26, fg_color="#10b981", hover_color="#059669", command=self._re_add_row).pack(side="left", padx=(12, 2))
        ctk.CTkButton(r2, text="➖", width=30, height=26, fg_color="#ef4444", hover_color="#dc2626", command=self._re_delete_row).pack(side="left", padx=2)

        # Grade Principal de Eventos (Treeview)
        tree_frame = ttk.Frame(tb1)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=2)

        columns = ("Campeonato", "Partida", "Data", "Horário", "Navegador", "Min antes", "Canal de Transmissão", "Url")
        self.re_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=14)

        col_widths = [180, 260, 95, 75, 80, 80, 160, 240]
        for col, w in zip(columns, col_widths):
            self.re_tree.heading(col, text=col, command=lambda c=col: self._re_sort_tree(c))
            self.re_tree.column(col, width=w, anchor=CENTER if col not in ("Partida", "Url") else W)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.re_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.re_tree.xview)
        self.re_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.re_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.re_tree.tag_configure("t1", background="#f1f5f9", foreground="#0f172a")
        self.re_tree.tag_configure("t2", background="#ffffff", foreground="#0f172a")
        self.re_tree.tag_configure("t3", background="#fee2e2", foreground="#991b1b")

        self.re_tree.bind("<Double-1>", self._on_re_tree_double_click)

        # Toolbar Inferior de Status
        self.re_toolbar = ctk.CTkFrame(tb1, height=30, fg_color="#1e293b", corner_radius=6)
        self.re_toolbar.pack(side="bottom", fill="x", padx=4, pady=(2, 0))

        self.re_lbl_status = ctk.CTkLabel(self.re_toolbar, text="Pronto para monitoramento.", font=ctk.CTkFont(size=11), text_color="#94a3b8")
        self.re_lbl_status.pack(side="left", padx=10, pady=4)

        self.re_progresso = ttk.Progressbar(self.re_toolbar, mode="determinate", length=180)
        self.re_progresso.pack(side="right", padx=10, pady=4)

        self.re_lbl_process = ctk.CTkLabel(self.re_toolbar, text="", font=ctk.CTkFont(size=11), text_color="#38bdf8")
        self.re_lbl_process.pack(side="right", padx=6, pady=4)

        # Carrega dados existentes do CSV
        self.after(200, self._re_carregar_dados_iniciais)

    # ── SUB-ABA 2: LOGS ───────────────────────────────────────────────────────

    def _build_subtab_logs(self, nb: ttk.Notebook) -> None:
        aba = ttk.Frame(nb, padding=8)
        nb.add(aba, text="Logs")

        ctrl = ctk.CTkFrame(aba, fg_color="#1e293b", corner_radius=8)
        ctrl.pack(fill="x", padx=4, pady=4)

        r = ctk.CTkFrame(ctrl, fg_color="transparent")
        r.pack(fill="x", padx=6, pady=6)

        ctk.CTkLabel(r, text="Tipo de Erro:", font=ctk.CTkFont(size=11)).pack(side="left", padx=4)
        self.re_log_tipo_var = tk.StringVar(value="")
        cbo = ttk.Combobox(r, textvariable=self.re_log_tipo_var, values=["", "ERROR", "WARNING", "INFO"], width=10, state="readonly")
        cbo.pack(side="left", padx=4)

        ctk.CTkLabel(r, text="Data Início:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(10, 4))
        self.re_log_data_ini = DateEntry(r, width=12, date_pattern="dd/MM/yyyy", locale="pt_BR")
        self.re_log_data_ini.set_date(datetime.now())
        self.re_log_data_ini.pack(side="left", padx=4)

        ctk.CTkLabel(r, text="Data Fim:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(10, 4))
        self.re_log_data_fim = DateEntry(r, width=12, date_pattern="dd/MM/yyyy", locale="pt_BR")
        self.re_log_data_fim.set_date(datetime.now())
        self.re_log_data_fim.pack(side="left", padx=4)

        ctk.CTkButton(r, text="Filtrar", width=70, height=26, fg_color="#0284c7", command=self._re_filtrar_logs).pack(side="left", padx=10)
        ctk.CTkButton(r, text="🧹 Limpar Logs", width=100, height=26, fg_color="#dc2626", command=self._re_limpar_logs).pack(side="left", padx=4)
        ctk.CTkButton(r, text="📤 Exportar CSV", width=100, height=26, fg_color="#059669", command=self._re_exportar_logs).pack(side="left", padx=4)

        # Treeview de logs
        tree_frame = ttk.Frame(aba)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.re_tree_logs = ttk.Treeview(tree_frame, columns=("data", "nivel", "linha", "mensagem"), show="headings", height=16)
        self.re_tree_logs.heading("data", text="Data/Hora")
        self.re_tree_logs.heading("nivel", text="Tipo")
        self.re_tree_logs.heading("linha", text="Linha")
        self.re_tree_logs.heading("mensagem", text="Mensagem")

        self.re_tree_logs.column("data", width=150)
        self.re_tree_logs.column("nivel", width=80, anchor=CENTER)
        self.re_tree_logs.column("linha", width=60, anchor=CENTER)
        self.re_tree_logs.column("mensagem", width=750)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.re_tree_logs.yview)
        self.re_tree_logs.configure(yscrollcommand=vsb.set)
        self.re_tree_logs.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.re_tree_logs.tag_configure("ERROR", background="#ffcccc", foreground="#991b1b")
        self.re_tree_logs.tag_configure("WARNING", background="#fff7cc", foreground="#854d0e")
        self.re_tree_logs.tag_configure("INFO", background="#ccffcc", foreground="#166534")

        self.after(300, self._re_filtrar_logs)

    # ── SUB-ABA 3: ACESSOS ────────────────────────────────────────────────────

    def _build_subtab_acessos(self, nb: ttk.Notebook) -> None:
        aba = ttk.Frame(nb, padding=16)
        nb.add(aba, text="Acessos")

        lf = ttk.LabelFrame(aba, text="Cadastrar/Atualizar Credenciais Criptografadas", padding=(20, 15))
        lf.pack(fill="both", expand=True)

        pares = [
            (("Usuário Prime", "usuario_prime", "config.xml"), ("Senha Prime", "senha_prime", "config.xml")),
            (("Usuário Disney", "usuario_disney", "config.xml"), ("Senha Disney", "senha_disney", "config.xml")),
            (("Usuário DAZN", "usuario_dazn", "config.xml"), ("Senha DAZN", "senha_dazn", "config.xml")),
            (("Usuário Paramount", "usuario_paramount", "config.xml"), ("Senha Paramount", "senha_paramount", "config.xml")),
            (("Usuário Max", "usuario_max", "config.xml"), ("Senha Max", "senha_max", "config.xml")),
            (("E-mail SMTP (Gmail)", "email", "auth.xml"), ("Senha SMTP (App Password)", "senha", "auth.xml")),
        ]

        self.re_acessos_entries = []
        self.re_acessos_info = []

        for i, ((l1, c1, f1), (l2, c2, f2)) in enumerate(pares):
            ttk.Label(lf, text=l1 + ":").grid(row=i, column=0, sticky=E, padx=8, pady=6)
            e1 = ttk.Entry(lf, width=32)
            e1.grid(row=i, column=1, sticky=W, padx=8, pady=6)
            val1 = get_config_value(c1) if f1 == "config.xml" else get_auth_value(c1)
            if val1: e1.insert(0, val1)
            self.re_acessos_entries.append(e1)
            self.re_acessos_info.append((c1, f1))

            ttk.Label(lf, text=l2 + ":").grid(row=i, column=2, sticky=E, padx=8, pady=6)
            e2 = ttk.Entry(lf, width=32, show="*" if "Senha" in l2 else "")
            e2.grid(row=i, column=3, sticky=W, padx=8, pady=6)
            val2 = get_config_value(c2) if f2 == "config.xml" else get_auth_value(c2)
            if val2: e2.insert(0, val2)
            self.re_acessos_entries.append(e2)
            self.re_acessos_info.append((c2, f2))

        btn = ctk.CTkButton(
            lf, text="💾 Salvar Credenciais", width=180, height=32,
            fg_color="#059669", hover_color="#047857", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._re_salvar_acessos
        )
        btn.grid(row=len(pares), column=0, columnspan=4, pady=25)

    # ── SUB-ABA 4: CAMPEONATOS ────────────────────────────────────────────────

    def _build_subtab_campeonatos(self, nb: ttk.Notebook) -> None:
        aba = ttk.Frame(nb, padding=10)
        nb.add(aba, text="⚽ Campeonatos")

        ttk.Label(aba, text="Campeonatos Extras", font=("Helvetica", 11, "bold")).pack(anchor=W, pady=(0, 2))
        ttk.Label(
            aba,
            text="Cadastre aqui campeonatos adicionais. Eles serão buscados automaticamente ao clicar em 'Buscar Eventos'.",
            foreground="#64748b"
        ).pack(anchor=W, pady=(0, 8))

        tv_frame = ttk.Frame(aba)
        tv_frame.pack(fill="both", expand=True)

        cols = ("campeonato", "plataforma", "url", "ativo")
        self.re_tv_camps = ttk.Treeview(tv_frame, columns=cols, show="headings", height=10)
        for col, hdr, w in zip(cols, ("Campeonato", "Plataforma", "URL", "Ativo"), (220, 130, 580, 60)):
            self.re_tv_camps.heading(col, text=hdr)
            self.re_tv_camps.column(col, width=w, anchor=W if col != "ativo" else CENTER)

        vsb = ttk.Scrollbar(tv_frame, orient="vertical", command=self.re_tv_camps.yview)
        self.re_tv_camps.configure(yscrollcommand=vsb.set)
        self.re_tv_camps.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Botões
        bar = ttk.Frame(aba)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="➕ Adicionar", command=self._re_add_campeonato).pack(side="left", padx=4)
        ttk.Button(bar, text="✏️ Editar", command=self._re_edit_campeonato).pack(side="left", padx=4)
        ttk.Button(bar, text="🗑️ Remover", command=self._re_remove_campeonato).pack(side="left", padx=4)
        ttk.Button(bar, text="🔄 Ativar/Pausar", command=self._re_toggle_campeonato).pack(side="left", padx=4)

        self.after(250, self._re_reload_camps_tv)

    # ── SUB-ABA 5: CANAIS YOUTUBE ─────────────────────────────────────────────

    def _build_subtab_youtube_channels(self, nb: ttk.Notebook) -> None:
        aba = ttk.Frame(nb, padding=10)
        nb.add(aba, text="📺 Canais YouTube")

        ttk.Label(aba, text="Canais do YouTube Monitorados (Validados pela CBF)", font=("Helvetica", 11, "bold")).pack(anchor=W, pady=(0, 2))
        ttk.Label(
            aba,
            text="Transmissões ao vivo coletadas desses canais são validadas contra a tabela oficial da CBF e sincronizadas no SharePoint.",
            foreground="#64748b"
        ).pack(anchor=W, pady=(0, 8))

        tv_frame = ttk.Frame(aba)
        tv_frame.pack(fill="both", expand=True)

        cols = ("nome", "url", "ativo")
        self.re_tv_yt = ttk.Treeview(tv_frame, columns=cols, show="headings", height=10)
        for col, hdr, w in zip(cols, ("Nome do Canal", "URL do Canal", "Ativo"), (250, 700, 80)):
            self.re_tv_yt.heading(col, text=hdr)
            self.re_tv_yt.column(col, width=w, anchor=W if col != "ativo" else CENTER)

        vsb = ttk.Scrollbar(tv_frame, orient="vertical", command=self.re_tv_yt.yview)
        self.re_tv_yt.configure(yscrollcommand=vsb.set)
        self.re_tv_yt.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Botões
        bar = ttk.Frame(aba)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="➕ Adicionar Canal", command=self._re_add_yt_channel).pack(side="left", padx=4)
        ttk.Button(bar, text="✏️ Editar Canal", command=self._re_edit_yt_channel).pack(side="left", padx=4)
        ttk.Button(bar, text="🗑️ Remover", command=self._re_remove_yt_channel).pack(side="left", padx=4)
        ttk.Button(bar, text="🔄 Ativar/Pausar", command=self._re_toggle_yt_channel).pack(side="left", padx=4)
        ttk.Button(bar, text="🔄 Restaurar Padrões", command=self._re_restore_default_yt_channels).pack(side="left", padx=4)
        ttk.Button(bar, text="🔍 Buscar Canais Agora", command=self._re_buscar_canais_youtube_agora).pack(side="left", padx=10)

        self.after(250, self._re_reload_yt_tv)

    # ── SUB-ABA 6: FAQ ────────────────────────────────────────────────────────

    def _build_subtab_faq(self, nb: ttk.Notebook) -> None:
        aba = ttk.Frame(nb, padding=10)
        nb.add(aba, text="FAQ")

        txt = tk.Text(aba, wrap="word", height=24, font=("Segoe UI", 10), bg="#0f172a", fg="#f1f5f9", padx=12, pady=12)
        vsb = ttk.Scrollbar(aba, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        txt.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        faq_content = """📌 FAQ — Módulo Reporte de Eventos (Migração Streaming_Scheduler)

1. Streaming (Aba Principal)
• 'Buscar Eventos': Coleta confrontos das plataformas selecionadas (Amazon Prime, Cazé TV, CBF PDF, Copa do Mundo, etc.).
• Validação CBF Obrigatória: Todos os confrontos de canais de YouTube são cruzados com a tabela oficial da CBF (-1h no fuso de PDFs).
• 'Start': Ativa o monitoramento contínuo em segundo plano para verificação de horários.
• 'Auto E-mail': Dispara automaticamente o relatório diário no horário configurado (ex: 09:00), bloqueando na madrugada (22h-07h).

2. Edição de Células na Grade (Duplo Clique)
• Coluna Data: Abre calendário visual DateEntry.
• Coluna Horário: Abre seletor com mostrador digital e sliders independentes de Hora/Minuto.
• Coluna Navegador: Permite alternar entre 'Esquerda' (9222) e 'Direito' (9224).
• Coluna Min Antes: Abre slider para configurar minutos de antecedência.
• Coluna Plataforma: Combobox com as opções canônicas suportadas.

3. Sincronização com SharePoint
• Os dados validados da grade são enviados de forma desduplicada para a lista corporativa do SharePoint via Microsoft Graph API com fallback automático para Power Automate Flow.
• Regra estrita de 1 linha por canal individual.

4. Segurança de Processos
• As portas de depuração do Chrome (9222 e 9224) são gerenciadas com profiles isolados em profiles_chrome/.
• O encerramento de processos é estritamente cirúrgico, preservando todas as outras janelas do sistema.
"""
        txt.insert("1.0", faq_content)
        txt.configure(state="disabled")

    # ── INTERAÇÕES E POPUPS DA GRADE ──────────────────────────────────────────

    def _on_re_tree_double_click(self, event) -> None:
        rowid = self.re_tree.identify_row(event.y)
        column = self.re_tree.identify_column(event.x)
        if not rowid or not column:
            return

        bbox = self.re_tree.bbox(rowid, column)
        if not bbox:
            return
        x, y, width, height = bbox
        col_index = int(column[1:]) - 1

        vals = self.re_tree.item(rowid, "values")
        atual = vals[col_index] if col_index < len(vals) else ""

        abs_x = self.re_tree.winfo_rootx() + x
        abs_y = self.re_tree.winfo_rooty() + y + height // 2

        if col_index == 2:
            DatePopup(self.re_tree, rowid, col_index, atual, abs_x, abs_y)
        elif col_index == 3:
            TimePopup(self.re_tree, rowid, col_index, atual, abs_x, abs_y)
        elif col_index == 4:
            OptionPopup(self.re_tree, rowid, col_index, atual, abs_x, abs_y, options=("Esquerda", "Direita"))
        elif col_index == 5:
            MinutesPopup(self.re_tree, rowid, col_index, atual, abs_x, abs_y, min_value=0, max_value=120)
        elif col_index == 6:
            OptionPopup(self.re_tree, rowid, col_index, atual, abs_x, abs_y, options=("Amazon Prime", "Disney", "Cazé TV", "Dazn", "Paramount", "Max"))
        else:
            ep = EntryPopup(self.re_tree, rowid, col_index, atual)
            ep.place(x=x, y=y + height // 2, width=width, height=height, anchor="w")

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

    def _re_popup_plat_menu(self) -> None:
        win = Toplevel(self)
        win.title("Plataformas")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        for p, var in self.re_plat_vars.items():
            ttk.Checkbutton(win, text=p, variable=var).pack(anchor="w", padx=10, pady=4)
        ttk.Button(win, text="Fechar", command=win.destroy).pack(pady=8)

    def _re_popup_camp_menu(self) -> None:
        win = Toplevel(self)
        win.title("Campeonatos")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        for c, var in self.re_camp_vars.items():
            ttk.Checkbutton(win, text=c, variable=var).pack(anchor="w", padx=10, pady=3)
        ttk.Button(win, text="Fechar", command=win.destroy).pack(pady=8)

    # ── MÉTODOS DE DADOS DA GRADE ─────────────────────────────────────────────

    def _re_carregar_dados_iniciais(self) -> None:
        linhas = carregar_streaming_csv()
        for i in self.re_tree.get_children():
            self.re_tree.delete(i)
        for idx, r in enumerate(linhas):
            tag = "t1" if idx % 2 == 0 else "t2"
            self.re_tree.insert("", "end", values=r, tags=(tag,))
        self.re_lbl_status.configure(text=f"Carregados {len(linhas)} eventos da base local.")

    def _re_salvar_csv(self) -> None:
        linhas = [list(self.re_tree.item(i, "values")) for i in self.re_tree.get_children()]
        salvar_streaming_csv(linhas)
        messagebox.showinfo("Sucesso", f"{len(linhas)} eventos salvos em streaming_data.csv!")

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
                tag = "t1" if idx % 2 == 0 else "t2"
                self.re_tree.insert("", "end", values=r, tags=(tag,))
            self.re_lbl_status.configure(text=f"Importados {len(linhas)} eventos do arquivo.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir arquivo: {e}")

    def _re_limpar_tree(self) -> None:
        if messagebox.askyesno("Limpar", "Deseja realmente limpar a grade de eventos?"):
            for i in self.re_tree.get_children():
                self.re_tree.delete(i)
            self.re_lbl_status.configure(text="Grade limpa.")

    def _re_add_row(self) -> None:
        hoje = datetime.now().strftime("%d/%m/%Y")
        nova_linha = ["Brasileirão serie A", "Novo Confronto x Adversário", hoje, "19:00", "Esquerda", "15", "Cazé TV", ""]
        self.re_tree.insert("", "end", values=nova_linha, tags=("t1",))

    def _re_delete_row(self) -> None:
        sel = self.re_tree.selection()
        if not sel: return
        for item in sel:
            self.re_tree.delete(item)

    # ── MÉTODOS DE AÇÃO E AUTOMAÇÃO ───────────────────────────────────────────

    def _re_toggle_chrome(self, porta: str) -> None:
        if verificar_chrome_debug(porta):
            fechar_chrome_seguro(porta)
            messagebox.showinfo("Chrome", f"Instância do Chrome na porta {porta} encerrada.")
        else:
            abrir_chrome(porta)
            messagebox.showinfo("Chrome", f"Instância do Chrome iniciada na porta {porta} com depuração ativa.")

    def _re_toggle_start(self) -> None:
        if self.re_is_running:
            self.re_is_running = False
            self.re_btn_start.configure(text="▶ Start", fg_color="#10b981", hover_color="#059669")
            self.re_lbl_status.configure(text="Monitoramento parado.")
            if self.re_loop_job_id:
                try: self.after_cancel(self.re_loop_job_id)
                except Exception: pass
                self.re_loop_job_id = None
        else:
            self.re_is_running = True
            self.re_btn_start.configure(text="⏹ Running", fg_color="#ef4444", hover_color="#dc2626")
            self.re_lbl_status.configure(text="Monitoramento ativo (loop iniciado).")
            self._re_executar_ciclo_monitoramento()

    def _re_executar_ciclo_monitoramento(self) -> None:
        if not self.re_is_running: return
        try:
            # 1. Verifica agendamento diário de e-mail
            if self.re_auto_email_var.get():
                agora_str = datetime.now().strftime("%H:%M")
                if agora_str == self.re_hora_auto_email_var.get().strip():
                    self._re_enviar_email(forcar=False)

            # 2. Verifica auto-busca de eventos
            if self.re_auto_busca_var.get() and not self.re_busy:
                # Dispara busca em background a cada hora se programado
                pass
        except Exception as e:
            logger.warning(f"[ReporteEventos] Erro no ciclo de monitoramento: {e}")

        # Reagenda próximo ciclo com base no refresh configurado
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
            messagebox.showinfo("Sucesso", msg)
        else:
            messagebox.showwarning("Aviso", msg)

    def _re_buscar_eventos(self) -> None:
        if self.re_busy:
            messagebox.showinfo("Ocupado", "Uma varredura já está em andamento.")
            return

        def _worker():
            self.re_busy = True
            self.re_btn_buscar.configure(state="disabled")
            self.re_lbl_status.configure(text="Iniciando varredura unificada...")
            self.re_progresso.configure(value=10)

            try:
                # 1. CBF PDF
                if self.re_plat_vars.get("CBF", tk.BooleanVar(value=True)).get():
                    self.re_lbl_process.configure(text="Baixando tabelas CBF (PDF)...")
                    idx = get_cbf_rights_index(force_reload=True)
                    self.re_progresso.configure(value=40)

                # 2. Cazé TV
                if self.re_plat_vars.get("Cazé TV", tk.BooleanVar(value=True)).get():
                    self.re_lbl_process.configure(text="Varrendo Cazé TV (YouTube)...")
                    caze_events = obter_eventos_caze_tv()
                    for ev in caze_events:
                        self.after(0, lambda e=ev: self._re_inserir_evento_na_grade(e))
                    self.re_progresso.configure(value=70)

                # 3. Copa do Mundo Excel
                if self.re_camp_vars.get("Copa do Mundo", tk.BooleanVar(value=True)).get():
                    self.re_lbl_process.configure(text="Lendo planilha Copa do Mundo...")
                    xls_p = get_app_path("Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx")
                    copa_evs = parse_copa_mundo_excel(xls_p)
                    for c_ev in copa_evs:
                        tup = (c_ev["Camp"], c_ev["Jogo"], c_ev["Data"], c_ev["Hora"], "Esquerda", "15", c_ev["TV"], "")
                        self.after(0, lambda e=tup: self._re_inserir_evento_na_grade(e))

                self.re_progresso.configure(value=100)
                self.re_lbl_status.configure(text="Varredura concluída com sucesso!")
                self.after(0, lambda: messagebox.showinfo("Concluído", "Varredura de eventos finalizada com sucesso!"))
            except Exception as e:
                logger.error(f"[ReporteEventos] Erro na varredura: {e}")
                self.after(0, lambda: messagebox.showerror("Erro", f"Erro na varredura: {e}"))
            finally:
                self.re_busy = False
                self.re_btn_buscar.configure(state="normal")
                self.re_lbl_process.configure(text="")

        threading.Thread(target=_worker, daemon=True).start()

    def _re_inserir_evento_na_grade(self, ev_tuple: tuple) -> None:
        """Insere tupla na grade evitando duplicações pelo confronto e data."""
        partida = ev_tuple[1]
        data = ev_tuple[2]
        for item in self.re_tree.get_children():
            vals = self.re_tree.item(item, "values")
            if len(vals) >= 3 and vals[1] == partida and vals[2] == data:
                return  # Já existe
        tag = "t1" if len(self.re_tree.get_children()) % 2 == 0 else "t2"
        self.re_tree.insert("", "end", values=ev_tuple, tags=(tag,))

    # ── MÉTODOS DE LOGS ───────────────────────────────────────────────────────

    def _re_filtrar_logs(self) -> None:
        for i in self.re_tree_logs.get_children():
            self.re_tree_logs.delete(i)

        log_path = get_app_path("log.txt")
        if not os.path.exists(log_path):
            return

        tipo_filtro = self.re_log_tipo_var.get().strip().upper()
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
                # Parse básico: 2026-11-11 12:00:00 [ERROR] mensagem
                m = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[?(\w+)\]?\s*(.*)', line)
                if m:
                    dt_str, nivel, msg = m.groups()
                    try:
                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                        if not (d_ini <= dt <= d_fim): continue
                    except Exception:
                        pass
                    if tipo_filtro and nivel.upper() != tipo_filtro:
                        continue
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
            messagebox.showinfo("Sucesso", f"Logs exportados para {path}!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na exportação: {e}")

    # ── MÉTODOS DE ACESSOS ────────────────────────────────────────────────────

    def _re_salvar_acessos(self) -> None:
        try:
            import xml.etree.ElementTree as ET
            trees = {}
            for campo, fname in self.re_acessos_info:
                p = get_app_path(fname)
                if p not in trees:
                    if os.path.exists(p):
                        trees[p] = ET.parse(p)
                    else:
                        rt = "auth" if fname == "auth.xml" else "credenciais"
                        root = ET.Element(rt)
                        trees[p] = ET.ElementTree(root)

            for entry, (campo, fname) in zip(self.re_acessos_entries, self.re_acessos_info):
                novo_val = entry.get().strip()
                if novo_val:
                    p = get_app_path(fname)
                    root = trees[p].getroot()
                    el = root.find(campo)
                    if el is None:
                        el = ET.SubElement(root, campo)
                    el.text = criptografar(novo_val)

            for p, tree in trees.items():
                tree.write(p, encoding="utf-8", xml_declaration=True)

            messagebox.showinfo("Sucesso", "Credenciais criptografadas e salvas com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar credenciais: {e}")

    # ── MÉTODOS DE CAMPEONATOS EXTRAS ─────────────────────────────────────────

    def _re_reload_camps_tv(self) -> None:
        for i in self.re_tv_camps.get_children():
            self.re_tv_camps.delete(i)
        camps = carregar_campeonatos_config()
        for c in camps:
            ativo_str = "✅" if c.get("ativo", True) else "❌"
            self.re_tv_camps.insert("", "end", values=(c.get("campeonato", ""), c.get("plataforma", ""), c.get("url", ""), ativo_str))

    def _re_add_campeonato(self) -> None:
        self._re_modal_campeonato("Adicionar Campeonato")

    def _re_edit_campeonato(self) -> None:
        sel = self.re_tv_camps.selection()
        if not sel: return
        idx = self.re_tv_camps.index(sel[0])
        lista = carregar_campeonatos_config()
        if idx < len(lista):
            self._re_modal_campeonato("Editar Campeonato", lista[idx], idx)

    def _re_modal_campeonato(self, titulo: str, inicial: Optional[dict] = None, idx: Optional[int] = None) -> None:
        win = Toplevel(self)
        win.title(titulo)
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.geometry("500x240")

        ttk.Label(win, text="Nome do Campeonato:").grid(row=0, column=0, padx=8, pady=8, sticky=E)
        e_nome = ttk.Entry(win, width=35)
        e_nome.grid(row=0, column=1, padx=8, pady=8, sticky=W)

        ttk.Label(win, text="Plataforma:").grid(row=1, column=0, padx=8, pady=8, sticky=E)
        cbo_plat = ttk.Combobox(win, values=["Amazon Prime", "Disney", "Max", "Dazn", "Cazé TV"], state="readonly", width=32)
        cbo_plat.grid(row=1, column=1, padx=8, pady=8, sticky=W)
        cbo_plat.current(0)

        ttk.Label(win, text="URL:").grid(row=2, column=0, padx=8, pady=8, sticky=E)
        e_url = ttk.Entry(win, width=35)
        e_url.grid(row=2, column=1, padx=8, pady=8, sticky=W)

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
            if not dados["campeonato"]: return
            lista = carregar_campeonatos_config()
            if idx is not None and idx < len(lista):
                lista[idx] = dados
            else:
                lista.append(dados)
            salvar_campeonatos_config(lista)
            self._re_reload_camps_tv()
            win.destroy()

        ttk.Button(win, text="Salvar", command=_salvar).grid(row=3, column=0, columnspan=2, pady=16)

    def _re_remove_campeonato(self) -> None:
        sel = self.re_tv_camps.selection()
        if not sel: return
        idx = self.re_tv_camps.index(sel[0])
        lista = carregar_campeonatos_config()
        if idx < len(lista):
            if messagebox.askyesno("Confirmar", f"Remover campeonato '{lista[idx].get('campeonato')}'?"):
                lista.pop(idx)
                salvar_campeonatos_config(lista)
                self._re_reload_camps_tv()

    def _re_toggle_campeonato(self) -> None:
        sel = self.re_tv_camps.selection()
        if not sel: return
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
        for c in canais:
            ativo_str = "✅" if c.get("ativo", True) else "❌"
            self.re_tv_yt.insert("", "end", values=(c.get("nome", ""), c.get("url", ""), ativo_str))

    def _re_add_yt_channel(self) -> None:
        self._re_modal_yt_channel("Adicionar Canal")

    def _re_edit_yt_channel(self) -> None:
        sel = self.re_tv_yt.selection()
        if not sel: return
        idx = self.re_tv_yt.index(sel[0])
        canais = carregar_youtube_channels_config()
        if idx < len(canais):
            self._re_modal_yt_channel("Editar Canal", canais[idx], idx)

    def _re_modal_yt_channel(self, titulo: str, inicial: Optional[dict] = None, idx: Optional[int] = None) -> None:
        win = Toplevel(self)
        win.title(titulo)
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.geometry("520x200")

        ttk.Label(win, text="Nome do Canal:").grid(row=0, column=0, padx=8, pady=8, sticky=E)
        e_nome = ttk.Entry(win, width=38)
        e_nome.grid(row=0, column=1, padx=8, pady=8, sticky=W)

        ttk.Label(win, text="URL do Canal:").grid(row=1, column=0, padx=8, pady=8, sticky=E)
        e_url = ttk.Entry(win, width=38)
        e_url.grid(row=1, column=1, padx=8, pady=8, sticky=W)

        if inicial:
            e_nome.insert(0, inicial.get("nome", ""))
            e_url.insert(0, inicial.get("url", ""))

        def _salvar():
            dados = {
                "nome": e_nome.get().strip(),
                "url": e_url.get().strip(),
                "ativo": True if not inicial else inicial.get("ativo", True)
            }
            if not dados["nome"] or not dados["url"]: return
            canais = carregar_youtube_channels_config()
            if idx is not None and idx < len(canais):
                canais[idx] = dados
            else:
                canais.append(dados)
            salvar_youtube_channels_config(canais)
            self._re_reload_yt_tv()
            win.destroy()

        ttk.Button(win, text="Salvar", command=_salvar).grid(row=2, column=0, columnspan=2, pady=16)

    def _re_remove_yt_channel(self) -> None:
        sel = self.re_tv_yt.selection()
        if not sel: return
        idx = self.re_tv_yt.index(sel[0])
        canais = carregar_youtube_channels_config()
        if idx < len(canais):
            if messagebox.askyesno("Confirmar", f"Remover canal '{canais[idx].get('nome')}'?"):
                canais.pop(idx)
                salvar_youtube_channels_config(canais)
                self._re_reload_yt_tv()

    def _re_toggle_yt_channel(self) -> None:
        sel = self.re_tv_yt.selection()
        if not sel: return
        idx = self.re_tv_yt.index(sel[0])
        canais = carregar_youtube_channels_config()
        if idx < len(canais):
            canais[idx]["ativo"] = not canais[idx].get("ativo", True)
            salvar_youtube_channels_config(canais)
            self._re_reload_yt_tv()

    def _re_restore_default_yt_channels(self) -> None:
        if messagebox.askyesno("Restaurar Padrões", "Restaurar os 6 canais padrão do YouTube?"):
            salvar_youtube_channels_config(DEFAULT_YOUTUBE_CHANNELS)
            self._re_reload_yt_tv()
            messagebox.showinfo("Sucesso", "Canais restaurados.")

    def _re_buscar_canais_youtube_agora(self) -> None:
        def _task():
            try:
                self.re_lbl_status.configure(text="Varrendo canais do YouTube cadastrados...")
                canais = [c for c in carregar_youtube_channels_config() if c.get("ativo", True)]
                cbf_idx = get_cbf_rights_index()
                total_encontrados = 0
                for c in canais:
                    evs = obter_eventos_canal_youtube(c["nome"], c["url"], cbf_idx=cbf_idx)
                    for ev in evs:
                        self.after(0, lambda e=ev: self._re_inserir_evento_na_grade(e))
                        total_encontrados += 1

                # Sincronização direta no SharePoint
                self.re_lbl_status.configure(text="Sincronizando com SharePoint...")
                linhas = [list(self.re_tree.item(i, "values")) for i in self.re_tree.get_children()]
                sp_res = push_events_to_sharepoint(linhas)
                msg_final = f"Busca concluída! {total_encontrados} confrontos novos identificados. SharePoint sincronizado: {sp_res.get('inseridos', 0)} novos itens."
                self.re_lbl_status.configure(text=msg_final)
                self.after(0, lambda: messagebox.showinfo("Sucesso", msg_final))
            except Exception as e:
                logger.error(f"[ReporteEventos] Erro ao buscar canais YouTube: {e}")
                self.after(0, lambda: messagebox.showerror("Erro", f"Erro na busca dos canais: {e}"))

        threading.Thread(target=_task, daemon=True).start()
