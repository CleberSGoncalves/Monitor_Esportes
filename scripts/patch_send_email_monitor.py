path = "modules/live_channel_monitor.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_func_start = "    # ---------------------------------------------------------------- email\n    def send_email(self, vid: str, recipients: Optional[List[str]] = None) -> bool:"
idx = content.find(old_func_start)
if idx == -1:
    old_func_start = "    # ---------------------------------------------------------------- email\r\n    def send_email(self, vid: str, recipients: Optional[List[str]] = None) -> bool:"
    idx = content.find(old_func_start)

if idx == -1:
    print("Inicio da funcao send_email nao encontrado!")
else:
    new_func = """    # ---------------------------------------------------------------- email
    def send_email(self, vid: str, recipients: Optional[List[str]] = None, return_details: bool = False) -> Any:
        from modules.email_service import EmailService
        ev = self.get_event(vid)
        if not ev:
            err = "Evento não encontrado na fila."
            return (False, err) if return_details else False

        cfg = self.config_provider() or {}
        recipients = recipients or self.get_setting("emails") or cfg.get("emails")
        if not recipients:
            for p in (
                os.path.join(os.environ.get("APPDATA", ""), "Monitor_Esportes", "config", "saved_emails.json"),
                os.path.join("config", "saved_emails.json")
            ):
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f_em:
                            recipients = json.load(f_em)
                            if recipients:
                                break
                    except Exception:
                        pass
        if not recipients:
            recipients = ["cleber.goncalves@ibope.com", "arthur@mediadna.com.br"]

        sender = cfg.get("sender") or cfg.get("email") or "kimsuportecaptacao@gmail.com"
        password = cfg.get("password") or cfg.get("senha") or "ufvg yhog yrql vmqb"
        smtp_server = cfg.get("smtp_server") or "smtp.gmail.com"
        smtp_port = int(cfg.get("smtp_port") or 587)

        pdf = ev.get("pdf_path") if ev.get("pdf_path") and os.path.exists(ev.get("pdf_path")) else None
        if not pdf:
            err = "O arquivo PDF do relatório deste evento ainda não foi gerado ou não foi encontrado em disco."
            self.log(f"⚠️ [EMAIL] {err}")
            return (False, err) if return_details else False

        attachments = []
        narr_path = ev.get("narration_path")
        large_narr_omitted = False
        if narr_path and os.path.exists(narr_path):
            try:
                sz = os.path.getsize(narr_path)
                # Se a narração tiver menos de 10 MB, anexa normalmente
                if sz <= 10 * 1024 * 1024:
                    attachments.append(narr_path)
                else:
                    large_narr_omitted = True
            except Exception:
                pass

        meta = ev.get("meta") or {}
        jogo = f"{meta.get('team1')} x {meta.get('team2')}" if meta.get("team1") else ev.get("title", "")
        body = (
            f"Relatório Oficial de Auditoria & Narração da live \\"{ev.get('title')}\\"\\n"
            f"Canal: {ev.get('channel_name')}\\nVídeo: {ev.get('url')}\\n"
            f"Partida / Evento: {jogo}\\n\\n"
            f"Segue anexo o Relatório Executivo em PDF com cronologia dos lances, marcos técnicos e inserções comerciais/marcas identificadas durante a transmissão.\\n"
        )
        if large_narr_omitted:
            body += "\\n(Nota: O arquivo completo de narração bruta em texto possui tamanho excessivo (>10MB) e foi preservado localmente no sistema para segurança do envio do relatório oficial).\\n"
        body += "\\n— Monitor de Esportes (Canais Live)"

        try:
            svc = EmailService(smtp_server, smtp_port, sender, password)
            ok = svc.send_report(recipients, f"Relatório de Narração Live — {ev.get('channel_name')} — {jogo}", body, pdf,
                                 extra_attachments=attachments)
            if ok:
                self.update_event(vid, emailed_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                self.log(f"✉️ E-mail enviado com sucesso para: {', '.join(recipients)}")
                return (True, f"E-mail enviado com sucesso para: {', '.join(recipients)}") if return_details else True
            else:
                err = f"Falha no envio via servidor SMTP ({smtp_server}:{smtp_port})."
                return (False, err) if return_details else False
        except Exception as ex:  # noqa: BLE001
            err_msg = f"Erro no envio de e-mail ({type(ex).__name__}): {ex}"
            self.log(f"⚠️ Falha ao enviar e-mail: {err_msg}")
            return (False, err_msg) if return_details else False
"""
    content = content[:idx] + new_func
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("send_email atualizado com sucesso!")
