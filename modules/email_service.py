import smtplib
import os
import email.mime.multipart
import email.mime.text
import email.mime.base
import email.encoders
import time
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

MIMEMultipart = email.mime.multipart.MIMEMultipart
MIMEText = email.mime.text.MIMEText
MIMEBase = email.mime.base.MIMEBase
encoders = email.encoders

class EmailService:
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587,
                 sender_email: str = "", sender_password: str = ""):
        self.smtp_server = smtp_server or "smtp.gmail.com"
        self.smtp_port = int(smtp_port or 587)
        self.sender_email = (sender_email or "").strip()
        self.sender_password = (sender_password or "").strip()

    def send_report(self, recipients: List[str], subject: str, body: str,
                    pdf_path: Optional[str] = None,
                    extra_attachments: Optional[List[str]] = None) -> bool:
        """
        Envia e-mail com relatório e anexos, blindado contra SMTPServerDisconnected,
        com retry automático e fallback entre portas 587 (STARTTLS) e 465 (SSL).
        """
        if not recipients:
            logger.warning("[EmailService] Lista de destinatários vazia.")
            return False

        if not self.sender_email or not self.sender_password:
            logger.warning("[EmailService] Credenciais de e-mail não configuradas.")
            return False

        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # Filtrar e anexar arquivos válidos (limite de 15MB total)
        attachments_to_add = []
        if pdf_path and os.path.exists(pdf_path):
            attachments_to_add.append(pdf_path)
        if extra_attachments:
            for att in extra_attachments:
                if att and os.path.exists(att) and att not in attachments_to_add:
                    try:
                        # Ignora arquivos de texto gigantes de horas de narração (> 5MB)
                        if os.path.getsize(att) <= 5 * 1024 * 1024:
                            attachments_to_add.append(att)
                    except Exception:
                        pass

        for file_path in attachments_to_add:
            try:
                filename = os.path.basename(file_path)
                with open(file_path, "rb") as attachment:
                    subtype = "pdf" if filename.lower().endswith(".pdf") else "octet-stream"
                    part = MIMEBase("application", subtype)
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename=\"{filename}\"")
                    part.set_param("name", filename)
                    msg.attach(part)
            except Exception as e_att:
                logger.warning(f"[EmailService] Falha ao anexar '{file_path}': {e_att}")

        text = msg.as_string()

        # Estratégia de Envio Resiliente:
        # 1. Tentar porta 587 STARTTLS com timeout de 25s
        # 2. Se houver SMTPServerDisconnected ou erro de conexão, tentar porta 465 SSL
        # 3. Até 3 tentativas com pausa de 2 segundos
        configs_to_try = [
            (self.smtp_server, 587, False),  # STARTTLS
            (self.smtp_server, 465, True),   # SSL Direto
            ("smtp.gmail.com", 587, False),  # Fallback padrão Gmail STARTTLS
            ("smtp.gmail.com", 465, True),   # Fallback padrão Gmail SSL
        ]

        last_error = None
        for attempt in range(1, 4):
            for server_host, port, use_ssl in configs_to_try:
                try:
                    logger.info(f"[EmailService] Tentativa {attempt}/3 conectando a {server_host}:{port} (SSL={use_ssl})...")
                    if use_ssl:
                        server = smtplib.SMTP_SSL(server_host, port, timeout=25)
                    else:
                        server = smtplib.SMTP(server_host, port, timeout=25)
                        server.starttls()

                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(self.sender_email, recipients, text)
                    try:
                        server.quit()
                    except Exception:
                        pass
                    logger.info(f"[EmailService] ✅ E-mail enviado com sucesso via {server_host}:{port}!")
                    return True
                except (smtplib.SMTPServerDisconnected, TimeoutError, ConnectionResetError, OSError) as e_disc:
                    last_error = e_disc
                    logger.warning(f"[EmailService] Conexão fechada por {server_host}:{port} ({e_disc}). Tentando rota alternativa...")
                    time.sleep(1.5)
                except Exception as e_gen:
                    last_error = e_gen
                    logger.warning(f"[EmailService] Erro no envio via {server_host}:{port}: {e_gen}")
                    time.sleep(1.5)

            time.sleep(2)

        logger.error(f"[EmailService] ❌ Falha definitiva no envio de e-mail após retries: {last_error}")
        raise last_error if last_error else RuntimeError("Falha desconhecida no envio de e-mail.")
