import re

def main():
    path = r"gui/nba_events_mixin.py"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    idx = c.find("def _open_nba_global_email_modal")
    if idx == -1:
        print("Not found")
        return

    base = c[:idx].rstrip() + "\n\n"

    methods = '''    def _open_nba_global_email_modal(self) -> None:
        """Abre modal global para gerenciar destinatarios da NBA que refletem em todas as partidas e auditoria autonoma."""
        modal = ctk.CTkToplevel(self)
        modal.title("✉️ Gerenciar Destinatarios Globais da NBA")
        modal.geometry("540x520")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()

        try:
            self.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() // 2) - 270
            y = self.winfo_y() + (self.winfo_height() // 2) - 260
            modal.geometry(f"540x520+{x}+{y}")
        except Exception:
            pass

        header = ctk.CTkFrame(modal, fg_color=("#0F172A", "#1E293B"), corner_radius=0, height=65)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="✉️ Destinatarios Globais de Auditoria NBA",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#F8FAFC"
        ).pack(anchor="w", padx=16, pady=(10, 2))

        ctk.CTkLabel(
            header,
            text="Os e-mails marcados abaixo receberao os relatorios de todas as partidas da NBA",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        ).pack(anchor="w", padx=16)

        body = ctk.CTkFrame(modal, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Adicionar novo e-mail
        add_frame = ctk.CTkFrame(body, fg_color=("#F1F5F9", "#0F172A"), corner_radius=8, border_width=1, border_color=("#CBD5E1", "#334155"))
        add_frame.pack(fill="x", pady=(0, 10), padx=2)

        entry_new = ctk.CTkEntry(
            add_frame,
            placeholder_text="Digite um novo e-mail (ex: analista@empresa.com)...",
            height=32,
            font=ctk.CTkFont(size=11)
        )
        entry_new.pack(side="left", fill="x", expand=True, padx=(10, 8), pady=8)

        scroll_emails = ctk.CTkScrollableFrame(body, fg_color=("#FFFFFF", "#1E293B"), border_width=1, border_color=("#CBD5E1", "#334155"), height=240)
        scroll_emails.pack(fill="both", expand=True, pady=(0, 10))

        email_check_vars = {}

        def _refresh_list():
            for w in scroll_emails.winfo_children():
                w.destroy()
            email_check_vars.clear()

            import json
            emails_list = []
            try:
                with open("config/saved_emails.json", "r", encoding="utf-8") as f:
                    emails_list = json.load(f)
            except Exception:
                emails_list = ["cleber.goncalves@ibope.com", "arthur@mediadna.com.br"]

            for em in emails_list:
                row = ctk.CTkFrame(scroll_emails, fg_color="transparent")
                row.pack(fill="x", pady=3, padx=6)

                var = ctk.BooleanVar(value=True)
                email_check_vars[em] = var

                chk = ctk.CTkCheckBox(row, text=em, variable=var, font=ctk.CTkFont(size=12))
                chk.pack(side="left", padx=4)

                def _make_del(del_em=em):
                    def _do_del():
                        try:
                            with open("config/saved_emails.json", "r", encoding="utf-8") as f_r:
                                cur = json.load(f_r)
                            if del_em in cur:
                                cur.remove(del_em)
                                with open("config/saved_emails.json", "w", encoding="utf-8") as f_w:
                                    json.dump(cur, f_w, indent=2)
                        except Exception:
                            pass
                        _refresh_list()
                    return _do_del

                btn_del = ctk.CTkButton(
                    row, text="🗑️", width=32, height=24,
                    fg_color=("#EF4444", "#DC2626"), hover_color=("#DC2626", "#B91C1C"),
                    command=_make_del(em)
                )
                btn_del.pack(side="right", padx=4)

        def _do_add():
            new_val = entry_new.get().strip()
            if not new_val or "@" not in new_val or "." not in new_val:
                messagebox.showwarning("E-mail Invalido", "Por favor, digite um e-mail valido.")
                return
            try:
                import json
                cur = []
                try:
                    with open("config/saved_emails.json", "r", encoding="utf-8") as f_r:
                        cur = json.load(f_r)
                except Exception:
                    cur = []
                if new_val not in cur:
                    cur.append(new_val)
                    with open("config/saved_emails.json", "w", encoding="utf-8") as f_w:
                        json.dump(cur, f_w, indent=2)
                entry_new.delete(0, "end")
                _refresh_list()
            except Exception as ex:
                messagebox.showerror("Erro", f"Erro ao adicionar e-mail: {ex}")

        btn_add = ctk.CTkButton(
            add_frame, text="➕ Adicionar", width=100, height=32,
            fg_color=("#16A34A", "#15803D"), hover_color=("#15803D", "#166534"),
            command=_do_add
        )
        btn_add.pack(side="right", padx=(0, 10), pady=8)

        _refresh_list()

        btn_bar = ctk.CTkFrame(modal, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(0, 14))

        def _do_save_global():
            selected = [em for em, v in email_check_vars.items() if v.get()]
            if not selected:
                messagebox.showwarning("Destinatarios", "Selecione pelo menos um e-mail para permanecer ativo.")
                return

            try:
                from modules.nba_autonomous_auditor import NBAAutonomousAuditor
                NBAAutonomousAuditor.get_instance().set_recipients(selected)
            except Exception:
                pass

            self.lbl_nba_status.configure(text=f"✉️ Destinatarios NBA atualizados: {len(selected)} e-mails ativos salvos.")
            modal.destroy()
            messagebox.showinfo(
                "Configuracao Salva",
                f"✅ Lista de destinatarios globais da NBA atualizada com sucesso!\\n\\n"
                f"Os {len(selected)} e-mail(s) selecionados receberao automaticamente todos os relatorios da temporada."
            )

        btn_cancel = ctk.CTkButton(
            btn_bar, text="Cancelar", width=100, height=32,
            fg_color=("#CBD5E1", "#334155"), text_color=("#0F172A", "#F8FAFC"),
            command=modal.destroy
        )
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_save = ctk.CTkButton(
            btn_bar, text="💾 Salvar Destinatarios", width=170, height=32,
            fg_color=("#16A34A", "#15803D"), hover_color=("#15803D", "#166534"),
            command=_do_save_global
        )
        btn_save.pack(side="right")

    def _nba_audit_entire_season(self) -> None:
        """Audita e sincroniza no SharePoint todas as partidas da temporada da NBA desde o inicio oficial (20/10/2026)."""
        from datetime import datetime, timedelta

        ans = messagebox.askyesno(
            "Sincronizar Temporada NBA",
            "Esta operacao ira varrer todas as partidas da temporada desde o inicio em 20/10/2026 ate hoje,\\n"
            "baixar os Game Books oficiais e sincronizar todos os relatorios no SharePoint.\\n\\n"
            "Deseja iniciar a sincronizacao completa da temporada agora?"
        )
        if not ans:
            return

        def _worker():
            import time
            season_start = datetime(2026, 10, 20)
            now_dt = datetime.now()
            days_span = max(1, (now_dt - season_start).days + 1)
            dates = [(season_start + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(days_span + 2)]

            self.lbl_nba_status.configure(text=f"Varrendo agenda completa da NBA desde 20/10 ({len(dates)} datas)...")
            all_games = []
            for d_str in dates:
                games = self.nba_service.fetch_games_for_date(d_str)
                all_games.extend(games)

            total = len(all_games)
            finished_games = [g for g in all_games if g.get("is_finished")]
            self.lbl_nba_status.configure(text=f"Encontradas {total} partidas ({len(finished_games)} finalizadas). Iniciando sincronizacao no SharePoint...")

            synced_count = 0
            for idx, g in enumerate(all_games, 1):
                m_name = g.get("match_display", "")
                d_disp = g.get("date_display", "")
                self.lbl_nba_status.configure(text=f"[{idx}/{total}] Processando {m_name} ({d_disp})...")

                gb_path = self.nba_service.download_gamebook(g) if g.get("is_finished") else None
                parsed = self.nba_service.parse_gamebook(gb_path) if gb_path else {}
                pdf = self.nba_reporter.generate_report(g, parsed)
                ok = SharePointNBAReporter.sync_nba_report(pdf, g)
                if ok:
                    synced_count += 1
                time.sleep(1.2)

            self.lbl_nba_status.configure(text=f"🎉 Temporada NBA sincronizada com sucesso: {synced_count}/{total} partidas no SharePoint!")
            self.after(0, lambda: messagebox.showinfo(
                "Temporada NBA Sincronizada",
                f"🎉 SUCESSO!\\n\\n"
                f"Todas as partidas da temporada da NBA desde 20/10 foram processadas:\\n\\n"
                f"• Total de jogos verificados: {total}\\n"
                f"• Jogos sincronizados no SharePoint: {synced_count}\\n"
                f"• Biblioteca: 'Relatorios_de_Jogos_NBA'"
            ))

        threading.Thread(target=_worker, daemon=True).start()
'''

    with open(path, "w", encoding="utf-8") as f:
        f.write(base + methods)
    print("Cleanly indented methods in nba_events_mixin.py")

if __name__ == "__main__":
    main()
