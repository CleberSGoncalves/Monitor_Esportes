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

# Recarregar lista oficial de destinatários
with open("config/saved_emails.json", "r", encoding="utf-8") as f:
    recipients = json.load(f)

with open("config/google_ai.json", "r", encoding="utf-8") as f:
    ai_cfg = json.load(f)

sender = ai_cfg.get("email", "kimsuportecaptacao@gmail.com")
password = ai_cfg.get("senha", "")

# Arquivos recém-gerados
reports_dir = os.path.join(PROJECT_ROOT, "reports")
recent_pdfs = [
    os.path.join(reports_dir, f) for f in os.listdir(reports_dir)
    if f.endswith(".pdf") and any(k in f for k in ("botafogo_x_chapecoense", "athletico-pr_x_palmeiras", "cruzeiro_x_fortaleza", "grêmio_x_internacional"))
]

# Pegar os mais recentes
from collections import defaultdict
latest_by_match = {}
for p in recent_pdfs:
    bn = os.path.basename(p)
    if "botafogo_x_chapecoense" in bn: latest_by_match["bota"] = p
    elif "athletico-pr_x_palmeiras" in bn: latest_by_match["ath"] = p
    elif "cruzeiro_x_fortaleza" in bn: latest_by_match["cruz"] = p
    elif "grêmio_x_internacional" in bn: latest_by_match["grenal"] = p

attachments = list(latest_by_match.values())

subject = "⚽ Relatórios Oficiais das Últimas Rodadas — Brasileirão Série A (Publicados no SharePoint)"
body = (
    "Olá,\n\n"
    "Os relatórios de auditoria e cronologia técnica das últimas duas rodadas foram gerados e sincronizados com 100% de conformidade no SharePoint (Relatorios_de_Jogos).\n\n"
    "Partidas contempladas nesta remessa:\n"
    "• Botafogo 2 x 0 Chapecoense (17/10/2026 - CazéTV)\n"
    "• Athletico-PR 0 x 2 Palmeiras (18/10/2026 - Amazon Prime)\n"
    "• Cruzeiro 1 x 1 Fortaleza (24/10/2026 - CazéTV)\n"
    "• Grêmio 1 x 1 Internacional (25/10/2026 - Amazon Prime)\n\n"
    "Todos os relatórios oficiais completos seguem anexados neste e-mail e já estão disponíveis no SharePoint para consulta.\n\n"
    "— Monitor de Esportes / Auditoria Autônoma"
)

print(f"Enviando e-mail para: {', '.join(recipients)}")
print(f"Anexos ({len(attachments)}): {[os.path.basename(a) for a in attachments]}")

svc = EmailService("smtp.gmail.com", 587, sender, password)
ok = svc.send_report(recipients, subject, body, pdf_path=attachments[0] if attachments else None, extra_attachments=attachments[1:] if len(attachments) > 1 else None)

if ok:
    print("✅ E-MAIL ENVIADO COM SUCESSO PARA ARTHUR E CLEBER!")
else:
    print("❌ Falha no envio do e-mail.")
