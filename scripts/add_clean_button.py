path = "gui/canais_live_mixin.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = "self.btn_view_recent_reports.pack(side=\"left\", padx=5, pady=2)"
addition = """
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

if target in content and "self.btn_clean_non_matches" not in content:
    content = content.replace(target, target + addition, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Botao Limpar Nao-Jogos adicionado com sucesso!")
else:
    print("Alvo nao encontrado ou botao ja presente!")
