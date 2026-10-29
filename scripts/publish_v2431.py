import os
import sys
import json
import subprocess
import requests

sys.stdout.reconfigure(encoding="utf-8")

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.31"
EXE_PATH = r"e:\desenvolvimento\Monitor_Esportes\dist\Monitor_Esportes.exe"

res = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, cwd=CWD)
remote_url = res.stdout.strip()
if "@" in remote_url and "://" in remote_url:
    auth_part = remote_url.split("://")[1].split("@")[0]
    token = auth_part.split(":")[1] if ":" in auth_part else auth_part
else:
    print("Erro: token não encontrado no remote.")
    sys.exit(1)

repo = "CleberSGoncalves/Monitor_Esportes"
release_name = "v2.4.31 - Isolamento Rigoroso YouTube, Auditoria Oficial CBF e Sincronização Streaming Scheduler"
body = (
    "### 🚀 Novidades e Correções da Versão 2.4.31:\n\n"
    "1. **Isolamento Absoluto de Canais do YouTube no SharePoint Oficial (`Relatorios_de_Jogos`):**\n"
    "   - Bloqueio estrito no `ReportGenerator` e `LiveChannelMonitor` impedindo que relatórios de teste, casos de ocorrência ou narração do YouTube subam para a biblioteca de jogos oficiais de futebol.\n"
    "   - Purge completo executado no SharePoint: removidos todos os itens de teste e PDFs impróprios que estavam impactando a operação da equipe do Arthur.\n\n"
    "2. **Auditoria e Publicação dos 4 Jogos Oficiais do Brasileirão:**\n"
    "   - Vasco da Gama 0 x 0 Remo (10/10/2026, CazéTV) - regularizado com data/hora e metadados oficiais.\n"
    "   - Vasco da Gama 3 x 2 Corinthians (24/10/2026, CazéTV) - auditado com cronologia completa de marcos técnicos e gols.\n"
    "   - Chapecoense 2 x 1 Fluminense (24/10/2026, Amazon Prime) - auditado e sincronizado com telemetria nominal.\n"
    "   - Fluminense 2 x 1 Internacional (28/10/2026, CazéTV) - auditado com acréscimos, virada tricolor e conformidade total.\n\n"
    "3. **Integração Nativa com o Streaming Scheduler (`data.csv`):**\n"
    "   - Sincronização bilateral direta entre `Streaming_Scheduler/data.csv` e o agendamento autônomo do `Monitor_Esportes`.\n"
    "   - Partida de hoje (Vasco da Gama x Flamengo, 29/10/2026 19:00, Amazon Prime) e próximas rodadas agendadas e monitoradas com tolerância de auditoria e súmula eletrônica da CBF.\n\n"
    "4. **Correções na Gestão de E-mails (Configurações e NBA):**\n"
    "   - Correção do botão '🗑️ Remover' na aba Configurações (exclusão insensível a maiúsculas/minúsculas persistida no `saved_emails.json` e `%APPDATA%`).\n"
    "   - Suporte a sincronização global de destinatários no modal '✉️ E-mails NBA' refletindo para toda a temporada.\n"
)

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

r = requests.get(f"https://api.github.com/repos/{repo}/releases/tags/{TAG}", headers=headers)
if r.status_code == 200:
    release_data = r.json()
    release_id = release_data["id"]
    upload_url = release_data["upload_url"].split("{")[0]
    print(f"Release {TAG} já existe (ID: {release_id}).", flush=True)
else:
    payload = {
        "tag_name": TAG,
        "name": release_name,
        "body": body,
        "draft": False,
        "prerelease": False
    }
    r = requests.post(f"https://api.github.com/repos/{repo}/releases", headers=headers, json=payload)
    if r.status_code != 201:
        print(f"Erro ao criar release: {r.status_code} - {r.text}", flush=True)
        sys.exit(1)
    release_data = r.json()
    release_id = release_data["id"]
    upload_url = release_data["upload_url"].split("{")[0]
    print(f"Release {TAG} criada com sucesso (ID: {release_id}).", flush=True)

# Listar assets existentes para substituir se necessário
r_assets = requests.get(f"https://api.github.com/repos/{repo}/releases/{release_id}/assets", headers=headers)
if r_assets.status_code == 200:
    for asset in r_assets.json():
        if asset["name"] == "Monitor_Esportes.exe":
            print(f"Deletando asset antigo {asset['name']} (ID: {asset['id']})...", flush=True)
            requests.delete(f"https://api.github.com/repos/{repo}/releases/assets/{asset['id']}", headers=headers)

# Upload do executável compilado
print(f"Fazendo upload de {EXE_PATH} ({os.path.getsize(EXE_PATH) / 1024 / 1024:.2f} MB)...", flush=True)
with open(EXE_PATH, "rb") as f_exe:
    upload_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream"
    }
    r_upload = requests.post(
        f"{upload_url}?name=Monitor_Esportes.exe",
        headers=upload_headers,
        data=f_exe,
        timeout=300
    )
    if r_upload.status_code == 201:
        print("Upload do Monitor_Esportes.exe concluído com sucesso!", flush=True)
    else:
        print(f"Erro no upload: {r_upload.status_code} - {r_upload.text}", flush=True)
        sys.exit(1)
