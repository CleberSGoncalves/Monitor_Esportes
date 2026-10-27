import os
import sys
import subprocess
import requests

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.15"
EXE_PATH = r"e:\desenvolvimento\Monitor_Esportes\dist\Monitor_Esportes.exe"

res = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, cwd=CWD)
remote_url = res.stdout.strip()
if "@" in remote_url and "://" in remote_url:
    auth_part = remote_url.split("://")[1].split("@")[0]
    token = auth_part.split(":")[1] if ":" in auth_part else auth_part
else:
    print("Erro: token nao encontrado no remote.")
    sys.exit(1)

repo = "CleberSGoncalves/Monitor_Esportes"
release_name = "v2.4.15 - Otimização Extrema de Performance (Canais Live), Paginação 60 FPS e Abertura Imediata de Relatórios"
body = (
    "### O que há de novo na v2.4.15:\n\n"
    "- ⚡ **Eliminação Total de Travamentos e 'Não está respondendo':** Implementada arquitetura de renderização ultra-leve com debounce de 350ms em `CanaisLiveMixin`. O sistema não reconstrói mais centenas de widgets desnecessariamente a cada atualização de evento.\n"
    "- 🎯 **Virtualização e Paginação Inteligente (60 FPS):** A fila de análise e a lista de eventos agora renderizam cards paginados (15 na fila, 25 nos eventos) com botões elegantes `🔽 Carregar Mais` e `Mostrar Todos`, reduzindo o número de widgets em mais de 85% e tornando a interface instantânea.\n"
    "- 🔍 **Filtros Rápidos na Fila:** Adicionados botões no cabeçalho da fila: `Todas`, `🟡 Ativas` (lives e em processamento) e `🟢 Prontas` (relatórios gerados).\n"
    "- 🧹 **Botão 'Limpar Antigas':** Permite desmarcar da fila eventos antigos já finalizados com 1 clique, mantendo apenas transmissões em andamento e relatórios prontos.\n"
    "- 👁️ **Abertura Imediata de Relatórios PDF:** Tanto o `📋 Relatório Geral de Auditoria` quanto o `📄 Relatório do Caso (Ocorrência)` agora abrem o PDF instantaneamente na tela do usuário (`os.startfile`) sem travar a interface ou bloquear o loop de eventos.\n"
    "- 📂 **Acesso Direto aos Arquivos:** Adicionados botões no topo da aba: `📂 Pasta de Relatórios` (abre a pasta no Windows Explorer) e `📑 Ver Relatórios (PDF)` (modal responsivo listando todos os PDFs gerados com botão de abrir)."
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
            print(f"Removendo asset antigo ID {asset.get('id')}...")
            requests.delete(f"https://api.github.com/repos/{repo}/releases/assets/{asset.get('id')}", headers=headers)

exe_size = os.path.getsize(EXE_PATH)
print(f"Fazendo upload de {EXE_PATH} ({exe_size / (1024*1024):.2f} MB)...")

upload_headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/octet-stream",
}
with open(EXE_PATH, "rb") as f_exe:
    upload_resp = requests.post(
        f"{upload_url}?name=Monitor_Esportes.exe",
        headers=upload_headers,
        data=f_exe
    )

if upload_resp.status_code in (200, 201):
    print("Upload de Monitor_Esportes.exe concluido com sucesso!")
else:
    print(f"Erro no upload do asset: {upload_resp.status_code} - {upload_resp.text}")
    sys.exit(1)

print(f"Release {TAG} publicada com sucesso no GitHub!")
