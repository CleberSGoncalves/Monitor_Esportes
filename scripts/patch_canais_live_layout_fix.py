import os

path = os.path.join("gui", "canais_live_mixin.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Ajuste da barra superior (kpi_row1) para NUNCA cortar o label do SharePoint
target_kpi_buttons = '''        # Botão: Pasta de Relatórios
        self.btn_open_reports_folder = ctk.CTkButton(
            kpi_row1,
            text="📁 Pasta de Relatórios",
            font=ctk.CTkFont(size=11),
            fg_color="#333333",
            hover_color="#444444",
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
        self.btn_clean_non_matches.pack(side="left", padx=5, pady=2)

        # Status SharePoint
        self.lbl_live_status_hint = ctk.CTkLabel(
            kpi_row1,
            text="☁️ SharePoint Conectado",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#00FF7F"
        )
        self.lbl_live_status_hint.pack(side="right", padx=12, pady=2)'''

replacement_kpi_buttons = '''        # Botão: Pasta de Relatórios
        self.btn_open_reports_folder = ctk.CTkButton(
            kpi_row1,
            text="📁 Pasta Relatórios",
            font=ctk.CTkFont(size=11),
            fg_color="#333333",
            hover_color="#444444",
            height=32,
            width=125,
            command=self._on_open_reports_folder_clicked
        )
        self.btn_open_reports_folder.pack(side="left", padx=3, pady=2)

        # Botão: Ver Relatórios Gerados
        self.btn_view_recent_reports = ctk.CTkButton(
            kpi_row1,
            text="📑 Relatórios (PDF)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1b5e20",
            hover_color="#2e7d32",
            height=32,
            width=125,
            command=self._open_recent_reports_modal
        )
        self.btn_view_recent_reports.pack(side="left", padx=3, pady=2)
        # Botão: Limpar Não-Jogos da Fila (Anti-Poluição)
        self.btn_clean_non_matches = ctk.CTkButton(
            kpi_row1,
            text="🧹 Limpar Não-Jogos",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#b71c1c",
            hover_color="#d32f2f",
            height=32,
            width=135,
            command=self._on_clean_non_matches_clicked
        )
        self.btn_clean_non_matches.pack(side="left", padx=3, pady=2)

        # Status SharePoint (Layout Protegido contra Cortes)
        self.lbl_live_status_hint = ctk.CTkLabel(
            kpi_row1,
            text="☁️ SharePoint OK",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#00FF7F"
        )
        self.lbl_live_status_hint.pack(side="right", padx=8, pady=2)'''

if target_kpi_buttons in content:
    content = content.replace(target_kpi_buttons, replacement_kpi_buttons, 1)

# 2. Otimizar as larguras dos botões dentro do card para NUNCA cortar no final
old_widths = '''                btn_width = 220
            elif pipe == "generating":
                # ETAPA ATIVA: Mostra exatamente o que a IA está fazendo em laranja pulsante
                chrono_text = stage_title
                btn_color = "#e65100"
                btn_hover = "#ef6c00"
                btn_cmd = lambda: None
                btn_state = "disabled"
                btn_width = 220
            elif pipe in ("analyzing", "transcribed") and has_narr:
                chrono_text = "🔍 Analisando Transcrição..."
                btn_color = "#5c6bc0"
                btn_hover = "#7986cb"
                btn_cmd = lambda: None
                btn_state = "disabled"
                btn_width = 200
            elif pipe == "transcribing":
                chrono_text = "🎙️ Extraindo Áudio..."
                btn_color = "#0277bd"
                btn_hover = "#0288d1"
                btn_cmd = lambda: None
                btn_state = "disabled"
                btn_width = 200
            else:
                chrono_text = "📊 Gerar Relatório Cronológico"
                btn_color = "#008080"
                btn_hover = "#005a5a"
                btn_cmd = make_chrono()
                btn_state = "normal" if has_narr else "disabled"
                btn_width = 200'''

new_widths = '''                btn_width = 175
            elif pipe == "generating":
                # ETAPA ATIVA: Mostra exatamente o que a IA está fazendo em laranja pulsante
                chrono_text = stage_title
                btn_color = "#e65100"
                btn_hover = "#ef6c00"
                btn_cmd = lambda: None
                btn_state = "disabled"
                btn_width = 175
            elif pipe in ("analyzing", "transcribed") and has_narr:
                chrono_text = "🔍 Analisando..."
                btn_color = "#5c6bc0"
                btn_hover = "#7986cb"
                btn_cmd = lambda: None
                btn_state = "disabled"
                btn_width = 140
            elif pipe == "transcribing":
                chrono_text = "🎙️ Áudio..."
                btn_color = "#0277bd"
                btn_hover = "#0288d1"
                btn_cmd = lambda: None
                btn_state = "disabled"
                btn_width = 130
            else:
                chrono_text = "📊 Gerar Relatório"
                btn_color = "#008080"
                btn_hover = "#005a5a"
                btn_cmd = make_chrono()
                btn_state = "normal" if has_narr else "disabled"
                btn_width = 145'''

if old_widths in content:
    content = content.replace(old_widths, new_widths, 1)

# Ajuste nos botões secundários do card:
content = content.replace('text="📝 Narração (.txt)",\n            font=ctk.CTkFont(size=11),\n            fg_color="#2b5b84" if has_narr else "#222222",\n            hover_color="#1d3e5a" if has_narr else "#222222",\n            state="normal" if has_narr else "disabled",\n            height=28,\n            width=115,',
                          'text="📝 Narração",\n            font=ctk.CTkFont(size=11),\n            fg_color="#2b5b84" if has_narr else "#222222",\n            hover_color="#1d3e5a" if has_narr else "#222222",\n            state="normal" if has_narr else "disabled",\n            height=28,\n            width=90,')

content = content.replace('text="📑 Relatório PDF",\n            font=ctk.CTkFont(size=11, weight="bold"),\n            fg_color="#2e7d32" if has_pdf else "#222222",\n            hover_color="#1b5e20" if has_pdf else "#222222",\n            state="normal" if has_pdf else "disabled",\n            height=28,\n            width=115,',
                          'text="📑 PDF",\n            font=ctk.CTkFont(size=11, weight="bold"),\n            fg_color="#2e7d32" if has_pdf else "#222222",\n            hover_color="#1b5e20" if has_pdf else "#222222",\n            state="normal" if has_pdf else "disabled",\n            height=28,\n            width=80,')

content = content.replace('width=115,\n            command=make_sync_sp()',
                          'width=95,\n            command=make_sync_sp()')

# Remover a duplicação do botão remover que cortava na extrema direita
old_remove_dup = '''        # 7. Botão Remover da Fila no Rodapé do Card
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
        ).pack(side="right", padx=(4, 0))'''

new_remove_dup = '''        # O botão '✕ Remover da Fila' já existe de forma destacada e perfeita no topo do card (hdr)'''

if old_remove_dup in content:
    content = content.replace(old_remove_dup, new_remove_dup, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("canais_live_mixin.py atualizado com layout responsivo anti-cortes!")
