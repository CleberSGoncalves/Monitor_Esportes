import os
import sys
import json
import subprocess
import requests

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.18"
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
release_name = "v2.4.18 - Despoluição Radical da Fila e Eliminação Sumária de Não-Jogos"
body = (
    "### 🚀 Novidades e Correções da Versão 2.4.18:\n\n"
    "1. **Despoluição Radical da Fila da Direita (Anti-Poluição Absoluta):**\n"
    "   - Eventos que não são partidas de futebol (programas diários, notícias, debates, correspondente, trânsito, mercado da bola, boletins) são **automaticamente eliminados da fila**.\n"
    "   - A fila de análise passa a exibir **exclusivamente transmissões de jogos reais**.\n\n"
    "2. **Filtro Inteligente de Inclusão no Auto-Detect Jogo:**\n"
    "   - O sistema agora pré-analisa os títulos e só enfileira eventos que possuam confronto evidente entre dois times (`team1 x team2`) com indicativo de partida/transmissão esportiva.\n"
    "   - Programas como 'Esportes ao Meio-Dia', 'Notícias do RS', 'Bagé TV News' e lives políticas nem sequer entram na fila.\n\n"
    "3. **Botão '🧹 Limpar Não-Jogos' na Barra Superior:**\n"
    "   - Permite executar a qualquer momento uma faxina com 1 clique para remover sumariamente qualquer evento que não seja jogo.\n\n"
    "4. **Resgate e Destaque dos Jogos de 24/10/2026 (Inter x Botafogo):**\n"
    "   - As transmissões oficiais da partida de 24/10 foram atualizadas para o status encerrado (`ended`) e posicionadas na fila da direita em destaque, prontas para gerar o relatório cronológico."
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
    print(f"Release {TAG} ja existe (ID: {release_id}).")
else:
    payload = {
        "tag_name": TAG,
        "target_commitish": "main",
        "name": release_name,
        "body": body,
        "draft": False,
        "prerelease": False
    }
    r_create = requests.post(f"https://api.github.com/repos/{repo}/releases", headers=headers, json=payload)
    if r_create.status_code not in (200, 201):
        print("Erro ao criar release:", r_create.text)
        sys.exit(1)
    release_data = r_create.json()
    release_id = release_data["id"]
    upload_url = release_data["upload_url"].split("{")[0]
    print(f"Release {TAG} criada com sucesso (ID: {release_id}).")

r_assets = requests.get(f"https://api.github.com/repos/{repo}/releases/{release_id}/assets", headers=headers)
if r_assets.status_code == 200:
    for asset in r_assets.json():
        if asset.get("name") == "Monitor_Esportes.exe":
            print("Removendo asset anterior para atualizar...")
            requests.delete(f"https://api.github.com/repos/{repo}/releases/assets/{asset.get('id')}", headers=headers)

exe_size = os.path.getsize(EXE_PATH)
print(f"Fazendo upload de {EXE_PATH} ({exe_size / (1024*1024):.2f} MB)...")

upload_headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/octet-stream",
}

with open(EXE_PATH, "rb") as f:
    upload_resp = requests.post(
        f"{upload_url}?name=Monitor_Esportes.exe",
        headers=upload_headers,
        data=f,
        timeout=600
    )

print("Upload Asset Status:", upload_resp.status_code)
if upload_resp.status_code in (200, 201):
    asset_info = upload_resp.json()
    download_url = asset_info.get("browser_download_url")
    print(f"RELEASE {TAG} PUBLICADA COM SUCESSO! Download: {download_url}")
else:
    print("Erro no upload do asset:", upload_resp.text)
