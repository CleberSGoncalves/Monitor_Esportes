import os
import sys
import json
import subprocess
import requests

sys.stdout.reconfigure(encoding="utf-8")

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.32"
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
release_name = "v2.4.32 - Desacoplamento Total de Projetos Externos, Auditoria Nativa CBF e Relatórios com Grounding Completo"
body = (
    "### 🚀 Novidades e Correções da Versão 2.4.32:\n\n"
    "1. **Desacoplamento Total de Projetos Externos:**\n"
    "   - Eliminada qualquer dependência de `Streaming_Scheduler` ou planilhas externas.\n"
    "   - Toda a esteira de monitoramento, agendamento de jogos e súmulas opera 100% de forma nativa e autônoma através dos módulos próprios (`CBFScheduleFetcher`, `ExpertAssistant` e `ReportGenerator`).\n\n"
    "2. **Relatórios Oficiais com Parecer Completo de Pesquisa e Grounding:**\n"
    "   - Todos os relatórios do Brasileirão foram regerados e sincronizados com o bloco completo de 'Confirmação de Horários na Transmissão Oficial & Cobertura Esportiva' (Súmula CBF, ge.globo.com, Lance!, portais oficiais de transmissão).\n"
    "   - Jogos oficiais 100% auditados e normalizados no SharePoint: Fluminense x Internacional (28/10), Vasco da Gama x Corinthians (24/10), Chapecoense x Fluminense (24/10) e Vasco da Gama x Remo (10/10).\n\n"
    "3. **Rotina Autônoma de Súmula e Agendamento Contínuo:**\n"
    "   - Agendamento autônomo baseado estritamente na tabela oficial da CBF (Brasileirão Série A e Copa do Brasil).\n"
    "   - Verificação automática da liberação de súmula oficial após 110 minutos de jogo com fallback de tolerância e atualização em tempo real.\n"
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
