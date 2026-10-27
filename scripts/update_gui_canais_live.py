# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def update_canais_live_mixin():
    path = Path("gui/canais_live_mixin.py")
    content = path.read_text(encoding="utf-8")

    # 1. Replace kpi_bar layout with 2 clean sub-rows
    old_kpi_pattern = r"# 1\. BARRA SUPERIOR: KPIS & CONTROLES GERAIS.*?(?=# ---------------------------------------------------------------------\s*# 2\. CORPO PRINCIPAL)"
    new_kpi_section = """# 1. BARRA SUPERIOR: KPIS & CONTROLES GERAIS
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
            width=200,
            command=self._on_audit_report_clicked
        )
        self.btn_audit_report.pack(side="left", padx=6, pady=2)

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

        """

    new_content, count = re.subn(old_kpi_pattern, new_kpi_section, content, count=1, flags=re.DOTALL)
    if count == 0:
        print("[!] Failed to replace KPI bar layout!")
    else:
        print("[+] KPI bar layout upgraded to 2 clean rows!")
        content = new_content

    # 2. Upgrade action buttons in _render_single_fila_card
    old_btn_row_pattern = r"# Linha de Ações / Botões\s*btn_row = ctk\.CTkFrame\(card, fg_color=\"transparent\"\).*?(?=\s*# =========================================================================\s*# HANDLERS DE AÇÃO)"
    
    new_btn_row = """# Linha de Ações / Botões
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

"""
    new_content, count = re.subn(old_btn_row_pattern, new_btn_row, content, count=1, flags=re.DOTALL)
    if count == 0:
        print("[!] Failed to replace card buttons pattern!")
    else:
        print("[+] Card action buttons upgraded with Case Report, SharePoint & Reprocess!")
        content = new_content

    # 3. Add handler functions
    new_handlers = """
    def _on_generate_case_report_clicked(self, vid: str) -> None:
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
        threading.Thread(target=_do_audit, daemon=True).start()

    def _on_reprocess_clicked(self, vid: str) -> None:
        \"\"\"Reprocessa a transcrição ou análise do evento.\"\"\"
        ev = self.live_service.get_event(vid)
        if not ev:
            return
        if messagebox.askyesno("Reprocessar Evento", f"Deseja reprocessar a live '{ev.get('title', vid)[:50]}' forçando nova transcrição e análise de IA?"):
            self._log(f"🔄 Disparando reprocessamento completo da live {vid}...")
            self.live_service.update_event(vid, pipeline="transcribing", error="", progress="Reprocessando transcrição...", is_match_narration=None)
            self.live_service.run_transcription_async(vid, force_audio=True)
            self._render_fila_cards()
"""
    if "def _on_generate_case_report_clicked" not in content:
        content += "\n" + new_handlers
        print("[+] Added new handlers (_on_generate_case_report_clicked, _on_sync_sharepoint_clicked, _on_audit_report_clicked, _on_reprocess_clicked)!")

    path.write_text(content, encoding="utf-8")
    print("[+] canais_live_mixin.py updated successfully.")

if __name__ == "__main__":
    update_canais_live_mixin()
