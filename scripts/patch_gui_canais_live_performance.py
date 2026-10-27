# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def patch_gui():
    path = Path("gui/canais_live_mixin.py")
    content = path.read_text(encoding="utf-8")

    # 1. Update _init_canais_live to set up debounce and pagination variables
    init_old = """        self._user_toggling: bool = False
        self._live_cards_cache: Dict[str, Any] = {}
        self._live_incoming_cache: Dict[str, Any] = {}"""

    init_new = """        self._user_toggling: bool = False
        self._refresh_timer = None
        self._fila_filter_mode: str = "all"  # "all", "active", "done"
        self._fila_limit: int = 15
        self._incoming_limit: int = 25
        self._live_cards_cache: Dict[str, Any] = {}
        self._live_incoming_cache: Dict[str, Any] = {}"""

    if init_old in content:
        content = content.replace(init_old, init_new)
        print("[+] _init_canais_live variables initialized!")

    # 2. Update _on_service_state_changed with smart 350ms debounce
    deb_old = """    def _on_service_state_changed(self) -> None:
        \"\"\"Callback acionado pelo serviço de monitoramento em background.\"\"\"
        if getattr(self, "_user_toggling", False):
            return
        self._refresh_canais_tab_ui()"""

    deb_new = """    def _on_service_state_changed(self) -> None:
        \"\"\"Callback acionado pelo serviço de monitoramento em background com debounce suave.\"\"\"
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
        self._refresh_canais_tab_ui()"""

    if deb_old in content:
        content = content.replace(deb_old, deb_new)
        print("[+] _on_service_state_changed debounced!")

    # 3. Add reports folder and recent reports buttons to kpi_row1
    old_row1_btn = """        # Botão: Relatório Geral de Casos / Auditoria de Lives
        self.btn_audit_report = ctk.CTkButton(
            kpi_row1,
            text="📋 Relatório Geral de Auditoria",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#4a148c",
            hover_color="#6a1b9a",
            height=34,
            width=200,
            command=self._on_audit_report_clicked
        )
        self.btn_audit_report.pack(side="left", padx=6, pady=2)"""

    new_row1_btn = """        # Botão: Relatório Geral de Casos / Auditoria de Lives
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
        self.btn_view_recent_reports.pack(side="left", padx=5, pady=2)"""

    if old_row1_btn in content:
        content = content.replace(old_row1_btn, new_row1_btn)
        print("[+] Added Reports Folder and View Reports buttons to top bar!")

    # 4. Enhance sec_queue_hdr with filters and queue cleanup
    old_sec_queue = """        # SEÇÃO C: FILA DE ANÁLISE DE TRANSMISSÕES (COLUNA DIREITA)
        sec_queue_hdr = ctk.CTkFrame(col_right, fg_color="transparent")
        sec_queue_hdr.pack(fill="x", padx=10, pady=(10, 2))

        ctk.CTkLabel(
            sec_queue_hdr,
            text="🎯 FILA DE ANÁLISE E CRONOLOGIA",
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
        self.btn_queue_emails.pack(side="right")"""

    new_sec_queue = """        # SEÇÃO C: FILA DE ANÁLISE DE TRANSMISSÕES (COLUNA DIREITA)
        sec_queue_hdr = ctk.CTkFrame(col_right, fg_color="transparent")
        sec_queue_hdr.pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            sec_queue_hdr,
            text="🎯 FILA DE ANÁLISE",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00FF7F",
            anchor="w"
        ).pack(side="left", padx=(0, 10))

        # Filtros Rápidos (Leveza & Usabilidade)
        self.btn_filter_all = ctk.CTkButton(
            sec_queue_hdr,
            text="Todas",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#2b5b84" if self._fila_filter_mode == "all" else "#1c1c1c",
            hover_color="#3a7ab3",
            height=24,
            width=65,
            command=lambda: self._on_set_fila_filter("all")
        )
        self.btn_filter_all.pack(side="left", padx=2)

        self.btn_filter_active = ctk.CTkButton(
            sec_queue_hdr,
            text="🟡 Ativas",
            font=ctk.CTkFont(size=10),
            fg_color="#8d6e63" if self._fila_filter_mode == "active" else "#1c1c1c",
            hover_color="#a1887f",
            height=24,
            width=70,
            command=lambda: self._on_set_fila_filter("active")
        )
        self.btn_filter_active.pack(side="left", padx=2)

        self.btn_filter_done = ctk.CTkButton(
            sec_queue_hdr,
            text="🟢 Prontas",
            font=ctk.CTkFont(size=10),
            fg_color="#2e7d32" if self._fila_filter_mode == "done" else "#1c1c1c",
            hover_color="#388e3c",
            height=24,
            width=75,
            command=lambda: self._on_set_fila_filter("done")
        )
        self.btn_filter_done.pack(side="left", padx=2)

        # Botão Limpar Fila Antiga
        self.btn_clean_queue = ctk.CTkButton(
            sec_queue_hdr,
            text="🧹 Limpar Antigas",
            font=ctk.CTkFont(size=10),
            fg_color="#3a1414",
            hover_color="#5f1d1d",
            text_color="#ffaaaa",
            height=24,
            width=105,
            command=self._on_clean_queue_clicked
        )
        self.btn_clean_queue.pack(side="left", padx=(6, 2))

        # Botão rápido de gerenciar destinatários no topo da fila
        self.btn_queue_emails = ctk.CTkButton(
            sec_queue_hdr,
            text="👥 Destinatários",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1f538d",
            hover_color="#14375e",
            height=26,
            width=125,
            command=self._open_email_recipients_modal
        )
        self.btn_queue_emails.pack(side="right")"""

    if old_sec_queue in content:
        content = content.replace(old_sec_queue, new_sec_queue)
        print("[+] Enhanced sec_queue_hdr with filter pills and clean queue button!")

    # 5. Overhaul _render_incoming_list with limit and Load More
    old_incoming_loop = """        sorted_events = sorted(events, key=incoming_sort_key)

        for w in self.scroll_incoming.winfo_children():
            w.destroy()

        self._incoming_cb_vars.clear()

        if not sorted_events:
            ctk.CTkLabel(
                self.scroll_incoming,
                text="Nenhum evento encontrado nos canais cadastrados.\\nClique em 'Atualizar Canais Agora' para escanear transmissões futuras.",
                font=ctk.CTkFont(size=11),
                text_color="#666666"
            ).pack(pady=20)
            return

        for ev in sorted_events:"""

    new_incoming_loop = """        sorted_events = sorted(events, key=incoming_sort_key)

        for w in self.scroll_incoming.winfo_children():
            w.destroy()

        self._incoming_cb_vars.clear()

        if not sorted_events:
            ctk.CTkLabel(
                self.scroll_incoming,
                text="Nenhum evento encontrado nos canais cadastrados.\\nClique em 'Atualizar Canais Agora' para escanear transmissões futuras.",
                font=ctk.CTkFont(size=11),
                text_color="#666666"
            ).pack(pady=20)
            return

        # Limitar renderização para manter a UI ultra-leve
        limit = getattr(self, "_incoming_limit", 25)
        visible_events = sorted_events[:limit]

        for ev in visible_events:"""

    if old_incoming_loop in content:
        content = content.replace(old_incoming_loop, new_incoming_loop)
        # Add footer load more for incoming
        footer_incoming = """
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
"""
        # Place footer before def _render_fila_cards
        content = content.replace("    def _render_fila_cards(self) -> None:", footer_incoming + "\n    def _render_fila_cards(self) -> None:")
        print("[+] _render_incoming_list limited with pagination!")

    # 6. Overhaul _render_fila_cards with filtering, smart sorting, and limit
    old_fila_render = """    def _render_fila_cards(self) -> None:
        \"\"\"Renderiza os cards da fila de análise (coluna direita).\"\"\"
        if not hasattr(self, "scroll_fila"):
            return

        for w in self.scroll_fila.winfo_children():
            w.destroy()

        events = self.live_service.list_events()
        selected_events = [e for e in events if e.get("selected")]

        if not selected_events:
            ctk.CTkLabel(
                self.scroll_fila,
                text="Nenhum evento selecionado para análise.\\nMarque as caixas de seleção [✓] na coluna à esquerda para adicionar eventos à fila.",
                font=ctk.CTkFont(size=11),
                text_color="#666666"
            ).pack(pady=40)
            return

        for ev in selected_events:
            vid = ev.get("video_id", "")
            try:
                self._render_single_fila_card(ev)
            except Exception as ex:
                self._log(f"⚠️ Erro ao renderizar card da fila ({vid}): {ex}")
                traceback.print_exc()"""

    new_fila_render = """    def _render_fila_cards(self) -> None:
        \"\"\"Renderiza os cards da fila de análise de forma ultra-leve e paginada.\"\"\"
        if not hasattr(self, "scroll_fila"):
            return

        for w in self.scroll_fila.winfo_children():
            w.destroy()

        events = self.live_service.list_events()
        selected_events = [e for e in events if e.get("selected")]

        if not selected_events:
            ctk.CTkLabel(
                self.scroll_fila,
                text="Nenhum evento selecionado para análise.\\nMarque as caixas de seleção [✓] na coluna à esquerda para adicionar eventos à fila.",
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
                text=f"Nenhum evento corresponde ao filtro '{mode.upper()}'.\\nClique em 'Todas' para ver os {len(selected_events)} eventos na fila.",
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
            ).pack(side="right", padx=4, pady=8)"""

    if old_fila_render in content:
        content = content.replace(old_fila_render, new_fila_render)
        print("[+] _render_fila_cards overhauled with smart filtering, sorting and virtualization!")

    # 7. Update handlers to open PDF immediately and provide clean queue / reports viewer
    old_handlers = """    def _on_generate_case_report_clicked(self, vid: str) -> None:
        \"\"\"Gera e publica no SharePoint o Relatório Técnico de Ocorrência (debate/programa ou caso não narrado).\"\"\"
        self._log(f"📄 Gerando Relatório do Caso para o evento {vid}...")
        def _do_case():
            res = self.live_service.generate_case_report_for_event(vid)
            if res.get("ok"):
                pdf = res.get("pdf_path")
                self.after(0, lambda: messagebox.showinfo(
                    "Relatório de Ocorrência Concluído",
                    f"Relatório Técnico de Ocorrência gerado e publicado no SharePoint com sucesso!\\n\\nArquivo:\\n{os.path.basename(pdf)}"
                ))
                self.after(0, self._render_fila_cards)
            else:
                self.after(0, lambda: messagebox.showerror("Erro ao Gerar", res.get("error") or "Falha ao gerar relatório de ocorrência."))
        threading.Thread(target=_do_case, daemon=True).start()

    def _on_sync_sharepoint_clicked(self, vid: str) -> None:
        \"\"\"Sincroniza manualmente o relatório de um evento com o SharePoint.\"\"\"
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
        \"\"\"Gera o Relatório Executivo Geral de Auditoria consolidando todas as transmissões e publica no SharePoint.\"\"\"
        self._log("📋 Iniciando geração do Relatório Geral de Auditoria de Lives...")
        def _do_audit():
            res = self.live_service.generate_all_cases_audit_report()
            if res.get("ok"):
                pdf = res.get("pdf_path")
                tot = res.get("total_events", 0)
                self.after(0, lambda: messagebox.showinfo(
                    "Auditoria de Lives Concluída",
                    f"Relatório Geral de Auditoria gerado e publicado com sucesso no SharePoint!\\n\\n"
                    f"Total de transmissões auditadas: {tot}\\n"
                    f"Arquivo:\\n{os.path.basename(pdf)}"
                ))
                try:
                    self._open_pdf_or_folder(pdf)
                except Exception:
                    pass
            else:
                self.after(0, lambda: messagebox.showerror("Falha na Auditoria", res.get("error") or "Erro ao consolidar auditoria."))
        threading.Thread(target=_do_audit, daemon=True).start()"""

    new_handlers = """    def _on_generate_case_report_clicked(self, vid: str) -> None:
        \"\"\"Gera, publica no SharePoint e abre imediatamente o Relatório Técnico de Ocorrência.\"\"\"
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
                    f"Relatório Técnico de Ocorrência gerado e aberto na tela!\\nPublicado também no SharePoint.\\n\\nArquivo:\\n{os.path.basename(pdf)}"
                ))
                self.after(0, self._render_fila_cards)
            else:
                self.after(0, lambda: messagebox.showerror("Erro ao Gerar", res.get("error") or "Falha ao gerar relatório de ocorrência."))
        threading.Thread(target=_do_case, daemon=True).start()

    def _on_sync_sharepoint_clicked(self, vid: str) -> None:
        \"\"\"Sincroniza manualmente o relatório de um evento com o SharePoint.\"\"\"
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
        \"\"\"Gera o Relatório Executivo Geral de Auditoria, publica no SharePoint e abre o PDF na tela na hora.\"\"\"
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
                        f"Relatório Geral de Auditoria gerado e aberto com sucesso!\\nPublicado também no SharePoint.\\n\\n"
                        f"Total de transmissões auditadas: {tot}\\n"
                        f"Arquivo: {os.path.basename(pdf)}"
                    ))
                else:
                    self.after(0, lambda: messagebox.showerror("Falha na Auditoria", res.get("error") or "Erro ao consolidar auditoria."))
            finally:
                if hasattr(self, "btn_audit_report"):
                    self.after(0, lambda: self.btn_audit_report.configure(state="normal", text="📋 Relatório Geral de Auditoria"))
        threading.Thread(target=_do_audit, daemon=True).start()

    def _on_clean_queue_clicked(self) -> None:
        \"\"\"Limpa da fila eventos antigos desnecessários mantendo apenas ativas e relatórios prontos.\"\"\"
        removed = self.live_service.clean_queue_keep_active()
        messagebox.showinfo("Fila Limpa", f"{removed} eventos antigos foram removidos da fila.\\nApenas eventos ativos e com relatórios prontos foram mantidos.")
        self._render_fila_cards()
        self._refresh_kpis()

    def _on_open_reports_folder_clicked(self) -> None:
        \"\"\"Abre a pasta reports no Windows Explorer com 1 clique direto.\"\"\"
        import glob
        from gui.main_gui import PROJECT_ROOT
        reports_dir = os.path.join(str(PROJECT_ROOT), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        try:
            os.startfile(reports_dir)
        except Exception as ex:
            self._log(f"Erro ao abrir pasta de relatórios: {ex}")

    def _open_recent_reports_modal(self) -> None:
        \"\"\"Abre modal responsivo listando todos os relatórios gerados recentemente.\"\"\"
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
        self._render_incoming_list()"""

    if old_handlers in content:
        content = content.replace(old_handlers, new_handlers)
        print("[+] Handlers upgraded with immediate PDF launch, reports viewer, and cleanup!")

    path.write_text(content, encoding="utf-8")
    print("[+] canais_live_mixin.py fully patched!")

if __name__ == "__main__":
    patch_gui()
