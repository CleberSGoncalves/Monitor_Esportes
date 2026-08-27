import smtplib
import os
import email.mime.multipart
import email.mime.text
import email.mime.base
import email.encoders

# Atalhos para uso interno (v11.3)
MIMEMultipart = email.mime.multipart.MIMEMultipart
MIMEText = email.mime.text.MIMEText
MIMEBase = email.mime.base.MIMEBase
encoders = email.encoders
from typing import List, Optional

class EmailService:
    def __init__(self, smtp_server: str, smtp_port: int, sender_email: str, sender_password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password

    def send_report(self, recipients: List[str], subject: str, body: str, pdf_path: Optional[str] = None) -> bool:
        if not recipients:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            if pdf_path and os.path.exists(pdf_path):
                filename = os.path.basename(pdf_path)
                if not filename.lower().endswith(".pdf"):
                    filename += ".pdf"
                
                with open(pdf_path, "rb") as attachment:
                    # v10.6.1: Nome do anexo em múltiplos locais para compatibilidade total
                    part = MIMEBase("application", "pdf")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    
                    # Tenta forçar o nome em todos os padrões conhecidos
                    part.add_header("Content-Disposition", "attachment", filename=filename)
                    part.set_param("name", filename) # Padrão antigo mas compatível
                    msg.attach(part)

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            text = msg.as_string()
            server.sendmail(self.sender_email, recipients, text)
            server.quit()
            return True
        except Exception as e:
            print(f"[EmailService] Erro ao enviar e-mail: {e}")
            return False
