path = "gui/canais_live_mixin.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_block = """    def _on_send_email_clicked(self, vid: str) -> None:
        recipients = self._get_configured_emails()
        if not recipients:
            if messagebox.askyesno("Destinatários Não Cadastrados", "Nenhum destinatário de e-mail foi cadastrado ainda nesta aba.\\nDeseja cadastrar agora?"):
                self._open_email_recipients_modal()
            return

        def _send():
            ok = self.live_service.send_email(vid, recipients=recipients)
            if ok:
                self.after(0, lambda: messagebox.showinfo("E-mail Enviado", f"Relatório PDF e Narração (.txt) enviados com sucesso para:\\n{', '.join(recipients)}"))
            else:
                self.after(0, lambda: messagebox.showwarning("Falha no Envio", "Não foi possível enviar o e-mail. Verifique suas credenciais SMTP na aba Config."))
        threading.Thread(target=_send, daemon=True).start()"""

new_block = """    def _on_send_email_clicked(self, vid: str) -> None:
        recipients = self._get_configured_emails()
        if not recipients:
            if messagebox.askyesno("Destinatários Não Cadastrados", "Nenhum destinatário de e-mail foi cadastrado ainda nesta aba.\\nDeseja cadastrar agora?"):
                self._open_email_recipients_modal()
            return

        ev = self.live_service.get_event(vid)
        if not ev:
            messagebox.showerror("Erro", "Evento não encontrado na fila.")
            return

        pdf_path = ev.get("pdf_path")
        if not pdf_path or not os.path.exists(pdf_path):
            err = ev.get("error")
            if err:
                ans = messagebox.askyesno(
                    "Relatório PDF Não Gerado",
                    f"O relatório PDF deste evento ainda não foi gerado com sucesso devido a um erro durante a análise:\\n\\n{err}\\n\\nDeseja reprocessar a geração do relatório agora?"
                )
                if ans:
                    self._generate_chronology(vid)
                return
            else:
                ans = messagebox.askyesno(
                    "Relatório PDF Pendente",
                    "O relatório PDF desta partida ainda não foi gerado.\\n\\nDeseja gerar o relatório cronológico agora antes de enviar por e-mail?"
                )
                if ans:
                    self._generate_chronology(vid)
                return

        def _send():
            ok, msg = self.live_service.send_email(vid, recipients=recipients, return_details=True)
            if ok:
                self.after(0, lambda: messagebox.showinfo("E-mail Enviado", f"Relatório PDF enviado com sucesso para:\\n{', '.join(recipients)}"))
            else:
                self.after(0, lambda: messagebox.showwarning("Falha no Envio de E-mail", f"Não foi possível enviar o e-mail.\\n\\nDetalhes do erro:\\n{msg}"))
        threading.Thread(target=_send, daemon=True).start()"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Sucesso ao atualizar _on_send_email_clicked!")
else:
    # Tenta com \r\n
    old_block_crlf = old_block.replace("\n", "\r\n")
    new_block_crlf = new_block.replace("\n", "\r\n")
    if old_block_crlf in content:
        content = content.replace(old_block_crlf, new_block_crlf)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Sucesso ao atualizar _on_send_email_clicked (crlf)!")
    else:
        print("Bloco old_block nao encontrado!")
