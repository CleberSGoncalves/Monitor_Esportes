import os
import sys
import json
import subprocess
import requests

sys.stdout.reconfigure(encoding="utf-8")

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.29"
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
release_name = "v2.4.29 - Correção do Crash no Update & Autenticação Enterprise SPN SharePoint 100% Autônoma"
body = (
    "### 🚀 Novidades e Correções da Versão 2.4.29:\n\n"
    "1. **Correção do Crash de Inicialização Pós-Update:**\n"
    "   - Corrigido `AttributeError: '_tkinter.tkapp' object has no attribute '_open_global_sharepoint_auth_modal'` ao iniciar o executável atualizado.\n"
    "   - Reordenação da árvore de execução do `main_gui.py`, garantindo que todos os métodos e mixins de interface sejam registrados no `MonitorApp` antes da inicialização do loop principal.\n\n"
    "2. **Integração Oficial do Service Principal Enterprise (SPN) da Azure:**\n"
    "   - O `Monitor_Esportes` agora utiliza o SPN em modo App-Only (`Client Credentials`), exatamente como o `Monitor_Servicos`.\n"
    "   - **Elimina 100% de qualquer bloqueio por Acesso Condicional da Azure (AADSTS53011)**, MFA, expiração de senhas de conta de usuário ou solicitações manuais de Device Code.\n"
    "   - Permissões validadas para leitura e gravação nas bibliotecas e listas `Relatorios_de_Jogos` (Futebol Brasileiro/Copa do Brasil) e `Relatorios_de_Jogos_NBA` (NBA 2026-27).\n\n"
    "3. **Auditoria e Sincronização 100% Autônoma e Resiliente:**\n"
    "   - Tokens são obtidos e renovados silenciosamente em segundo plano direto na Microsoft Graph API.\n"
    "   - Tratamento automático de rate limiting (HTTP 429) com backoff inteligente via cabeçalho `Retry-After`.\n"
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
