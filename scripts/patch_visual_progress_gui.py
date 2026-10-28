path = "gui/canais_live_mixin.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Substitui o bloco da linha de botões e adiciona a barra de progresso visual de etapas
old_block = """        # Linha de Ações / Botões
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
            ).pack(side="left", padx=(0, 4))"""

new_block = """        has_narr = bool(ev.get("narration_path") and os.path.exists(ev.get("narration_path")))
        has_pdf = bool(ev.get("pdf_path") and os.path.exists(ev.get("pdf_path")))
        sp_synced = bool(ev.get("sharepoint_synced"))
        prog_str = (ev.get("progress") or "").lower()

        # Determina etapa e porcentagem para feedback visual em tempo real
        stage_percent = 0.25
        stage_title = "⏳ Iniciando..."
        if "transcrevendo" in prog_str or pipe == "transcribing":
            stage_percent = 0.30
            stage_title = "🎙️ [1/4] Extraindo Transcrição..."
        elif "gemini" in prog_str or "analisando" in prog_str or pipe == "analyzing":
            stage_percent = 0.60
            stage_title = "🧠 [2/4] Gemini Analisando Lances..."
        elif "pdf" in prog_str or "renderizando" in prog_str:
            stage_percent = 0.85
            stage_title = "📄 [3/4] Renderizando PDF..."
        elif "sharepoint" in prog_str or "email" in prog_str or "e-mail" in prog_str:
            stage_percent = 0.95
            stage_title = "☁️ [4/4] Sincronizando Nuvem & E-mail..."

        # Barra de Progresso Visual de Etapas durante processamento
        if pipe in ("generating", "transcribing", "analyzing") or ("gerando" in prog_str and not has_pdf):
            prog_bar_box = ctk.CTkFrame(card, fg_color="transparent")
            prog_bar_box.pack(fill="x", padx=10, pady=(2, 6))

            p_bar = ctk.CTkProgressBar(prog_bar_box, height=8, corner_radius=4)
            p_bar.pack(fill="x", expand=True, side="left", padx=(0, 8))
            p_bar.set(stage_percent)
            p_bar.configure(progress_color="#FF8C00" if stage_percent < 0.8 else "#00FF7F")

            ctk.CTkLabel(
                prog_bar_box,
                text=f"{int(stage_percent * 100)}%",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#FF8C00" if stage_percent < 0.8 else "#00FF7F"
            ).pack(side="right")

        # Linha de Ações / Botões
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(4, 10))

        # 1. BOTÃO DE RELATÓRIO DINÂMICO COM FEEDBACK VISUAL POR ETAPA
        if is_match is True:
            def make_open_live_pdf(v_id=vid):
                return lambda: self._open_live_pdf(v_id)

            def make_chrono(v_id=vid):
                return lambda: self._on_generate_chronology_direct(v_id)

            if has_pdf:
                # RELATÓRIO PRONTO: Botão verde para abrir o PDF imediatamente em 1 clique
                chrono_text = "✅ Abrir Relatório PDF (Pronto)"
                btn_color = "#2e7d32"
                btn_hover = "#388e3c"
                btn_cmd = make_open_live_pdf()
                btn_state = "normal"
                btn_width = 220
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
                btn_width = 200

            ctk.CTkButton(
                btn_row,
                text=chrono_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=btn_color if btn_state == "normal" or pipe in ("generating", "transcribing", "analyzing") else "#222222",
                hover_color=btn_hover if btn_state == "normal" else "#222222",
                state=btn_state,
                height=28,
                width=btn_width,
                command=btn_cmd
            ).pack(side="left", padx=(0, 4))"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("gui/canais_live_mixin.py atualizado com feedback visual por etapa com sucesso!")
else:
    old_crlf = old_block.replace("\n", "\r\n")
    new_crlf = new_block.replace("\n", "\r\n")
    if old_crlf in content:
        content = content.replace(old_crlf, new_crlf)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("gui/canais_live_mixin.py atualizado com feedback visual por etapa (crlf)!")
    else:
        print("Bloco old_block nao encontrado em canais_live_mixin.py!")
