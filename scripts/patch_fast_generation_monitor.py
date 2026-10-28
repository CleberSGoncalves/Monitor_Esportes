path = "modules/live_channel_monitor.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Substitui o trecho síncrono de PDF + SharePoint + Email em _generate_locked
old_code = """        plog("📄 Gerando PDF oficial do relatório cronológico...")
        prefs = {"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}
        pdf = self.reporter.write_expert_report([result], prefs=prefs, sync_sharepoint=True, name_prefix="narracao")
        sp_synced = bool(result.get("sharepoint_synced", True))
        self.update_event(vid, pipeline="done", pdf_path=pdf, error="", progress=f"Relatório PDF gerado ({os.path.basename(pdf)})",
                          generated_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                          sharepoint_synced=sp_synced,
                          sharepoint_synced_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S") if sp_synced else None)
        plog(f"✅ Relatório pronto e sincronizado no SharePoint: {os.path.basename(pdf)}")
        if auto or self.get_setting("auto_report", True) or self.get_setting("auto_email", True):
            self.send_email(vid)
        return {"ok": True, "pdf_path": pdf}"""

new_code = """        plog("📄 Renderizando PDF oficial do relatório cronológico...")
        prefs = {"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}
        # Gera o PDF localmente em 1-2 segundos sem travar na rede
        pdf = self.reporter.write_expert_report([result], prefs=prefs, sync_sharepoint=False, name_prefix="narracao")
        
        # ATUALIZA IMEDIATAMENTE PARA PRONTO: o usuário já pode ver e abrir o PDF na hora!
        self.update_event(vid, pipeline="done", pdf_path=pdf, error="",
                          progress=f"Relatório PDF concluído ({os.path.basename(pdf)})",
                          generated_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        plog(f"✅ Relatório PDF pronto: {os.path.basename(pdf)}")

        # Sincronização com SharePoint e disparo de E-mail desacoplados em segundo plano
        def _bg_sync():
            try:
                plog("☁️ Sincronizando relatório com SharePoint...")
                self.sync_event_to_sharepoint(vid)
            except Exception as ex_sp:
                self.log(f"⚠️ Aviso SharePoint: {ex_sp}")

            if auto or self.get_setting("auto_report", True) or self.get_setting("auto_email", True):
                try:
                    plog("✉️ Enviando relatório por e-mail...")
                    self.send_email(vid)
                except Exception as ex_em:
                    self.log(f"⚠️ Aviso E-mail: {ex_em}")

        threading.Thread(target=_bg_sync, daemon=True).start()
        return {"ok": True, "pdf_path": pdf}"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("live_channel_monitor.py desacoplado com sucesso!")
else:
    # tenta com CRLF
    old_crlf = old_code.replace("\n", "\r\n")
    new_crlf = new_code.replace("\n", "\r\n")
    if old_crlf in content:
        content = content.replace(old_crlf, new_crlf)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("live_channel_monitor.py desacoplado com sucesso (crlf)!")
    else:
        print("Bloco old_code nao encontrado em live_channel_monitor.py!")
