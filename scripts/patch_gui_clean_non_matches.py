path = "gui/canais_live_mixin.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add auto-cleaning in __init__
old_init_start = "        self._auto_email_live_var.set(self.live_service.get_setting(\"auto_email\", True))\n        self.live_service.start()"
new_init_start = """        self._auto_email_live_var.set(self.live_service.get_setting("auto_email", True))
        self.live_service.start()
        try:
            self.live_service.clean_non_matches_from_queue()
        except Exception:
            pass"""

# 2. Add button in kpi_row1
old_kpi_btn = """        # Botão: Ver Relatórios Gerados
        self.btn_view_recent_reports = ctk.CTkButton(
            kpi_row1,
            text="📑 Ver Relatórios (PDF)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1b5e20",
            hover_color="#2e7d32",
            height=34,
            width=165,
            command=self._on_view_recent_reports_clicked
        )
        self.btn_view_recent_reports.pack(side="left", padx=5, pady=2)"""

new_kpi_btn = """        # Botão: Ver Relatórios Gerados
        self.btn_view_recent_reports = ctk.CTkButton(
            kpi_row1,
            text="📑 Ver Relatórios (PDF)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1b5e20",
            hover_color="#2e7d32",
            height=34,
            width=165,
            command=self._on_view_recent_reports_clicked
        )
        self.btn_view_recent_reports.pack(side="left", padx=5, pady=2)

        # Botão: Limpar Não-Jogos da Fila (Anti-Poluição)
        self.btn_clean_non_matches = ctk.CTkButton(
            kpi_row1,
            text="🧹 Limpar Não-Jogos",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#b71c1c",
            hover_color="#d32f2f",
            height=34,
            width=150,
            command=self._on_clean_non_matches_clicked
        )
        self.btn_clean_non_matches.pack(side="left", padx=5, pady=2)"""

# 3. Update KPI calculation
old_kpi_calc = """        channels = self.live_service.list_channels()
        events = self.live_service.list_events()
        selected_events = [e for e in events if e.get("selected")]"""

new_kpi_calc = """        channels = self.live_service.list_channels()
        events = self.live_service.list_events()
        selected_events = [
            e for e in events
            if e.get("selected")
            and e.get("pipeline") != "not_match"
            and e.get("is_match_narration") is not False
        ]"""

# 4. Update _render_fila_cards filtering
old_fila_filter = """        events = self.live_service.list_events()
        selected_events = [e for e in events if e.get("selected")]"""

new_fila_filter = """        events = self.live_service.list_events()
        selected_events = [
            e for e in events
            if e.get("selected")
            and e.get("pipeline") != "not_match"
            and e.get("is_match_narration") is not False
        ]"""

# 5. Add callback method _on_clean_non_matches_clicked
callback_code = """
    def _on_clean_non_matches_clicked(self) -> None:
        \"\"\"Executa a limpeza cirúrgica de eventos que não são jogos da fila.\"\"\"
        rem = self.live_service.clean_non_matches_from_queue()
        messagebox.showinfo(
            "Limpeza Concluída",
            f"Foram eliminados {rem} eventos que não eram partidas de futebol da fila.\\n\\nA fila agora exibe exclusivamente partidas reais!"
        )
        self._refresh_canais_tab_ui()
"""

changed = False

if old_init_start in content:
    content = content.replace(old_init_start, new_init_start)
    changed = True
    print("[+] Init clean added!")
else:
    old_init_crlf = old_init_start.replace("\n", "\r\n")
    new_init_crlf = new_init_start.replace("\n", "\r\n")
    if old_init_crlf in content:
        content = content.replace(old_init_crlf, new_init_crlf)
        changed = True
        print("[+] Init clean added (crlf)!")

if old_kpi_btn in content:
    content = content.replace(old_kpi_btn, new_kpi_btn)
    changed = True
    print("[+] Clean button added to kpi_row1!")
else:
    old_kpi_crlf = old_kpi_btn.replace("\n", "\r\n")
    new_kpi_crlf = new_kpi_btn.replace("\n", "\r\n")
    if old_kpi_crlf in content:
        content = content.replace(old_kpi_crlf, new_kpi_crlf)
        changed = True
        print("[+] Clean button added to kpi_row1 (crlf)!")

if old_kpi_calc in content:
    content = content.replace(old_kpi_calc, new_kpi_calc)
    changed = True
    print("[+] KPI calc patched!")
else:
    old_kpi_calc_crlf = old_kpi_calc.replace("\n", "\r\n")
    new_kpi_calc_crlf = new_kpi_calc.replace("\n", "\r\n")
    if old_kpi_calc_crlf in content:
        content = content.replace(old_kpi_calc_crlf, new_kpi_calc_crlf)
        changed = True
        print("[+] KPI calc patched (crlf)!")

if old_fila_filter in content:
    content = content.replace(old_fila_filter, new_fila_filter)
    changed = True
    print("[+] Fila filter patched!")
else:
    old_fila_crlf = old_fila_filter.replace("\n", "\r\n")
    new_fila_crlf = new_fila_filter.replace("\n", "\r\n")
    if old_fila_crlf in content:
        content = content.replace(old_fila_crlf, new_fila_crlf)
        changed = True
        print("[+] Fila filter patched (crlf)!")

if "def _on_clean_non_matches_clicked" not in content:
    content += callback_code
    changed = True
    print("[+] _on_clean_non_matches_clicked added!")

if changed:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("canais_live_mixin.py atualizado com sucesso!")
else:
    print("Nenhuma alteracao aplicada!")
