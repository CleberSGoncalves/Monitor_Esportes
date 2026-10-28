import os
import sys
from pathlib import Path

# Configurar stdout UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
from modules.email_service import EmailService

with open("config/saved_emails.json", "r", encoding="utf-8") as f:
    recipients = json.load(f)

with open("config/google_ai.json", "r", encoding="utf-8") as f:
    ai_cfg = json.load(f)

sender = ai_cfg.get("email", "kimsuportecaptacao@gmail.com")
password = ai_cfg.get("senha", "")

reports_dir = os.path.join(PROJECT_ROOT, "reports")

# Selecionar rigorosamente os 4 arquivos do Brasileirão Série A das Rodadas 31 e 32
exact_files = [
    "expert_cazétv_brasileirão_série_a_botafogo_x_chapecoense_17102026_20261027_102230.pdf",
    "expert_amazon_prime_brasileirão_série_a_athletico-pr_x_palmeiras_18102026_20261027_102234.pdf",
    "expert_cazétv_brasileirão_série_a_cruzeiro_x_fortaleza_24102026_20261027_102239.pdf",
    "expert_amazon_prime_brasileirão_série_a_grêmio_x_internacional_25102026_20261027_102243.pdf"
]

attachments = [os.path.join(reports_dir, fn) for fn in exact_files if os.path.exists(os.path.join(reports_dir, fn))]

subject = "⚽ Relatórios Oficiais do Brasileirão Série A — Rodadas 31 e 32 (CazéTV e Amazon Prime)"
body = (
    "Prezado Arthur e equipe,\n\n"
    "Conforme alinhamento e regras de auditoria do projeto, seguem em anexo os relatórios oficiais completos de auditoria e cronologia técnica das últimas duas rodadas do Brasileirão Série A gerados pelo sistema padrão (súmulas oficiais CBF e marcos técnicos):\n\n"
    "📋 JOGOS DAS ÚLTIMAS DUAS RODADAS:\n"
    "1. Botafogo 2 x 0 Chapecoense (17/10/2026 - CazéTV)\n"
    "2. Athletico-PR 0 x 2 Palmeiras (18/10/2026 - Amazon Prime)\n"
    "3. Cruzeiro 1 x 1 Fortaleza (24/10/2026 - CazéTV)\n"
    "4. Grêmio 1 x 1 Internacional (25/10/2026 - Amazon Prime)\n\n"
    "ℹ️ ESCLARECIMENTO SOBRE AS PLATAFORMAS NO SHAREPOINT:\n"
    "Os relatórios de testes experimentais realizados na nova aba de canais web (ex: rádio Gaúcha e Bagé TV no YouTube) foram corrigidos na biblioteca do SharePoint para a categoria 'Outro', preservando as plataformas 'Amazon Prime' e 'CazéTV' exclusivamente para os jogos oficiais do Brasileirão e Copa do Brasil acima.\n\n"
    "Atenciosamente,\n"
    "Cleber Gonçalves / Auditoria Autônoma — Monitor de Esportes"
)

print(f"Enviando e-mail para: {', '.join(recipients)}")
print(f"Anexos ({len(attachments)}): {[os.path.basename(a) for a in attachments]}")

svc = EmailService("smtp.gmail.com", 587, sender, password)
ok = svc.send_report(recipients, subject, body, pdf_path=attachments[0] if attachments else None, extra_attachments=attachments[1:] if len(attachments) > 1 else None)

if ok:
    print("✅ E-MAIL OFICIAL DO BRASILEIRÃO ENVIADO COM SUCESSO PARA ARTHUR E CLEBER!")
else:
    print("❌ Falha no envio do e-mail.")
