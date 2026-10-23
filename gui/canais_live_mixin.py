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
        self._auto_email_live_var = ctk.BooleanVar(value=True)
        self._live_cards_cache: Dict[str, Any] = {}
        self._live_incoming_cache: Dict[str, Any] = {}

        self.live_service = LiveNarrationService(
            reporter=self.reporter,
            config_provider=self._get_live_service_config,
            log=self._log,
            on_change=lambda: self.after(0, self._refresh_canais_tab_ui)
        )
        self._auto_email_live_var.set(self.live_service.get_setting("auto_email", True))
        self.live_service.start()

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
            cfg["emails"] = _load_saved_emails()
            cfg["smtp_server"] = EMAIL_SMTP_SERVER
            cfg["smtp_port"] = EMAIL_SMTP_PORT
        except Exception as ex:
            self._log(f"⚠️ [CANAIS LIVE] Erro ao ler configurações: {ex}")
        return cfg

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

        # KPI 1: Canais Cadastrados
        kpi1 = ctk.CTkFrame(kpi_bar, fg_color="#1b1b1b", corner_radius=8, width=170, height=54)
        kpi1.pack(side="left", padx=8, pady=8)
        kpi1.pack_propagate(False)
        ctk.CTkLabel(kpi1, text="📺 CANAIS MONITORADOS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_kpi_canais_count = ctk.CTkLabel(kpi1, text="0", font=ctk.CTkFont(size=15, weight="bold"), text_color="#00CED1")
        self.lbl_kpi_canais_count.pack(anchor="w", padx=10, pady=(0, 4))

        # KPI 2: Eventos Futuros / Ao Vivo
        kpi2 = ctk.CTkFrame(kpi_bar, fg_color="#1b1b1b", corner_radius=8, width=180, height=54)
        kpi2.pack(side="left", padx=4, pady=8)
        kpi2.pack_propagate(False)
        ctk.CTkLabel(kpi2, text="📅 EVENTOS ENCONTRADOS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_kpi_eventos_count = ctk.CTkLabel(kpi2, text="0", font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFD700")
        self.lbl_kpi_eventos_count.pack(anchor="w", padx=10, pady=(0, 4))

        # KPI 3: Fila de Análise
        kpi3 = ctk.CTkFrame(kpi_bar, fg_color="#1b1b1b", corner_radius=8, width=170, height=54)
        kpi3.pack(side="left", padx=4, pady=8)
        kpi3.pack_propagate(False)
        ctk.CTkLabel(kpi3, text="🎯 FILA DE ANÁLISE", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_kpi_fila_count = ctk.CTkLabel(kpi3, text="0", font=ctk.CTkFont(size=15, weight="bold"), text_color="#00FF7F")
        self.lbl_kpi_fila_count.pack(anchor="w", padx=10, pady=(0, 4))

        # Botão: Atualizar Todos os Canais Agora
        self.btn_scan_all_canais = ctk.CTkButton(
            kpi_bar,
            text="🔄 Atualizar Canais Agora",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#008080",
            hover_color="#005a5a",
            height=34,
            width=180,
            command=self._on_scan_all_clicked
        )
        self.btn_scan_all_canais.pack(side="left", padx=12, pady=8)

        # Switch: Auto Envio de E-mail
        self.switch_auto_email = ctk.CTkSwitch(
            kpi_bar,
            text="✉️ Auto E-mail ao Concluir (PDF + .txt)",
            font=ctk.CTkFont(size=11, weight="bold"),
            variable=self._auto_email_live_var,
            progress_color="#00CED1",
            command=self._on_auto_email_toggle
        )
        self.switch_auto_email.pack(side="left", padx=12, pady=8)

        self.lbl_live_status_hint = ctk.CTkLabel(
            kpi_bar,
            text="Varredura automática ativa (a cada 10 min) • Sem SharePoint",
            font=ctk.CTkFont(size=10),
            text_color="#777777"
        )
        self.lbl_live_status_hint.pack(side="right", padx=15, pady=8)

        # ---------------------------------------------------------------------
        # 2. CORPO PRINCIPAL (2 COLUNAS)
        # ---------------------------------------------------------------------
        body = ctk.CTkFrame(container, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=2, pady=2)

        # ---------------------- COLUNA ESQUERDA (CANAIS & EVENTOS) ----------------------
        col_left = ctk.CTkFrame(body, fg_color="#121212", corner_radius=10, border_width=1, border_color="#222222")
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=2)

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
        col_right.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=2)

        sec_queue_hdr = ctk.CTkFrame(col_right, fg_color="transparent")
        sec_queue_hdr.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            sec_queue_hdr,
            text="🎙️ FILA DE ANÁLISE E CRONOLOGIA DE NARRAÇÃO",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00FF7F"
        ).pack(side="left")

        self.lbl_queue_sub = ctk.CTkLabel(
            col_right,
            text="Fluxo: Upcoming ➔ Ao Vivo ➔ Término ➔ Transcrição Áudio (.txt) ➔ Cronologia Técnica (PDF)",
            font=ctk.CTkFont(size=10),
            text_color="#777777"
        )
        self.lbl_queue_sub.pack(anchor="w", padx=12, pady=(0, 6))

        # Scroll de Cards da Fila
        self.scroll_fila = ctk.CTkScrollableFrame(col_right, fg_color="#0a0a0a", corner_radius=8)
        self.scroll_fila.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Renderização inicial
        self._refresh_canais_tab_ui()

    # =========================================================================
    # REFRESH E ATUALIZAÇÃO DOS CARDS
    # =========================================================================
    def _refresh_canais_tab_ui(self) -> None:
        """Atualiza KPIs, lista de canais, eventos incoming e cards da fila de análise."""
        if not hasattr(self, "scroll_canais") or not hasattr(self, "scroll_fila"):
            return

        channels = self.live_service.list_channels()
        events = self.live_service.list_events()

        # KPIs
        selected_events = [e for e in events if e.get("selected")]
        done_events = [e for e in selected_events if e.get("pipeline") in ("transcribed", "done")]

        self.lbl_kpi_canais_count.configure(text=str(len(channels)))
        self.lbl_kpi_eventos_count.configure(text=str(len(events)))
        self.lbl_kpi_fila_count.configure(text=str(len(selected_events)))
        if hasattr(self, "lbl_kpi_prontos_count"):
            self.lbl_kpi_prontos_count.configure(text=str(len(done_events)))

        # 1. Renderiza Canais
        for w in self.scroll_canais.winfo_children():
            w.destroy()

        if not channels:
            ctk.CTkLabel(
                self.scroll_canais,
                text="Nenhum canal cadastrado ainda. Digite a URL ou @ acima e clique em 'Cadastrar'.",
                font=ctk.CTkFont(size=11),
                text_color="#666666"
            ).pack(pady=15)
        else:
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

        # 2. Renderiza Próximos Eventos (Incoming / Ao Vivo)
        for w in self.scroll_incoming.winfo_children():
            w.destroy()

        # Ordenação: Ao Vivo primeiro, depois Upcoming por data
        def incoming_sort_key(ev):
            st = ev.get("status")
            prio = 0 if st == "live" else (1 if st == "upcoming" else 2)
            epoch = ev.get("scheduled_epoch") or ev.get("actual_start_epoch") or 9999999999
            return (prio, epoch)

        sorted_events = sorted(events, key=incoming_sort_key)

        if not sorted_events:
            ctk.CTkLabel(
                self.scroll_incoming,
                text="Nenhum evento encontrado nos canais cadastrados.\nClique em 'Atualizar Canais Agora' para escanear transmissões futuras.",
                font=ctk.CTkFont(size=11),
                text_color="#666666"
            ).pack(pady=20)
        else:
            for ev in sorted_events:
                vid = ev["video_id"]
                card = ctk.CTkFrame(self.scroll_incoming, fg_color="#161616", corner_radius=8)
                card.pack(fill="x", pady=3, padx=2)

                top_line = ctk.CTkFrame(card, fg_color="transparent")
                top_line.pack(fill="x", padx=8, pady=(6, 2))

                # Checkbox de Seleção
                is_sel = bool(ev.get("selected"))
                cb_var = ctk.BooleanVar(value=is_sel)

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
                    t_str = datetime.fromtimestamp(sched).strftime("%d/%m %H:%M") if sched else "Futuro"
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
                    wraplength=480
                )
                lbl_title.pack(fill="x", padx=32, pady=(0, 6))

        # 3. Renderiza Fila de Análise (Coluna Direita)
        for w in self.scroll_fila.winfo_children():
            w.destroy()

        if not selected_events:
            ctk.CTkLabel(
                self.scroll_fila,
                text="Nenhum evento selecionado para análise.\nMarque as caixas de seleção [✓] na coluna à esquerda para adicionar eventos à fila.",
                font=ctk.CTkFont(size=11),
                text_color="#666666"
            ).pack(pady=40)
        else:
            for ev in selected_events:
                vid = ev["video_id"]
                pipe = ev.get("pipeline", "waiting")
                badge_info = PIPELINE_LABELS.get(pipe, ("⏳ Na Fila", "#FFD700"))

                card = ctk.CTkFrame(self.scroll_fila, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2a2a2a")
                card.pack(fill="x", pady=5, padx=4)

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
                    text=f"• {ev.get('channel_name', 'YouTube')}",
                    font=ctk.CTkFont(size=11),
                    text_color="#999999"
                ).pack(side="left", padx=6)

                # Botão Remover da Fila
                def make_remove_sel(v_id=vid):
                    return lambda: self.live_service.set_selected(v_id, False)

                ctk.CTkButton(
                    hdr,
                    text="✕",
                    width=22,
                    height=20,
                    fg_color="transparent",
                    hover_color="#550000",
                    font=ctk.CTkFont(size=11),
                    command=make_remove_sel()
                ).pack(side="right")

                # Título
                ctk.CTkLabel(
                    card,
                    text=ev.get("title", vid),
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#ffffff",
                    anchor="w",
                    justify="left",
                    wraplength=520
                ).pack(fill="x", padx=10, pady=(2, 4))

                # Mensagem de Progresso / Erro
                prog = ev.get("progress") or ""
                err = ev.get("error") or ""
                if err:
                    ctk.CTkLabel(
                        card,
                        text=f"⚠️ {err}",
                        font=ctk.CTkFont(size=10),
                        text_color="#FF6B6B",
                        anchor="w",
                        justify="left",
                        wraplength=520
                    ).pack(fill="x", padx=10, pady=(0, 4))
                elif prog:
                    ctk.CTkLabel(
                        card,
                        text=f"ℹ️ {prog}",
                        font=ctk.CTkFont(size=10, slant="italic"),
                        text_color="#00CED1",
                        anchor="w"
                    ).pack(fill="x", padx=10, pady=(0, 4))

                # Metadados de Linha (Início, Duração, Narração)
                meta_row = ctk.CTkFrame(card, fg_color="transparent")
                meta_row.pack(fill="x", padx=10, pady=(2, 6))

                start_epoch = ev.get("actual_start_epoch") or ev.get("scheduled_epoch")
                s_txt = datetime.fromtimestamp(start_epoch).strftime("%d/%m %H:%M") if start_epoch else "N/D"
                dur = ev.get("duration") or 0
                dur_txt = f"{dur//3600:02d}:{(dur%3600)//60:02d}:{dur%60:02d}" if dur else "N/D"

                details = f"Início: {s_txt}  •  Duração: {dur_txt}"
                if ev.get("narration_lines"):
                    details += f"  •  Trechos: {ev['narration_lines']}"
                if ev.get("transcript_source_label"):
                    details += f"  •  Fonte: {ev['transcript_source_label']}"

                ctk.CTkLabel(
                    meta_row,
                    text=details,
                    font=ctk.CTkFont(size=9.5),
                    text_color="#888888"
                ).pack(side="left")

                # Linha de Ações / Botões
                btn_row = ctk.CTkFrame(card, fg_color="transparent")
                btn_row.pack(fill="x", padx=10, pady=(4, 10))

                has_narr = bool(ev.get("narration_path") and os.path.exists(ev.get("narration_path")))
                has_pdf = bool(ev.get("pdf_path") and os.path.exists(ev.get("pdf_path")))

                # 1. Botão Gerar Cronologia
                def make_chrono(v_id=vid):
                    return lambda: self._open_generate_chronology_modal(v_id)

                chrono_btn = ctk.CTkButton(
                    btn_row,
                    text="🧠 Gerar Cronologia",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#008080" if has_narr else "#333333",
                    hover_color="#005a5a" if has_narr else "#333333",
                    state="normal" if has_narr else "disabled",
                    height=28,
                    width=140,
                    command=make_chrono()
                )
                chrono_btn.pack(side="left", padx=(0, 6))

                # 2. Botão Baixar Narração (.txt)
                def make_open_narr(v_id=vid):
                    return lambda: self._open_narration_file(v_id)

                narr_btn = ctk.CTkButton(
                    btn_row,
                    text="💾 Narração (.txt)",
                    font=ctk.CTkFont(size=11),
                    fg_color="#2b5b84" if has_narr else "#222222",
                    hover_color="#1d3e5a" if has_narr else "#222222",
                    state="normal" if has_narr else "disabled",
                    height=28,
                    width=120,
                    command=make_open_narr()
                )
                narr_btn.pack(side="left", padx=4)

                # 3. Botão Abrir Relatório PDF
                def make_open_pdf(v_id=vid):
                    return lambda: self._open_live_pdf(v_id)

                pdf_btn = ctk.CTkButton(
                    btn_row,
                    text="📄 Abrir Relatório",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#2e7d32" if has_pdf else "#222222",
                    hover_color="#1b5e20" if has_pdf else "#222222",
                    state="normal" if has_pdf else "disabled",
                    height=28,
                    width=130,
                    command=make_open_pdf()
                )
                pdf_btn.pack(side="left", padx=4)

                # 4. Botão E-mail
                def make_send_mail(v_id=vid):
                    return lambda: self._on_send_email_clicked(v_id)

                mail_btn = ctk.CTkButton(
                    btn_row,
                    text="✉️ E-mail",
                    font=ctk.CTkFont(size=11),
                    fg_color="#455a64" if (has_pdf or has_narr) else "#222222",
                    hover_color="#546e7a" if (has_pdf or has_narr) else "#222222",
                    state="normal" if (has_pdf or has_narr) else "disabled",
                    height=28,
                    width=85,
                    command=make_send_mail()
                )
                mail_btn.pack(side="left", padx=4)

                # Botão Forçar Transcrição de Áudio se falhou ou aguardando
                if pipe in ("ended", "failed"):
                    def make_force(v_id=vid):
                        return lambda: self.live_service.run_transcription_async(v_id, force_audio=True)

                    ctk.CTkButton(
                        btn_row,
                        text="🔊 Transcrever Áudio",
                        font=ctk.CTkFont(size=10),
                        fg_color="#8d6e63",
                        hover_color="#6d4c41",
                        height=28,
                        width=120,
                        command=make_force()
                    ).pack(side="left", padx=4)

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

    def _on_auto_email_toggle(self) -> None:
        val = bool(self._auto_email_live_var.get())
        self.live_service.set_setting("auto_email", val)
        self._log(f"Configuração de e-mail automático atualizada: {'ATIVADO' if val else 'DESATIVADO'}")

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
        self.live_service.set_selected(vid, selected)

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
        def _send():
            ok = self.live_service.send_email(vid)
            if ok:
                self.after(0, lambda: messagebox.showinfo("E-mail Enviado", "Relatório PDF e Narração (.txt) enviados com sucesso por e-mail!"))
            else:
                self.after(0, lambda: messagebox.showwarning("Falha no Envio", "Não foi possível enviar o e-mail. Verifique os destinatários e credenciais SMTP na aba Config."))
        threading.Thread(target=_send, daemon=True).start()

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
            font=ctk.CTkFont(size=10.5),
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
