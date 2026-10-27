# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def patch_gui_posterior():
    path = Path("gui/canais_live_mixin.py")
    content = path.read_text(encoding="utf-8")

    # 1. In _render_single_fila_card, add the "Relatório Posterior (Sob Demanda)" button
    old_btn_section = """            cat_label = t_analysis.get("event_category") or "Ocorrência"
            ctk.CTkButton(
                btn_row,
                text=f"📄 Relatório do Caso ({cat_label[:14]})",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#455a64",
                hover_color="#546e7a",
                height=28,
                width=190,
                command=make_case_rep()
            ).pack(side="left", padx=(0, 4))"""

    new_btn_section = """            cat_label = t_analysis.get("event_category") or "Ocorrência"
            ctk.CTkButton(
                btn_row,
                text=f"📄 Relatório do Caso ({cat_label[:14]})",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#455a64",
                hover_color="#546e7a",
                height=28,
                width=175,
                command=make_case_rep()
            ).pack(side="left", padx=(0, 3))

            # Botão explícito para FORÇAR GERAÇÃO DE RELATÓRIO DE JOGO POSTERIOR
            def make_posterior_gen(v_id=vid):
                return lambda: self._open_posterior_match_modal(v_id)

            ctk.CTkButton(
                btn_row,
                text="⚽ Relatório Posterior (Jogo)",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#00695c",
                hover_color="#00897b",
                height=28,
                width=180,
                command=make_posterior_gen()
            ).pack(side="left", padx=3)"""

    if old_btn_section in content:
        content = content.replace(old_btn_section, new_btn_section)
        print("[+] Added posterior match report button to card action row!")

    # 2. Add button in the left column manual input row
    old_add_vid_btn = """        self.btn_add_video = ctk.CTkButton(
            add_vid_row,
            text="➕ Incluir",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#37474f",
            hover_color="#455a64",
            width=80,
            height=28,
            command=self._on_add_video_clicked
        )
        self.btn_add_video.pack(side="left")"""

    new_add_vid_btn = """        self.btn_add_video = ctk.CTkButton(
            add_vid_row,
            text="➕ Incluir",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#37474f",
            hover_color="#455a64",
            width=70,
            height=28,
            command=self._on_add_video_clicked
        )
        self.btn_add_video.pack(side="left", padx=(0, 4))

        self.btn_add_posterior_video = ctk.CTkButton(
            add_vid_row,
            text="⚽ Incluir Jogo Passado",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#00695c",
            hover_color="#00897b",
            width=150,
            height=28,
            command=self._on_add_posterior_video_clicked
        )
        self.btn_add_posterior_video.pack(side="left")"""

    if old_add_vid_btn in content:
        content = content.replace(old_add_vid_btn, new_add_vid_btn)
        print("[+] Added incluir jogo passado button to left column!")

    # 3. Add modal implementation and handlers
    modal_code = """
    def _open_posterior_match_modal(self, vid: str) -> None:
        \"\"\"Abre modal elegante para confirmar dados e gerar relatório cronológico de jogo já encerrado (posterior ao evento).\"\"\"
        ev = self.live_service.get_event(vid)
        if not ev:
            messagebox.showerror("Erro", "Evento não encontrado.")
            return

        meta = self.live_service.default_meta(ev)
        title = ev.get("title", "")
        chan = ev.get("channel_name", "YouTube")

        modal = ctk.CTkToplevel(self)
        modal.title("⚽ Gerar Relatório de Jogo Posterior (Sob Demanda)")
        modal.geometry("560x520")
        modal.transient(self)
        modal.grab_set()

        # Cabeçalho
        ctk.CTkLabel(
            modal,
            text="⚽ Gerar Relatório de Jogo Posterior (Sob Demanda)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#00FF7F"
        ).pack(padx=16, pady=(16, 4), anchor="w")

        ctk.CTkLabel(
            modal,
            text=f"Canal: {chan}\\nVídeo: {title[:75]}",
            font=ctk.CTkFont(size=11),
            text_color="#aaaaaa",
            justify="left",
            wraplength=520
        ).pack(padx=16, pady=(0, 10), anchor="w")

        form = ctk.CTkFrame(modal, fg_color="#181818", corner_radius=8)
        form.pack(fill="x", padx=16, pady=4)

        # Time 1
        ctk.CTkLabel(form, text="Time Mandante:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(8, 2))
        ent_t1 = ctk.CTkEntry(form, height=30)
        ent_t1.pack(fill="x", padx=12, pady=(0, 6))
        ent_t1.insert(0, meta.get("team1") or "")

        # Time 2
        ctk.CTkLabel(form, text="Time Visitante:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(4, 2))
        ent_t2 = ctk.CTkEntry(form, height=30)
        ent_t2.pack(fill="x", padx=12, pady=(0, 6))
        ent_t2.insert(0, meta.get("team2") or "")

        # Competição
        ctk.CTkLabel(form, text="Competição:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(4, 2))
        ent_comp = ctk.CTkEntry(form, height=30)
        ent_comp.pack(fill="x", padx=12, pady=(0, 6))
        ent_comp.insert(0, meta.get("competition") or "Brasileirão Série A")

        # Data
        ctk.CTkLabel(form, text="Data da Partida (DD/MM/AAAA):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(4, 2))
        ent_date = ctk.CTkEntry(form, height=30)
        ent_date.pack(fill="x", padx=12, pady=(0, 10))
        ent_date.insert(0, meta.get("date") or datetime.now().strftime("%d/%m/%Y"))

        status_lbl = ctk.CTkLabel(modal, text="", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00CED1")
        status_lbl.pack(pady=4)

        btn_row = ctk.CTkFrame(modal, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(8, 16))

        def _do_generate():
            t1 = ent_t1.get().strip()
            t2 = ent_t2.get().strip()
            comp = ent_comp.get().strip()
            dt = ent_date.get().strip()

            if not t1 or not t2:
                messagebox.showwarning("Aviso", "Preencha o nome de ambos os times para gerar o relatório do jogo.")
                return

            btn_gen.configure(state="disabled", text="⏳ Processando Áudio & Cronologia...")
            status_lbl.configure(text="Extraindo narração do áudio e gerando relatório no Gemini...")

            final_meta = {
                "team1": t1,
                "team2": t2,
                "competition": comp or "Brasileirão Série A",
                "date": dt or datetime.now().strftime("%d/%m/%Y")
            }

            def _done(res):
                if res.get("ok"):
                    pdf = res.get("pdf_path")
                    if pdf and os.path.exists(pdf):
                        try:
                            os.startfile(pdf)
                        except Exception:
                            pass
                    self.after(0, lambda: messagebox.showinfo(
                        "Relatório Posterior Concluído",
                        f"Relatório de partida gerado com sucesso!\\nPublicado no SharePoint e enviado por e-mail.\\n\\nArquivo:\\n{os.path.basename(pdf)}"
                    ))
                    self.after(0, modal.destroy)
                    self.after(0, self._render_fila_cards)
                else:
                    err_msg = res.get("error") or "Erro desconhecido na geração."
                    self.after(0, lambda: messagebox.showerror("Erro ao Gerar", f"Não foi possível gerar o relatório:\\n{err_msg}"))
                    self.after(0, lambda: btn_gen.configure(state="normal", text="🚀 Iniciar Geração de Jogo Agora"))
                    self.after(0, lambda: status_lbl.configure(text=f"Erro: {err_msg}"))

            self.live_service.generate_posterior_match_report_async(
                vid,
                meta=final_meta,
                progress_cb=lambda m: self.after(0, lambda: status_lbl.configure(text=m)),
                done_cb=_done
            )

        btn_gen = ctk.CTkButton(
            btn_row,
            text="🚀 Iniciar Geração de Jogo Agora",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#008080",
            hover_color="#005a5a",
            height=34,
            command=_do_generate
        )
        btn_gen.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_row,
            text="Cancelar",
            font=ctk.CTkFont(size=11),
            fg_color="#333333",
            hover_color="#444444",
            height=34,
            width=90,
            command=modal.destroy
        ).pack(side="right")

    def _on_add_posterior_video_clicked(self) -> None:
        \"\"\"Permite colar a URL de uma live/VOD passada e abre imediatamente o gerador de relatório posterior.\"\"\"
        url = self.entry_add_video.get().strip()
        if not url:
            messagebox.showwarning("Aviso", "Digite ou cole a URL da Live/Jogo do YouTube.")
            return

        self.btn_add_posterior_video.configure(state="disabled", text="⏳ Buscando...")

        def _do_add_post():
            try:
                ev = self.live_service.add_video_manually(url)
                vid = ev.get("video_id")
                self.after(0, lambda: self.entry_add_video.delete(0, "end"))
                self.after(0, lambda: self._open_posterior_match_modal(vid))
            except Exception as ex:
                self.after(0, lambda: messagebox.showerror("Erro ao Incluir Vídeo", str(ex)))
            finally:
                self.after(0, lambda: self.btn_add_posterior_video.configure(state="normal", text="⚽ Incluir Jogo Passado"))

        threading.Thread(target=_do_add_post, daemon=True).start()
"""

    if "def _open_posterior_match_modal" not in content:
        content += "\n" + modal_code
        print("[+] Added _open_posterior_match_modal and _on_add_posterior_video_clicked!")

    path.write_text(content, encoding="utf-8")
    print("[+] canais_live_mixin.py successfully patched with posterior match generation!")

if __name__ == "__main__":
    patch_gui_posterior()
