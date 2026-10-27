import os
import sys
import json
import subprocess
import requests

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.3.8"
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
release_name = "v2.3.8 - Correcao Critica de Inicializacao (NumPy C-Extensions) & Sincronizacao SharePoint"
body = (
    "### O que ha de novo na v2.3.8:\n"
    "- Correcao Critica de Inicializacao (NumPy C-Extensions): Resolvido o erro de 'Importing the numpy C-extensions failed' empacotando integralmente as dependencias dinamicas do NumPy e as DLLs BLAS/OpenBLAS (numpy.libs e scipy.libs). A compressao UPX foi desativada no PyInstaller.\n"
    "- Publicacao dos Jogos do Fim de Semana (Rodada 30) no SharePoint: Relatorios completos em PDF com 100% dos 7 metadados obrigatorios sincronizados na biblioteca Relatorios_de_Jogos:\n"
    "  * Vasco da Gama 0 x 0 Remo (10/10/2026 - CazeTV)\n"
    "  * Coritiba 1 x 1 Botafogo (11/10/2026 - Amazon Prime)\n"
    "- Atualizacao dos Paineis e Fila com a Rodada 31: Inclusao dos confrontos oficiais futuros da 31a rodada do Brasileirao Serie A (Botafogo x Chapecoense em 17/10 e Athletico-PR x Palmeiras em 18/10)."
)

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

# 1. Verificar se a release já existe
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
    print("Create Release Status:", r_create.status_code)
    if r_create.status_code not in (200, 201):
        print("Erro ao criar release:", r_create.text)
        sys.exit(1)
    release_data = r_create.json()
    release_id = release_data["id"]
    upload_url = release_data["upload_url"].split("{")[0]
    print(f"Release {TAG} criada com sucesso (ID: {release_id}).")

# 2. Remover asset pré-existente se houver
r_assets = requests.get(f"https://api.github.com/repos/{repo}/releases/{release_id}/assets", headers=headers)
if r_assets.status_code == 200:
    for asset in r_assets.json():
        if asset.get("name") == "Monitor_Esportes.exe":
            asset_id = asset.get("id")
            print(f"Removendo asset anterior (ID: {asset_id})...")
            requests.delete(f"https://api.github.com/repos/{repo}/releases/assets/{asset_id}", headers=headers)

# 3. Upload do binário
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
    print("==================================================")
    print("  RELEASE v2.3.8 PUBLICADA COM SUCESSO NO GITHUB! ")
    print(f"  URL de Download: {download_url}")
    print("==================================================")
else:
    print("Erro no upload do asset:", upload_resp.text)
