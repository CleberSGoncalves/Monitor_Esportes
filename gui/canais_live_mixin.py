# gui/canais_live_mixin.py
"""
Mixin com a interface completa e fluxos de controle da aba '📡 Canais Live'.
Permite cadastrar canais do YouTube, listar eventos futuros (upcoming) e ao vivo,
selecionar para a fila de análise, aguardar encerramento, transcrever o áudio
integral e transformar em cronologia com auxílio do Gemini Web e ReportGenerator.
"""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

import customtkinter as ctk
from tkinter import messagebox, filedialog

from modules.live_channel_monitor import LiveNarrationService, PIPELINE_LABELS, normalize_channel_url


class CanaisLiveMixin:
    """Mixin integrado ao MonitorApp para gerenciar a aba 📡 Canais Live."""

    def _init_canais_live(self) -> None:
        """Inicializa variáveis e o serviço de monitoramento em segundo plano."""
        self._canais_search_var = ctk.StringVar(value="")
        self._auto_detect_match_var = ctk.BooleanVar(value=True)
        self._auto_report_live_var = ctk.BooleanVar(value=True)
        self._auto_email_live_var = ctk.BooleanVar(value=True)
        self._incoming_cb_vars: Dict[str, ctk.BooleanVar] = {}
        self._user_toggling: bool = False
        self._refresh_timer = None
        self._fila_filter_mode: str = "all"  # "all", "active", "done"
        self._fila_limit: int = 15
        self._incoming_limit: int = 25
        self._live_cards_cache: Dict[str, Any] = {}
        self._live_incoming_cache: Dict[str, Any] = {}

        self.live_service = LiveNarrationService(
            reporter=self.reporter,
            config_provider=self._get_live_service_config,
            log=self._log,
            on_change=lambda: self.after(0, self._on_service_state_changed)
        )
        auto_det = self.live_service.get_setting("auto_detect_match", True)
        auto_rep = self.live_service.get_setting("auto_report", True)
        self._auto_detect_match_var.set(auto_det)
        self._auto_report_live_var.set(auto_rep)
        self._auto_email_live_var.set(self.live_service.get_setting("auto_email", True))
        self.live_service.start()

    def _on_service_state_changed(self) -> None:
        """Callback acionado pelo serviço de monitoramento em background com debounce suave."""
        if getattr(self, "_user_toggling", False):
            return
        if hasattr(self, "_refresh_timer") and self._refresh_timer is not None:
            try:
                self.after_cancel(self._refresh_timer)
            except Exception:
                pass
        self._refresh_timer = self.after(350, self._debounced_refresh_ui)

    def _debounced_refresh_ui(self) -> None:
        self._refresh_timer = None
        self._refresh_canais_tab_ui()

    def _get_live_service_config(self) -> Dict[str, Any]:
        """Lê credenciais e configurações para transcrição, cronologia e e-mail."""
        cfg: Dict[str, Any] = {
            "api_key": "",
            "model_id": "gemini-2.5-flash",
            "emails": [],
            "sender": "",
            "password": "",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
        }
        try:
            from gui.main_gui import _get_config_read_path, _load_saved_emails, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT
            cfg_path = _get_config_read_path("google_ai.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cfg["api_key"] = data.get("gemini_api_keys") or data.get("gemini_api_key") or data.get("api_key") or ""
                cfg["model_id"] = data.get("model") or "gemini-2.5-flash"
                cfg["sender"] = data.get("email") or ""
                cfg["password"] = data.get("senha") or ""
            cfg["emails"] = self._get_configured_emails()
            cfg["smtp_server"] = EMAIL_SMTP_SERVER
            cfg["smtp_port"] = EMAIL_SMTP_PORT
        except Exception as ex:
            self._log(f"⚠️ [CANAIS LIVE] Erro ao ler configurações: {ex}")
        return cfg

    def _get_configured_emails(self) -> List[str]:
        """Retorna a lista atual de e-mails configurados para recebimento."""
        from gui.main_gui import _load_saved_emails
        emails = self.live_service.get_setting("emails")
        if emails and isinstance(emails, list):
            res = [str(e).strip() for e in emails if str(e).strip()]
            if res:
                return res
        return _load_saved_emails() or []

    def _save_configured_emails(self, emails: List[str]) -> None:
        """Salva a lista de e-mails no serviço e sincroniza com saved_emails.json."""
        from gui.main_gui import _save_config_file
        cleaned = []
        for e in emails:
            s = str(e).strip()
            if s and s not in cleaned:
                cleaned.append(s)
        self.live_service.set_setting("emails", cleaned)
        try:
            _save_config_file("saved_emails.json", cleaned)
        except Exception:
            pass
        self._update_emails_button_text()
        self._log(f"👥 Destinatários de e-mail atualizados ({len(cleaned)}): {', '.join(cleaned)}")

    def _update_emails_button_text(self) -> None:
        """Atualiza o texto dos botões de destinatários com a contagem atual."""
        try:
            emails = self._get_configured_emails()
            n = len(emails)
            if hasattr(self, "btn_manage_emails"):
                self.btn_manage_emails.configure(text=f"👥 Destinatários ({n})")
            if hasattr(self, "btn_queue_emails"):
                self.btn_queue_emails.configure(text=f"👥 Destinatários ({n})")
        except Exception:
            pass

    # =========================================================================
    # CONSTRUÇÃO DA ABA
    # =========================================================================
    def _build_tab_canais_live(self) -> None:
        """Monta a interface gráfica da aba '📡 Canais Live'."""
        container = ctk.CTkFrame(self.tab_canais, fg_color="#0d0d0d")
        container.pack(fill="both", expand=True, padx=8, pady=8)

        # ---------------------------------------------------------------------
        # 1. BARRA SUPERIOR: KPIS & CONTROLES GERAIS
        # ---------------------------------------------------------------------
        kpi_bar = ctk.CTkFrame(container, fg_color="#141414", corner_radius=10, border_width=1, border_color="#262626")
        kpi_bar.pack(fill="x", padx=4, pady=(2, 8))

        # LINHA 1 DA BARRA SUPERIOR: KPIs + Atualizar + Auditoria Geral + SharePoint
        kpi_row1 = ctk.CTkFrame(kpi_bar, fg_color="transparent")
        kpi_row1.pack(fill="x", padx=6, pady=(6, 3))

        # KPI 1: Canais Cadastrados
        kpi1 = ctk.CTkFrame(kpi_row1, fg_color="#1b1b1b", corner_radius=8, width=155, height=52)
        kpi1.pack(side="left", padx=4, pady=2)
        kpi1.pack_propagate(False)
        ctk.CTkLabel(kpi1, text="📡 CANAIS MONITORADOS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=8, pady=(5, 0))
        self.lbl_kpi_canais_count = ctk.CTkLabel(kpi1, text="0", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00CED1")
        self.lbl_kpi_canais_count.pack(anchor="w", padx=8, pady=(0, 4))

        # KPI 2: Eventos Futuros / Ao Vivo
        kpi2 = ctk.CTkFrame(kpi_row1, fg_color="#1b1b1b", corner_radius=8, width=165, height=52)
        kpi2.pack(side="left", padx=4, pady=2)
        kpi2.pack_propagate(False)
        ctk.CTkLabel(kpi2, text="📅 EVENTOS ENCONTRADOS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=8, pady=(5, 0))
        self.lbl_kpi_eventos_count = ctk.CTkLabel(kpi2, text="0", font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFD700")
        self.lbl_kpi_eventos_count.pack(anchor="w", padx=8, pady=(0, 4))

        # KPI 3: Fila de Análise
        kpi3 = ctk.CTkFrame(kpi_row1, fg_color="#1b1b1b", corner_radius=8, width=155, height=52)
        kpi3.pack(side="left", padx=4, pady=2)
        kpi3.pack_propagate(False)
        ctk.CTkLabel(kpi3, text="🎯 FILA DE ANÁLISE", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=8, pady=(5, 0))
        self.lbl_kpi_fila_count = ctk.CTkLabel(kpi3, text="0", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00FF7F")
        self.lbl_kpi_fila_count.pack(anchor="w", padx=8, pady=(0, 4))

        # Botão: Atualizar Todos os Canais Agora
        self.btn_scan_all_canais = ctk.CTkButton(
            kpi_row1,
            text="🔄 Atualizar Canais Agora",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#008080",
            hover_color="#005a5a",
            height=34,
            width=175,
            command=self._on_scan_all_clicked
        )
        self.btn_scan_all_canais.pack(side="left", padx=6, pady=2)

        # Botão: Relatório Geral de Casos / Auditoria de Lives
        self.btn_audit_report = ctk.CTkButton(
            kpi_row1,
            text="📋 Relatório Geral de Auditoria",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#4a148c",
            hover_color="#6a1b9a",
            height=34,
            width=195,
            command=self._on_audit_report_clicked
        )
        self.btn_audit_report.pack(side="left", padx=5, pady=2)

        # Botão: Abrir Pasta de Relatórios
        self.btn_open_reports_folder = ctk.CTkButton(
            kpi_row1,
            text="📂 Pasta de Relatórios",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#263238",
            hover_color="#37474f",
            height=34,
            width=155,
            command=self._on_open_reports_folder_clicked
        )
        self.btn_open_reports_folder.pack(side="left", padx=5, pady=2)

        # Botão: Ver Relatórios Gerados
        self.btn_view_recent_reports = ctk.CTkButton(
            kpi_row1,
            text="📑 Ver Relatórios (PDF)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1b5e20",
            hover_color="#2e7d32",
            height=34,
            width=155,
            command=self._open_recent_reports_modal
        )
        self.btn_view_recent_reports.pack(side="left", padx=5, pady=2)

        # Status SharePoint
        self.lbl_live_status_hint = ctk.CTkLabel(
            kpi_row1,
            text="☁️ SharePoint Conectado",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#00FF7F"
        )
        self.lbl_live_status_hint.pack(side="right", padx=12, pady=2)

        # LINHA 2 DA BARRA SUPERIOR: Switches e Destinatários de E-mail (NUNCA CORTA!)
        kpi_row2 = ctk.CTkFrame(kpi_bar, fg_color="transparent")
        kpi_row2.pack(fill="x", padx=6, pady=(2, 6))

        # Switch 1: Auto-Detect Jogo (Avalia automaticamente todas as lives dos canais)
        self.switch_auto_detect_match = ctk.CTkSwitch(
            kpi_row2,
            text="🤖 Auto-Detect Jogo (Avalia todas as lives)",
            font=ctk.CTkFont(size=11, weight="bold"),
            variable=self._auto_detect_match_var,
            progress_color="#00CED1",
            command=self._on_auto_detect_toggle
        )
        self.switch_auto_detect_match.pack(side="left", padx=(8, 16), pady=2)

        # Switch 2: Auto-Relatório + E-mail (Faz tudo ao encerrar)
        self.switch_auto_report = ctk.CTkSwitch(
            kpi_row2,
            text="⚡ Auto-Relatório + E-mail (Faz tudo ao encerrar)",
            font=ctk.CTkFont(size=11, weight="bold"),
            variable=self._auto_report_live_var,
            progress_color="#00FF7F",
            command=self._on_auto_report_toggle
        )
        self.switch_auto_report.pack(side="left", padx=16, pady=2)

        # Botão: Gerenciar Destinatários de E-mail
        self.btn_manage_emails = ctk.CTkButton(
            kpi_row2,
            text="👥 Destinatários (0)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1f538d",
            hover_color="#14375e",
            height=30,
            width=160,
            command=self._open_email_recipients_modal
        )
        self.btn_manage_emails.pack(side="left", padx=16, pady=2)
        self._update_emails_button_text()

        # ---------------------------------------------------------------------
        # 2. CORPO PRINCIPAL (2 COLUNAS VIA GRID EQUILIBRADO)
        # ---------------------------------------------------------------------
        body = ctk.CTkFrame(container, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=2, pady=2)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        # ---------------------- COLUNA ESQUERDA (CANAIS & EVENTOS) ----------------------
        col_left = ctk.CTkFrame(body, fg_color="#121212", corner_radius=10, border_width=1, border_color="#222222")
        col_left.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=2)

        # SEÇÃO A: CADASTRO DE CANAIS
        sec_ch_hdr = ctk.CTkFrame(col_left, fg_color="transparent")
        sec_ch_hdr.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(sec_ch_hdr, text="📺 CANAIS DO YOUTUBE CADASTRADOS", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00CED1").pack(side="left")

        # Linha de entrada de canal
        add_ch_row = ctk.CTkFrame(col_left, fg_color="transparent")
        add_ch_row.pack(fill="x", padx=10, pady=(2, 6))

        self.entry_add_channel = ctk.CTkEntry(
            add_ch_row,
            placeholder_text="URL ou @ do Canal (ex: @CazeTV ou link do canal)",
            font=ctk.CTkFont(size=11),
            height=30
        )
        self.entry_add_channel.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry_add_channel.bind("<Return>", lambda e: self._on_add_channel_clicked())

        self.btn_add_channel = ctk.CTkButton(
            add_ch_row,
            text="➕ Cadastrar",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1f77b4",
            hover_color="#155584",
            width=100,
            height=30,
            command=self._on_add_channel_clicked
        )
        self.btn_add_channel.pack(side="left")

        # Lista de Canais Cadastrados (Scrollable)
        self.scroll_canais = ctk.CTkScrollableFrame(col_left, fg_color="#0a0a0a", corner_radius=8, height=120)
        self.scroll_canais.pack(fill="x", padx=10, pady=(0, 8))

        # SEÇÃO B: EVENTOS FUTUROS (UPCOMING) & AO VIVO
        sec_ev_hdr = ctk.CTkFrame(col_left, fg_color="transparent")
        sec_ev_hdr.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(
            sec_ev_hdr,
            text="📅 PRÓXIMOS EVENTOS & AO VIVO (ESCOLHA PARA ANALISAR)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FFD700"
        ).pack(side="left")

        # Linha para inclusão de live avulsa por URL direta
        add_vid_row = ctk.CTkFrame(col_left, fg_color="transparent")
        add_vid_row.pack(fill="x", padx=10, pady=(2, 6))

        self.entry_add_video = ctk.CTkEntry(
            add_vid_row,
            placeholder_text="Ou adicione uma Live específica por URL direta...",
            font=ctk.CTkFont(size=11),
            height=28
        )
        self.entry_add_video.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry_add_video.bind("<Return>", lambda e: self._on_add_video_clicked())

        self.btn_add_video = ctk.CTkButton(
            add_vid_row,
            text="➕ Incluir",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#37474f",
            hover_color="#455a64",
            width=80,
            height=28,
            command=self._on_add_video_clicked
        )
        self.btn_add_video.pack(side="left")

        # Lista de Eventos Encontrados
        self.scroll_incoming = ctk.CTkScrollableFrame(col_left, fg_color="#0a0a0a", corner_radius=8)
        self.scroll_incoming.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ---------------------- COLUNA DIREITA (FILA DE ANÁLISE) ----------------------
        col_right = ctk.CTkFrame(body, fg_color="#121212", corner_radius=10, border_width=1, border_color="#222222")
        col_right.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=2)

        sec_queue_hdr = ctk.CTkFrame(col_right, fg_color="transparent")
        sec_queue_hdr.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            sec_queue_hdr,
            text="🎙️ FILA DE ANÁLISE E CRONOLOGIA",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00FF7F",
            anchor="w"
        ).pack(side="left")

        # Botão rápido de gerenciar destinatários no topo da fila
        self.btn_queue_emails = ctk.CTkButton(
            sec_queue_hdr,
            text="👥 Destinatários",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1f538d",
            hover_color="#14375e",
            height=26,
            width=135,
            command=self._open_email_recipients_modal
        )
        self.btn_queue_emails.pack(side="right")

        self.lbl_queue_sub = ctk.CTkLabel(
            col_right,
            text="Fluxo: Upcoming ➔ Ao Vivo ➔ Término ➔ Transcrição Áudio (.txt) ➔ Cronologia Técnica (PDF) ➔ Envio por E-mail",
            font=ctk.CTkFont(size=10),
            text_color="#777777",
            anchor="w"
        )
        self.lbl_queue_sub.pack(fill="x", padx=12, pady=(0, 6))

        # Scroll de Cards da Fila
        self.scroll_fila = ctk.CTkScrollableFrame(col_right, fg_color="#0a0a0a", corner_radius=8)
        self.scroll_fila.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Renderização inicial
        self._refresh_canais_tab_ui()

    # =========================================================================
    # REFRESH E ATUALIZAÇÃO DOS CARDS
    # =========================================================================
    def _refresh_canais_tab_ui(self) -> None:
        """Atualiza KPIs, canais, lista incoming e cards da fila de análise."""
        if not hasattr(self, "scroll_canais") or not hasattr(self, "scroll_fila"):
            return

        self._refresh_kpis()
        self._render_canais_list()
        self._render_incoming_list()
        self._render_fila_cards()

    def _refresh_kpis(self) -> None:
        """Atualiza os contadores numéricos superiores."""
        channels = self.live_service.list_channels()
        events = self.live_service.list_events()
        selected_events = [e for e in events if e.get("selected")]
        done_events = [e for e in selected_events if e.get("pipeline") in ("transcribed", "done")]

        if hasattr(self, "lbl_kpi_canais_count"):
            self.lbl_kpi_canais_count.configure(text=str(len(channels)))
        if hasattr(self, "lbl_kpi_eventos_count"):
            self.lbl_kpi_eventos_count.configure(text=str(len(events)))
        if hasattr(self, "lbl_kpi_fila_count"):
            self.lbl_kpi_fila_count.configure(text=str(len(selected_events)))
        if hasattr(self, "lbl_kpi_prontos_count"):
            self.lbl_kpi_prontos_count.configure(text=str(len(done_events)))
        self._update_emails_button_text()

    def _render_canais_list(self) -> None:
        """Renderiza a lista de canais cadastrados."""
        channels = self.live_service.list_channels()
        for w in self.scroll_canais.winfo_children():
            w.destroy()

        if not channels:
            ctk.CTkLabel(
                self.scroll_canais,
                text="Nenhum canal cadastrado ainda. Digite a URL ou @ acima e clique em 'Cadastrar'.",
                font=ctk.CTkFont(size=11),
                text_color="#666666"
            ).pack(pady=15)
            return

        for ch in channels:
            row = ctk.CTkFrame(self.scroll_canais, fg_color="#181818", corner_radius=6, height=36)
            row.pack(fill="x", pady=2, padx=2)
            row.pack_propagate(False)

            ctk.CTkLabel(row, text="📺", font=ctk.CTkFont(size=12)).pack(side="left", padx=(8, 4))
            ctk.CTkLabel(
                row,
                text=ch.get("name", "Canal"),
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#ffffff"
            ).pack(side="left", padx=4)

            ctk.CTkLabel(
                row,
                text=f"({ch.get('url', '')})",
                font=ctk.CTkFont(size=9),
                text_color="#777777"
            ).pack(side="left", padx=4)

            def make_del(cid=ch["id"], cname=ch.get("name")):
                return lambda: self._on_remove_channel(cid, cname)

            ctk.CTkButton(
                row,
                text="🗑️",
                width=28,
                height=24,
                fg_color="transparent",
                hover_color="#550000",
                font=ctk.CTkFont(size=11),
                command=make_del()
            ).pack(side="right", padx=6)

    def _render_incoming_list(self) -> None:
        """Renderiza a lista de eventos encontrados à esquerda com checkboxes reativos."""
        events = self.live_service.list_events()

        def incoming_sort_key(ev):
            st = ev.get("status")
            prio = 0 if st == "live" else (1 if st == "upcoming" else 2)
            epoch = ev.get("scheduled_epoch") or ev.get("actual_start_epoch") or 9999999999
            return (prio, epoch)

        sorted_events = sorted(events, key=incoming_sort_key)

        for w in self.scroll_incoming.winfo_children():
            w.destroy()

        self._incoming_cb_vars.clear()

        if not sorted_events:
            ctk.CTkLabel(
                self.scroll_incoming,
                text="Nenhum evento encontrado nos canais cadastrados.\nClique em 'Atualizar Canais Agora' para escanear transmissões futuras.",
                font=ctk.CTkFont(size=11),
                text_color="#666666"
            ).pack(pady=20)
            return

        # Limitar renderização para manter a UI ultra-leve
        limit = getattr(self, "_incoming_limit", 25)
        visible_events = sorted_events[:limit]

        for ev in visible_events:
            vid = ev["video_id"]
            card = ctk.CTkFrame(self.scroll_incoming, fg_color="#161616", corner_radius=8)
            card.pack(fill="x", pady=3, padx=2)

            top_line = ctk.CTkFrame(card, fg_color="transparent")
            top_line.pack(fill="x", padx=8, pady=(6, 2))

            # Checkbox de Seleção
            is_sel = bool(ev.get("selected"))
            cb_var = ctk.BooleanVar(value=is_sel)
            self._incoming_cb_vars[vid] = cb_var

            def make_toggle(v_id=vid, v_var=cb_var):
                return lambda: self._on_toggle_event(v_id, v_var.get())

            cb = ctk.CTkCheckBox(
                top_line,
                text="",
                variable=cb_var,
                width=20,
                checkbox_width=18,
                checkbox_height=18,
                command=make_toggle(),
                checkmark_color="#000000",
                fg_color="#00CED1"
            )
            cb.pack(side="left", padx=(0, 6))

            # Badge Status
            st = ev.get("status")
            if st == "live":
                badge_txt, badge_color = "🔴 AO VIVO", "#FF4C4C"
            elif st == "upcoming":
                sched = ev.get("scheduled_epoch")
                try:
                    t_str = datetime.fromtimestamp(float(sched)).strftime("%d/%m %H:%M") if sched else "Futuro"
                except Exception:
                    t_str = "Futuro"
                badge_txt, badge_color = f"⏳ {t_str}", "#FFD700"
            else:
                badge_txt, badge_color = "🏁 Encerrado", "#888888"

            ctk.CTkLabel(
                top_line,
                text=badge_txt,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=badge_color
            ).pack(side="left", padx=4)

            ctk.CTkLabel(
                top_line,
                text=f"• {ev.get('channel_name', 'YouTube')}",
                font=ctk.CTkFont(size=10),
                text_color="#aaaaaa"
            ).pack(side="left", padx=4)

            # Título do Vídeo
            title_txt = ev.get("title", vid)
            lbl_title = ctk.CTkLabel(
                card,
                text=title_txt,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#ffffff",
                anchor="w",
                justify="left",
                wraplength=420
            )
            lbl_title.pack(fill="x", padx=32, pady=(0, 6))


        if len(sorted_events) > limit:
            f_frame = ctk.CTkFrame(self.scroll_incoming, fg_color="transparent")
            f_frame.pack(fill="x", pady=8)
            ctk.CTkLabel(
                f_frame,
                text=f"Exibindo {len(visible_events)} de {len(sorted_events)} eventos encontrados",
                font=ctk.CTkFont(size=10),
                text_color="#888888"
            ).pack(side="left", padx=8)
            ctk.CTkButton(
                f_frame,
                text=f"🔽 Carregar Mais (+25)",
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color="#263238",
                hover_color="#37474f",
                height=24,
                width=130,
                command=self._on_load_more_incoming
            ).pack(side="right", padx=8)

    def _render_fila_cards(self) -> None:
        """Renderiza os cards da fila de análise de forma ultra-leve e paginada."""
        if not hasattr(self, "scroll_fila"):
            return

        for w in self.scroll_fila.winfo_children():
            w.destroy()

        events = self.live_service.list_events()
        selected_events = [e for e in events if e.get("selected")]

        if not selected_events:
            ctk.CTkLabel(
                self.scroll_fila,
                text="Nenhum evento selecionado para análise.\nMarque as caixas de seleção [✓] na coluna à esquerda para adicionar eventos à fila.",
                font=ctk.CTkFont(size=11),
                text_color="#666666"
            ).pack(pady=40)
            return

        # Atualiza cor dos botões de filtro
        mode = getattr(self, "_fila_filter_mode", "all")
        if hasattr(self, "btn_filter_all"):
            self.btn_filter_all.configure(fg_color="#2b5b84" if mode == "all" else "#1c1c1c")
        if hasattr(self, "btn_filter_active"):
            self.btn_filter_active.configure(fg_color="#8d6e63" if mode == "active" else "#1c1c1c")
        if hasattr(self, "btn_filter_done"):
            self.btn_filter_done.configure(fg_color="#2e7d32" if mode == "done" else "#1c1c1c")

        # Filtragem rápida
        if mode == "active":
            filtered = [e for e in selected_events if e.get("pipeline") in ("live", "transcribing", "analyzing", "generating", "waiting") or e.get("status") in ("live", "upcoming")]
        elif mode == "done":
            filtered = [e for e in selected_events if e.get("pdf_path") or e.get("pipeline") in ("done", "ready_match", "not_match")]
        else:
            filtered = selected_events

        if not filtered:
            ctk.CTkLabel(
                self.scroll_fila,
                text=f"Nenhum evento corresponde ao filtro '{mode.upper()}'.\nClique em 'Todas' para ver os {len(selected_events)} eventos na fila.",
                font=ctk.CTkFont(size=11),
                text_color="#888888"
            ).pack(pady=30)
            return

        # Ordenação inteligente: Ao Vivo > Em Processamento > Prontas > Aguardando
        def fila_prio(e):
            p = e.get("pipeline")
            st = e.get("status")
            if p == "live" or st == "live":
                return 0
            if p in ("generating", "analyzing", "transcribing"):
                return 1
            if p == "ready_match":
                return 2
            if e.get("pdf_path"):
                return 3
            if p == "waiting" or st == "upcoming":
                return 4
            return 5

        sorted_fila = sorted(filtered, key=fila_prio)

        # Paginação inteligente para garantir 60 FPS
        limit = getattr(self, "_fila_limit", 15)
        visible_fila = sorted_fila[:limit]

        for ev in visible_fila:
            vid = ev.get("video_id", "")
            try:
                self._render_single_fila_card(ev)
            except Exception as ex:
                self._log(f"⚠️ Erro ao renderizar card da fila ({vid}): {ex}")

        # Rodapé de Paginação quando houver muitos cards
        if len(sorted_fila) > limit:
            footer = ctk.CTkFrame(self.scroll_fila, fg_color="#141414", corner_radius=8)
            footer.pack(fill="x", pady=10, padx=6)

            ctk.CTkLabel(
                footer,
                text=f"Exibindo {len(visible_fila)} de {len(sorted_fila)} eventos na fila",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#00CED1"
            ).pack(side="left", padx=12, pady=8)

            ctk.CTkButton(
                footer,
                text="Mostrar Todos",
                font=ctk.CTkFont(size=10),
                fg_color="#37474f",
                hover_color="#455a64",
                height=26,
                width=100,
                command=self._on_show_all_fila
            ).pack(side="right", padx=(4, 12), pady=8)

            ctk.CTkButton(
                footer,
                text="🔽 Carregar Mais (+15)",
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color="#008080",
                hover_color="#005a5a",
                height=26,
                width=140,
                command=self._on_load_more_fila
            ).pack(side="right", padx=4, pady=8)

    def _render_single_fila_card(self, ev: Dict[str, Any]) -> None:
        """Renderiza um card individual na fila de análise da coluna direita."""
        vid = ev["video_id"]
        pipe = ev.get("pipeline", "waiting")
        badge_info = PIPELINE_LABELS.get(pipe, ("⏳ Na Fila", "#FFD700"))

        card = ctk.CTkFrame(self.scroll_fila, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2a2a2a")
        card.pack(fill="x", pady=6, padx=4)

        # Cabeçalho do Card
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            hdr,
            text=badge_info[0],
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=badge_info[1]
        ).pack(side="left")

        ctk.CTkLabel(
            hdr,
            text=f"• {ev.get('channel_name') or 'YouTube'}",
            font=ctk.CTkFont(size=11),
            text_color="#999999"
        ).pack(side="left", padx=6)

        # Botão Superior de Remover da Fila (DESTACADO E CLARO)
        def make_remove_sel(v_id=vid):
            return lambda: self._on_remove_from_queue(v_id)

        ctk.CTkButton(
            hdr,
            text="✕ Remover da Fila",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#3a1414",
            hover_color="#5f1d1d",
            text_color="#ff8888",
            height=24,
            width=125,
            command=make_remove_sel()
        ).pack(side="right")

        # Título
        ctk.CTkLabel(
            card,
            text=ev.get("title") or vid,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffffff",
            anchor="w",
            justify="left",
            wraplength=560
        ).pack(fill="x", padx=10, pady=(2, 4))

        # Diagnóstico da Análise da Transcrição (Partida + Marcas/Anúncios)
        t_analysis = ev.get("transcript_analysis") or {}
        is_match = ev.get("is_match_narration")
        meta = ev.get("meta") or {}
        if is_match is True and (meta.get("team1") or meta.get("team2")):
            score_str = f" ({t_analysis.get('detected_score')})" if t_analysis.get("detected_score") else ""
            match_txt = f"⚽ Partida Identificada: {meta.get('team1', '')} x {meta.get('team2', '')}{score_str} • {meta.get('competition', '')}"
            ctk.CTkLabel(
                card,
                text=match_txt,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#00FF7F",
                anchor="w",
                justify="left",
                wraplength=560
            ).pack(fill="x", padx=10, pady=(0, 2))
        elif is_match is False:
            cat_txt = t_analysis.get("event_category") or "Programa / Debate"
            reason_txt = t_analysis.get("classification_summary") or "Não foi identificada narração de partida em tempo real."
            ctk.CTkLabel(
                card,
                text=f"ℹ️ {cat_txt}: {reason_txt}",
                font=ctk.CTkFont(size=10),
                text_color="#90A4AE",
                anchor="w",
                justify="left",
                wraplength=560
            ).pack(fill="x", padx=10, pady=(0, 2))

        brand_mentions = ev.get("brand_mentions") or t_analysis.get("brand_mentions") or []
        brands_summary = str(ev.get("brands_summary") or t_analysis.get("brands_summary") or "").strip()
        if brand_mentions or brands_summary:
            b_names = []
            for bm in brand_mentions:
                if isinstance(bm, dict) and bm.get("brand"):
                    bn = str(bm["brand"]).strip()
                    if bn and bn not in b_names:
                        b_names.append(bn)
            b_display = f"📢 Marcas/Anúncios na Narração ({len(brand_mentions)}): {', '.join(b_names[:8])}" if b_names else f"📢 Marcas/Anúncios: {brands_summary[:110]}"
            ctk.CTkLabel(
                card,
                text=b_display,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#FFB74D",
                anchor="w",
                justify="left",
                wraplength=560
            ).pack(fill="x", padx=10, pady=(0, 3))

        # Mensagem de Progresso / Erro
        prog = str(ev.get("progress") or "").strip()
        err = str(ev.get("error") or "").strip()
        if err:
            ctk.CTkLabel(
                card,
                text=f"⚠️ {err}",
                font=ctk.CTkFont(size=10),
                text_color="#FF6B6B",
                anchor="w",
                justify="left",
                wraplength=560
            ).pack(fill="x", padx=10, pady=(0, 4))
        elif prog and is_match is not False:
            ctk.CTkLabel(
                card,
                text=f"ℹ️ {prog}",
                font=ctk.CTkFont(size=10, slant="italic"),
                text_color="#00CED1",
                anchor="w",
                justify="left",
                wraplength=560
            ).pack(fill="x", padx=10, pady=(0, 4))

        # Metadados de Linha (Início, Duração, Narração)
        meta_row = ctk.CTkFrame(card, fg_color="transparent")
        meta_row.pack(fill="x", padx=10, pady=(2, 6))

        start_epoch = ev.get("actual_start_epoch") or ev.get("scheduled_epoch")
        try:
            s_txt = datetime.fromtimestamp(float(start_epoch)).strftime("%d/%m %H:%M") if start_epoch else "N/D"
        except Exception:
            s_txt = "N/D"

        dur = ev.get("duration")
        try:
            dur_sec = int(dur) if dur is not None else 0
        except Exception:
            dur_sec = 0
        dur_txt = f"{dur_sec // 3600:02d}:{(dur_sec % 3600) // 60:02d}:{dur_sec % 60:02d}" if dur_sec > 0 else "N/D"

        details = f"Início: {s_txt}  •  Duração: {dur_txt}"
        if ev.get("narration_lines"):
            details += f"  •  Trechos: {ev['narration_lines']}"
        if ev.get("transcript_source_label"):
            details += f"  •  Fonte: {ev['transcript_source_label']}"

        ctk.CTkLabel(
            meta_row,
            text=details,
            font=ctk.CTkFont(size=10),
            text_color="#888888"
        ).pack(side="left")

        # Linha de Ações / Botões
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(4, 10))

        has_narr = bool(ev.get("narration_path") and os.path.exists(ev.get("narration_path")))
        has_pdf = bool(ev.get("pdf_path") and os.path.exists(ev.get("pdf_path")))
        sp_synced = bool(ev.get("sharepoint_synced"))

        # 1. BOTÃO DE RELATÓRIO (Partida ou Caso/Ocorrência)
        if is_match is True:
            can_generate_chrono = bool(has_narr and pipe not in ("generating", "analyzing", "transcribing"))
            if pipe == "generating":
                chrono_text = "⏳ Gerando Relatório..."
            elif pipe in ("analyzing", "transcribed") and has_narr:
                chrono_text = "🔍 Analisando Transcrição..."
            else:
                chrono_text = "📊 Gerar Relatório Cronológico"

            def make_chrono(v_id=vid):
                return lambda: self._on_generate_chronology_direct(v_id)

            ctk.CTkButton(
                btn_row,
                text=chrono_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#008080" if can_generate_chrono else "#222222",
                hover_color="#005a5a" if can_generate_chrono else "#222222",
                state="normal" if can_generate_chrono else "disabled",
                height=28,
                width=190,
                command=make_chrono()
            ).pack(side="left", padx=(0, 4))
        else:
            # Caso não seja partida narrada (Debate, Programa, Análise ou Falha)
            # Permite emitir formalmente o Relatório do Caso com diagnóstico de IA e marcas!
            def make_case_rep(v_id=vid):
                return lambda: self._on_generate_case_report_clicked(v_id)

            cat_label = t_analysis.get("event_category") or "Ocorrência"
            ctk.CTkButton(
                btn_row,
                text=f"📄 Relatório do Caso ({cat_label[:14]})",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#455a64",
                hover_color="#546e7a",
                height=28,
                width=190,
                command=make_case_rep()
            ).pack(side="left", padx=(0, 4))

        # 2. Botão Baixar Narração (.txt)
        def make_open_narr(v_id=vid):
            return lambda: self._open_narration_file(v_id)

        ctk.CTkButton(
            btn_row,
            text="📝 Narração (.txt)",
            font=ctk.CTkFont(size=11),
            fg_color="#2b5b84" if has_narr else "#222222",
            hover_color="#1d3e5a" if has_narr else "#222222",
            state="normal" if has_narr else "disabled",
            height=28,
            width=115,
            command=make_open_narr()
        ).pack(side="left", padx=3)

        # 3. Botão Abrir Relatório PDF
        def make_open_pdf(v_id=vid):
            return lambda: self._open_live_pdf(v_id)

        ctk.CTkButton(
            btn_row,
            text="📑 Relatório PDF",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#2e7d32" if has_pdf else "#222222",
            hover_color="#1b5e20" if has_pdf else "#222222",
            state="normal" if has_pdf else "disabled",
            height=28,
            width=115,
            command=make_open_pdf()
        ).pack(side="left", padx=3)

        # 4. Botão SharePoint (Sincronização Direta)
        def make_sync_sp(v_id=vid):
            return lambda: self._on_sync_sharepoint_clicked(v_id)

        sp_text = "☁️ No SharePoint" if sp_synced else "☁️ SharePoint"
        sp_fg = "#1b5e20" if sp_synced else ("#00838f" if has_pdf else "#222222")
        sp_hover = "#2e7d32" if sp_synced else ("#00acc1" if has_pdf else "#222222")

        ctk.CTkButton(
            btn_row,
            text=sp_text,
            font=ctk.CTkFont(size=11, weight="bold" if sp_synced else "normal"),
            fg_color=sp_fg,
            hover_color=sp_hover,
            text_color="#00FF7F" if sp_synced else "#ffffff",
            state="normal" if has_pdf else "disabled",
            height=28,
            width=115,
            command=make_sync_sp()
        ).pack(side="left", padx=3)

        # 5. Botão E-mail
        def make_send_mail(v_id=vid):
            return lambda: self._on_send_email_clicked(v_id)

        ctk.CTkButton(
            btn_row,
            text="✉️ E-mail",
            font=ctk.CTkFont(size=11),
            fg_color="#455a64" if (has_pdf or has_narr) else "#222222",
            hover_color="#546e7a" if (has_pdf or has_narr) else "#222222",
            state="normal" if (has_pdf or has_narr) else "disabled",
            height=28,
            width=75,
            command=make_send_mail()
        ).pack(side="left", padx=3)

        # 6. Botão Reprocessar / Forçar
        if pipe in ("ended", "failed", "not_match") or not has_narr:
            def make_reprocess(v_id=vid):
                return lambda: self._on_reprocess_clicked(v_id)

            ctk.CTkButton(
                btn_row,
                text="🔄 Reprocessar",
                font=ctk.CTkFont(size=10),
                fg_color="#6d4c41",
                hover_color="#8d6e63",
                height=28,
                width=85,
                command=make_reprocess()
            ).pack(side="left", padx=3)

        # 7. Botão Remover da Fila no Rodapé do Card
        ctk.CTkButton(
            btn_row,
            text="🗑️ Remover",
            font=ctk.CTkFont(size=11),
            fg_color="#2b1111",
            hover_color="#4a1919",
            text_color="#ff8888",
            height=28,
            width=80,
            command=make_remove_sel()
        ).pack(side="right", padx=(4, 0))



    # =========================================================================
    # HANDLERS DE AÇÃO
    # =========================================================================
    def _on_scan_all_clicked(self) -> None:
        self._log("📡 Varredura manual disparada para todos os canais cadastrados...")
        self.btn_scan_all_canais.configure(state="disabled", text="⏳ Varrendo...")
        threading.Thread(target=self._run_scan_thread, daemon=True).start()

    def _run_scan_thread(self) -> None:
        try:
            self.live_service.scan_channels()
        finally:
            self.after(0, lambda: self.btn_scan_all_canais.configure(state="normal", text="🔄 Atualizar Canais Agora"))

    def _on_auto_detect_toggle(self) -> None:
        val = bool(self._auto_detect_match_var.get())
        self.live_service.set_setting("auto_detect_match", val)
        self._log(f"🎯 Auto-Detect Jogo (avaliação automática de todas as lives): {'ATIVADO' if val else 'DESATIVADO'}")
        if val:
            self.live_service.apply_auto_detect_all(silent=False)
        else:
            self.live_service.unapply_auto_detect_waiting()
        self._refresh_canais_tab_ui()

    def _on_auto_report_toggle(self) -> None:
        val = bool(self._auto_report_live_var.get())
        self.live_service.set_setting("auto_report", val)
        self.live_service.set_setting("auto_email", val)
        self._auto_email_live_var.set(val)
        self._log(f"⚡ Auto-Relatório + E-mail automático: {'ATIVADO' if val else 'DESATIVADO'}")
        if val:
            # Se houver partidas narradas prontas na fila ainda sem PDF, dispara automaticamente
            for ev in self.live_service.list_events():
                if ev.get("selected") and ev.get("pipeline") == "ready_match" and not ev.get("pdf_path"):
                    self.live_service.run_generation_async(ev["video_id"], meta=None, auto=True)

    def _on_auto_email_toggle(self) -> None:
        val = bool(self._auto_email_live_var.get())
        self.live_service.set_setting("auto_email", val)
        self._log(f"Configuração de e-mail automático atualizada: {'ATIVADO' if val else 'DESATIVADO'}")

    def _on_generate_chronology_direct(self, vid: str) -> None:
        """Gera diretamente o relatório cronológico usando os dados extraídos na análise da transcrição (sem abrir modal)."""
        ev = self.live_service.get_event(vid)
        if not ev:
            return
        meta = self.live_service.default_meta(ev)
        self._log(f"🧠 Gerando Relatório Cronológico direto para {meta.get('team1', '')} x {meta.get('team2', '')}...")
        self.live_service.run_generation_async(vid, meta=meta, auto=False)

    def _on_add_channel_clicked(self) -> None:
        raw = self.entry_add_channel.get().strip()
        if not raw:
            messagebox.showwarning("Aviso", "Digite a URL ou @ do canal do YouTube.")
            return

        self.btn_add_channel.configure(state="disabled", text="⏳ Buscando...")

        def _do_add():
            try:
                ch = self.live_service.add_channel(raw)
                self.after(0, lambda: self.entry_add_channel.delete(0, "end"))
                self.after(0, lambda: messagebox.showinfo("Sucesso", f"Canal '{ch.get('name')}' cadastrado com sucesso!"))
            except Exception as ex:
                self.after(0, lambda: messagebox.showerror("Erro ao Cadastrar", str(ex)))
            finally:
                self.after(0, lambda: self.btn_add_channel.configure(state="normal", text="➕ Cadastrar"))

        threading.Thread(target=_do_add, daemon=True).start()

    def _on_remove_channel(self, cid: str, cname: Optional[str]) -> None:
        if messagebox.askyesno("Confirmar Exclusão", f"Deseja remover o canal '{cname or cid}' da lista de monitoramento?"):
            self.live_service.remove_channel(cid)

    def _on_add_video_clicked(self) -> None:
        url = self.entry_add_video.get().strip()
        if not url:
            messagebox.showwarning("Aviso", "Digite a URL da Live do YouTube.")
            return

        self.btn_add_video.configure(state="disabled", text="⏳ Buscando...")

        def _do_add_vid():
            try:
                ev = self.live_service.add_video_manually(url)
                self.after(0, lambda: self.entry_add_video.delete(0, "end"))
                self.after(0, lambda: messagebox.showinfo("Sucesso", f"Live '{ev.get('title')}' adicionada à fila de análise!"))
            except Exception as ex:
                self.after(0, lambda: messagebox.showerror("Erro ao Incluir Vídeo", str(ex)))
            finally:
                self.after(0, lambda: self.btn_add_video.configure(state="normal", text="➕ Incluir"))

        threading.Thread(target=_do_add_vid, daemon=True).start()

    def _on_toggle_event(self, vid: str, selected: bool) -> None:
        """Chamado ao marcar/desmarcar o checkbox de um evento na coluna esquerda."""
        try:
            self._user_toggling = True
            self.live_service.set_selected(vid, selected)
        finally:
            self._user_toggling = False
        self._refresh_kpis()
        self._render_fila_cards()

    def _on_remove_from_queue(self, vid: str) -> None:
        """Remove o evento da fila de análise com 1 clique direto na coluna direita."""
        if hasattr(self, "_incoming_cb_vars") and vid in self._incoming_cb_vars:
            try:
                self._incoming_cb_vars[vid].set(False)
            except Exception:
                pass

        try:
            self._user_toggling = True
            self.live_service.set_selected(vid, False)
        finally:
            self._user_toggling = False

        self._refresh_kpis()
        self._render_fila_cards()
        self._log(f"Evento {vid} removido da fila de análise.")

    def _open_narration_file(self, vid: str) -> None:
        ev = self.live_service.get_event(vid)
        if not ev or not ev.get("narration_path"):
            return
        path = ev["narration_path"]
        if os.path.exists(path):
            try:
                os.startfile(path)
            except Exception as ex:
                self._log(f"Erro ao abrir arquivo de narração: {ex}")

    def _open_live_pdf(self, vid: str) -> None:
        ev = self.live_service.get_event(vid)
        if not ev or not ev.get("pdf_path"):
            return
        self._open_pdf_or_folder(ev["pdf_path"])

    def _on_send_email_clicked(self, vid: str) -> None:
        recipients = self._get_configured_emails()
        if not recipients:
            if messagebox.askyesno("Destinatários Não Cadastrados", "Nenhum destinatário de e-mail foi cadastrado ainda nesta aba.\nDeseja cadastrar agora?"):
                self._open_email_recipients_modal()
            return

        def _send():
            ok = self.live_service.send_email(vid, recipients=recipients)
            if ok:
                self.after(0, lambda: messagebox.showinfo("E-mail Enviado", f"Relatório PDF e Narração (.txt) enviados com sucesso para:\n{', '.join(recipients)}"))
            else:
                self.after(0, lambda: messagebox.showwarning("Falha no Envio", "Não foi possível enviar o e-mail. Verifique suas credenciais SMTP na aba Config."))
        threading.Thread(target=_send, daemon=True).start()

    # =========================================================================
    # MODAL DE CADASTRO E GERENCIAMENTO DE DESTINATÁRIOS DE E-MAIL
    # =========================================================================
    def _open_email_recipients_modal(self) -> None:
        """Abre modal elegante para cadastrar, visualizar e remover destinatários de e-mail."""
        modal = ctk.CTkToplevel(self)
        modal.title("👥 Destinatários dos E-mails Automáticos")
        modal.geometry("540x510")
        modal.transient(self)
        modal.grab_set()

        # Cabeçalho
        ctk.CTkLabel(
            modal,
            text="👥 Destinatários de E-mails Automáticos",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#00CED1"
        ).pack(padx=16, pady=(16, 4), anchor="w")

        ctk.CTkLabel(
            modal,
            text="Cadastre quem receberá automaticamente o Relatório Técnico (PDF) e a narração completa (.txt) assim que uma partida narrada ao vivo for encerrada e analisada.",
            font=ctk.CTkFont(size=11),
            text_color="#aaaaaa",
            justify="left",
            wraplength=500
        ).pack(padx=16, pady=(0, 12), anchor="w")

        # Linha de Cadastro (Entry + Botão)
        add_frame = ctk.CTkFrame(modal, fg_color="#181818", corner_radius=8, border_width=1, border_color="#2b2b2b")
        add_frame.pack(fill="x", padx=16, pady=(0, 8))

        e_input = ctk.CTkEntry(
            add_frame,
            placeholder_text="Digite o e-mail (ex: cleber.goncalves@ibope.com)...",
            font=ctk.CTkFont(size=11),
            height=32
        )
        e_input.pack(side="left", fill="x", expand=True, padx=(8, 6), pady=8)

        lbl_status = ctk.CTkLabel(modal, text="", font=ctk.CTkFont(size=10), text_color="#00FF7F")
        lbl_status.pack(padx=16, pady=(0, 4), anchor="w")

        # Frame de Lista de E-mails
        list_container = ctk.CTkFrame(modal, fg_color="#141414", corner_radius=8, border_width=1, border_color="#262626")
        list_container.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        list_hdr = ctk.CTkFrame(list_container, fg_color="transparent")
        list_hdr.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(list_hdr, text="E-MAILS CADASTRADOS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#888888").pack(side="left")
        lbl_count = ctk.CTkLabel(list_hdr, text="0 cadastrado(s)", font=ctk.CTkFont(size=10), text_color="#00CED1")
        lbl_count.pack(side="right")

        scroll_emails = ctk.CTkScrollableFrame(list_container, fg_color="#0a0a0a", corner_radius=6)
        scroll_emails.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        def _refresh_list():
            for w in scroll_emails.winfo_children():
                w.destroy()
            cur_emails = self._get_configured_emails()
            lbl_count.configure(text=f"{len(cur_emails)} cadastrado(s)")
            self._update_emails_button_text()
            if not cur_emails:
                ctk.CTkLabel(
                    scroll_emails,
                    text="Nenhum destinatário cadastrado ainda.\nDigite um e-mail acima e clique em '➕ Adicionar E-mail'.",
                    font=ctk.CTkFont(size=11),
                    text_color="#666666"
                ).pack(pady=30)
                return

            for em in cur_emails:
                row = ctk.CTkFrame(scroll_emails, fg_color="#181818", corner_radius=6, height=36)
                row.pack(fill="x", pady=2, padx=2)
                row.pack_propagate(False)

                ctk.CTkLabel(row, text="✉️", font=ctk.CTkFont(size=12)).pack(side="left", padx=(8, 4))
                ctk.CTkLabel(
                    row,
                    text=em,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="#ffffff"
                ).pack(side="left", padx=4)

                def make_del(target_email=em):
                    def _do_del():
                        curr = self._get_configured_emails()
                        if target_email in curr:
                            curr.remove(target_email)
                            self._save_configured_emails(curr)
                            lbl_status.configure(text=f"✓ E-mail '{target_email}' removido com sucesso.", text_color="#FF8888")
                            _refresh_list()
                    return _do_del

                ctk.CTkButton(
                    row,
                    text="🗑️ Remover",
                    width=75,
                    height=24,
                    fg_color="#3a1414",
                    hover_color="#5f1d1d",
                    text_color="#ff8888",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    command=make_del()
                ).pack(side="right", padx=6)

        def _add_email():
            raw = e_input.get().strip()
            if not raw:
                lbl_status.configure(text="⚠️ Digite um endereço de e-mail.", text_color="#FFB74D")
                return
            if "@" not in raw or "." not in raw.split("@")[-1] or len(raw) < 6:
                lbl_status.configure(text="⚠️ Formato de e-mail inválido. Ex: nome@empresa.com", text_color="#FF6B6B")
                return
            curr = self._get_configured_emails()
            if any(e.lower() == raw.lower() for e in curr):
                lbl_status.configure(text="ℹ️ Este e-mail já está cadastrado.", text_color="#FFD700")
                return
            curr.append(raw)
            self._save_configured_emails(curr)
            e_input.delete(0, "end")
            lbl_status.configure(text=f"✓ E-mail '{raw}' adicionado com sucesso!", text_color="#00FF7F")
            _refresh_list()

        btn_add = ctk.CTkButton(
            add_frame,
            text="➕ Adicionar E-mail",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1f77b4",
            hover_color="#155584",
            width=135,
            height=32,
            command=_add_email
        )
        btn_add.pack(side="right", padx=(0, 8), pady=8)
        e_input.bind("<Return>", lambda e: _add_email())

        # Barra inferior
        b_bar = ctk.CTkFrame(modal, fg_color="transparent")
        b_bar.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkButton(
            b_bar,
            text="✓ Concluir / Fechar",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#008080",
            hover_color="#005a5a",
            width=130,
            height=32,
            command=modal.destroy
        ).pack(side="right")

        _refresh_list()

    # =========================================================================
    # MODAL DE GERAÇÃO DE CRONOLOGIA (COM CONFERÊNCIA DE TIMES/DATA)
    # =========================================================================
    def _open_generate_chronology_modal(self, vid: str) -> None:
        ev = self.live_service.get_event(vid)
        if not ev:
            return

        meta = self.live_service.default_meta(ev)

        modal = ctk.CTkToplevel(self)
        modal.title("🧠 Gerar Cronologia da Narração")
        modal.geometry("520x460")
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(
            modal,
            text="🧠 Gerar Cronologia Técnica a partir da Narração",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#00CED1"
        ).pack(padx=15, pady=(15, 4), anchor="w")

        ctk.CTkLabel(
            modal,
            text=f"Live: {ev.get('title', '')[:70]}...\nCanal: {ev.get('channel_name', '')}",
            font=ctk.CTkFont(size=11),
            text_color="#aaaaaa",
            justify="left"
        ).pack(padx=15, pady=(0, 10), anchor="w")

        box = ctk.CTkFrame(modal, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2b2b2b")
        box.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Time 1
        ctk.CTkLabel(box, text="Time Mandante (Time 1):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))
        e_t1 = ctk.CTkEntry(box, font=ctk.CTkFont(size=11))
        e_t1.insert(0, meta.get("team1", ""))
        e_t1.pack(fill="x", padx=12, pady=(0, 6))

        # Time 2
        ctk.CTkLabel(box, text="Time Visitante (Time 2):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(4, 2))
        e_t2 = ctk.CTkEntry(box, font=ctk.CTkFont(size=11))
        e_t2.insert(0, meta.get("team2", ""))
        e_t2.pack(fill="x", padx=12, pady=(0, 6))

        # Competição
        ctk.CTkLabel(box, text="Competição:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(4, 2))
        e_comp = ctk.CTkEntry(box, font=ctk.CTkFont(size=11))
        e_comp.insert(0, meta.get("competition", "Brasileirão Série A"))
        e_comp.pack(fill="x", padx=12, pady=(0, 6))

        # Data
        ctk.CTkLabel(box, text="Data do Jogo (DD/MM/AAAA):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(4, 2))
        e_date = ctk.CTkEntry(box, font=ctk.CTkFont(size=11))
        e_date.insert(0, meta.get("date", datetime.now().strftime("%d/%m/%Y")))
        e_date.pack(fill="x", padx=12, pady=(0, 10))

        # Barra inferior
        btn_bar = ctk.CTkFrame(modal, fg_color="transparent")
        btn_bar.pack(fill="x", padx=15, pady=(0, 15))

        def _cancel():
            modal.destroy()

        def _start_gen():
            updated_meta = {
                "team1": e_t1.get().strip() or "Time 1",
                "team2": e_t2.get().strip() or "Time 2",
                "competition": e_comp.get().strip() or "Brasileirão",
                "date": e_date.get().strip() or datetime.now().strftime("%d/%m/%Y"),
            }
            modal.destroy()
            self._log(f"Iniciando geração de cronologia para {updated_meta['team1']} x {updated_meta['team2']}...")
            self.live_service.run_generation_async(vid, meta=updated_meta, auto=False)

        ctk.CTkButton(btn_bar, text="Cancelar", fg_color="#333333", hover_color="#444444", width=100, command=_cancel).pack(side="left")
        ctk.CTkButton(btn_bar, text="▶️ Gerar Cronologia Agora", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#00CED1", text_color="#000000", hover_color="#008B8B", command=_start_gen).pack(side="right")


    def _on_generate_case_report_clicked(self, vid: str) -> None:
        """Gera, publica no SharePoint e abre imediatamente o Relatório Técnico de Ocorrência."""
        self._log(f"📄 Gerando Relatório do Caso para o evento {vid}...")
        def _do_case():
            res = self.live_service.generate_case_report_for_event(vid)
            if res.get("ok"):
                pdf = res.get("pdf_path")
                # Abre imediatamente na tela do usuário
                if pdf and os.path.exists(pdf):
                    try:
                        os.startfile(pdf)
                    except Exception as e:
                        self._log(f"Erro ao abrir PDF de ocorrência: {e}")
                self.after(0, lambda: messagebox.showinfo(
                    "Relatório de Ocorrência Aberto",
                    f"Relatório Técnico de Ocorrência gerado e aberto na tela!\nPublicado também no SharePoint.\n\nArquivo:\n{os.path.basename(pdf)}"
                ))
                self.after(0, self._render_fila_cards)
            else:
                self.after(0, lambda: messagebox.showerror("Erro ao Gerar", res.get("error") or "Falha ao gerar relatório de ocorrência."))
        threading.Thread(target=_do_case, daemon=True).start()

    def _on_sync_sharepoint_clicked(self, vid: str) -> None:
        """Sincroniza manualmente o relatório de um evento com o SharePoint."""
        self._log(f"☁️ Sincronizando evento {vid} com o SharePoint...")
        def _do_sp():
            ok = self.live_service.sync_event_to_sharepoint(vid)
            if ok:
                self.after(0, lambda: messagebox.showinfo("SharePoint Sincronizado", "Relatório publicado com sucesso na biblioteca 'Relatorios_de_Jogos' do SharePoint!"))
                self.after(0, self._render_fila_cards)
            else:
                self.after(0, lambda: messagebox.showwarning("Falha no SharePoint", "Não foi possível sincronizar o relatório no SharePoint. Verifique a conexão com a rede/Graph API."))
        threading.Thread(target=_do_sp, daemon=True).start()

    def _on_audit_report_clicked(self) -> None:
        """Gera o Relatório Executivo Geral de Auditoria, publica no SharePoint e abre o PDF na tela na hora."""
        self._log("📋 Iniciando geração do Relatório Geral de Auditoria de Lives...")
        if hasattr(self, "btn_audit_report"):
            self.btn_audit_report.configure(state="disabled", text="⏳ Gerando...")

        def _do_audit():
            try:
                res = self.live_service.generate_all_cases_audit_report()
                if res.get("ok"):
                    pdf = res.get("pdf_path")
                    tot = res.get("total_events", 0)
                    self._log(f"✅ Relatório Geral de Auditoria concluído: {pdf}")
                    
                    # Abre imediatamente o arquivo PDF na tela do usuário
                    if pdf and os.path.exists(pdf):
                        try:
                            os.startfile(pdf)
                        except Exception as e:
                            self._log(f"Erro ao abrir PDF: {e}")

                    self.after(0, lambda: messagebox.showinfo(
                        "Auditoria de Lives Aberta",
                        f"Relatório Geral de Auditoria gerado e aberto com sucesso!\nPublicado também no SharePoint.\n\n"
                        f"Total de transmissões auditadas: {tot}\n"
                        f"Arquivo: {os.path.basename(pdf)}"
                    ))
                else:
                    self.after(0, lambda: messagebox.showerror("Falha na Auditoria", res.get("error") or "Erro ao consolidar auditoria."))
            finally:
                if hasattr(self, "btn_audit_report"):
                    self.after(0, lambda: self.btn_audit_report.configure(state="normal", text="📋 Relatório Geral de Auditoria"))
        threading.Thread(target=_do_audit, daemon=True).start()

    def _on_clean_queue_clicked(self) -> None:
        """Limpa da fila eventos antigos desnecessários mantendo apenas ativas e relatórios prontos."""
        removed = self.live_service.clean_queue_keep_active()
        messagebox.showinfo("Fila Limpa", f"{removed} eventos antigos foram removidos da fila.\nApenas eventos ativos e com relatórios prontos foram mantidos.")
        self._render_fila_cards()
        self._refresh_kpis()

    def _on_open_reports_folder_clicked(self) -> None:
        """Abre a pasta reports no Windows Explorer com 1 clique direto."""
        import glob
        from gui.main_gui import PROJECT_ROOT
        reports_dir = os.path.join(str(PROJECT_ROOT), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        try:
            os.startfile(reports_dir)
        except Exception as ex:
            self._log(f"Erro ao abrir pasta de relatórios: {ex}")

    def _open_recent_reports_modal(self) -> None:
        """Abre modal responsivo listando todos os relatórios gerados recentemente."""
        from gui.main_gui import PROJECT_ROOT
        reports_dir = os.path.join(str(PROJECT_ROOT), "reports")
        os.makedirs(reports_dir, exist_ok=True)

        modal = ctk.CTkToplevel(self)
        modal.title("📑 Central de Relatórios Gerados")
        modal.geometry("780x560")
        modal.transient(self)
        modal.grab_set()

        hdr = ctk.CTkFrame(modal, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(hdr, text="📑 Relatórios PDF Gerados (Prontos p/ Visualização)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00FF7F").pack(side="left")

        ctk.CTkButton(
            hdr,
            text="📂 Abrir Pasta no Explorer",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#37474f",
            hover_color="#455a64",
            height=28,
            width=170,
            command=self._on_open_reports_folder_clicked
        ).pack(side="right")

        scroll = ctk.CTkScrollableFrame(modal, fg_color="#121212", corner_radius=8)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        import glob
        pdf_files = sorted(glob.glob(os.path.join(reports_dir, "*.pdf")), key=os.path.getmtime, reverse=True)

        if not pdf_files:
            ctk.CTkLabel(scroll, text="Nenhum relatório PDF encontrado na pasta de relatórios.", font=ctk.CTkFont(size=12), text_color="#888888").pack(pady=40)
            return

        for p in pdf_files[:50]:
            fname = os.path.basename(p)
            sz_kb = os.path.getsize(p) // 1024
            mtime = datetime.fromtimestamp(os.path.getmtime(p)).strftime("%d/%m/%Y %H:%M")

            row = ctk.CTkFrame(scroll, fg_color="#1a1a1a", corner_radius=6)
            row.pack(fill="x", pady=3, padx=4)

            info_col = ctk.CTkFrame(row, fg_color="transparent")
            info_col.pack(side="left", fill="x", expand=True, padx=10, pady=6)

            ctk.CTkLabel(info_col, text=fname, font=ctk.CTkFont(size=11, weight="bold"), text_color="#ffffff", anchor="w").pack(fill="x")
            ctk.CTkLabel(info_col, text=f"Data: {mtime}   |   Tamanho: {sz_kb} KB", font=ctk.CTkFont(size=10), text_color="#888888", anchor="w").pack(fill="x")

            def make_open(p_file=p):
                return lambda: os.startfile(p_file)

            ctk.CTkButton(
                row,
                text="👁️ Abrir PDF",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#2e7d32",
                hover_color="#1b5e20",
                height=28,
                width=100,
                command=make_open()
            ).pack(side="right", padx=10, pady=6)

    def _on_set_fila_filter(self, mode: str) -> None:
        self._fila_filter_mode = mode
        self._render_fila_cards()

    def _on_load_more_fila(self) -> None:
        self._fila_limit += 15
        self._render_fila_cards()

    def _on_show_all_fila(self) -> None:
        self._fila_limit = 9999
        self._render_fila_cards()

    def _on_load_more_incoming(self) -> None:
        self._incoming_limit += 25
        self._render_incoming_list()

    def _on_reprocess_clicked(self, vid: str) -> None:
        """Reprocessa a transcrição ou análise do evento."""
        ev = self.live_service.get_event(vid)
        if not ev:
            return
        if messagebox.askyesno("Reprocessar Evento", f"Deseja reprocessar a live '{ev.get('title', vid)[:50]}' forçando nova transcrição e análise de IA?"):
            self._log(f"🔄 Disparando reprocessamento completo da live {vid}...")
            self.live_service.update_event(vid, pipeline="transcribing", error="", progress="Reprocessando transcrição...", is_match_narration=None)
            self.live_service.run_transcription_async(vid, force_audio=True)
            self._render_fila_cards()
