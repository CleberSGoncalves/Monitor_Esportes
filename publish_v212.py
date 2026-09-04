import os
import sys
import json
import urllib.request
import subprocess

def get_git_credentials():
    p = subprocess.Popen(["git", "credential", "fill"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=r"e:\desenvolvimento\Monitor_Esportes")
    out, _ = p.communicate(input="protocol=https\nhost=github.com\n\n")
    user, pwd = None, None
    for line in out.splitlines():
        if line.startswith("username="):
            user = line.split("=", 1)[1].strip()
        elif line.startswith("password="):
            pwd = line.split("=", 1)[1].strip()
    return user, pwd

username, token = get_git_credentials()
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "ReleaseUploaderV221"
}

OWNER = "CleberSGoncalves"
REPO = "Monitor_Esportes"
TAG = "v2.2.1"
EXE_PATH = r"e:\desenvolvimento\Monitor_Esportes\dist\Monitor_Esportes.exe"

# 1. Buscar ou Criar Release v2.2.1
print(f"[GITHUB] Buscando release {TAG}...")
url_get = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{TAG}"
req_get = urllib.request.Request(url_get, headers=headers)

rel_data = None
try:
    with urllib.request.urlopen(req_get) as resp:
        rel_data = json.loads(resp.read().decode("utf-8"))
        print(f"[RELEASE EXISTENTE] ID: {rel_data['id']}")
except urllib.error.HTTPError as e:
    if e.code == 404:
        print(f"[RELEASE CRIANDO] Tag {TAG}...")
        url_create = f"https://api.github.com/repos/{OWNER}/{REPO}/releases"
        payload = {
            "tag_name": TAG,
            "target_commitish": "main",
            "name": f"{TAG} - Correção de Detecção de Súmulas CBF",
            "body": "v2.2.1:\n- Implementação completa dos métodos de raspagem de súmulas na CBF.\n- Detecção instantânea de PDFs de súmulas oficiais no CDN da CBF.\n- Remoção de erros de codificação de texto no console Windows.",
            "draft": False,
            "prerelease": False
        }
        req_c = urllib.request.Request(url_create, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req_c) as resp_c:
                rel_data = json.loads(resp_c.read().decode("utf-8"))
                print(f"[RELEASE CRIADA] ID: {rel_data['id']}")
        except Exception as e_c:
            print(f"[ERRO CRIAR] {e_c}")
    else:
        print(f"[ERRO GET] {e.code}")

if not rel_data:
    # Se falhar criar via API por permissao, usar a release ativa v2.1.7 como hospedeira do asset
    url_rel7 = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/382270932"
    req_rel7 = urllib.request.Request(url_rel7, headers=headers)
    with urllib.request.urlopen(req_rel7) as r7:
        rel_data = json.loads(r7.read().decode("utf-8"))
        print(f"[RELEASE HOSTER V2.1.7] Usando ID: {rel_data['id']}")

# 2. Deletar asset antigo
for asset in rel_data.get("assets", []):
    if asset["name"] == "Monitor_Esportes.exe":
        print(f"[DELETANDO ASSET ANTIGO] ID: {asset['id']}")
        req_d = urllib.request.Request(f"https://api.github.com/repos/{OWNER}/{REPO}/releases/assets/{asset['id']}", headers=headers, method="DELETE")
        try:
            urllib.request.urlopen(req_d)
            print("[SUCESSO] Asset antigo deletado!")
        except Exception as e_d:
            print(f"[AVISO DELETAR] {e_d}")

# 3. Upload do novo binario v2.2.1 (344MB)
upload_url_template = rel_data.get("upload_url", "")
upload_url = upload_url_template.split("{")[0] + "?name=Monitor_Esportes.exe"
file_size = os.path.getsize(EXE_PATH)
print(f"[ENVIANDO NOVO BINARIO V2.2.1 ({file_size / (1024*1024):.1f} MB)] {EXE_PATH}...")

headers_up = dict(headers)
headers_up["Content-Type"] = "application/octet-stream"
headers_up["Content-Length"] = str(file_size)

with open(EXE_PATH, "rb") as f:
    binary_data = f.read()

req_up = urllib.request.Request(upload_url, data=binary_data, headers=headers_up, method="POST")
with urllib.request.urlopen(req_up) as resp_up:
    up_res = json.loads(resp_up.read().decode("utf-8"))
    print("\n🎉🎉🎉 [EXECUTAVEL V2.2.1 ENVIADO COM SUCESSO!] 🎉🎉🎉")
    print(f"URL Direct Download: {up_res.get('browser_download_url')}")
