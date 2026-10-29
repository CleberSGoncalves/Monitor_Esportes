import os
import sys
import json
import subprocess
import requests

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.25"
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
release_name = "v2.4.25 - Botão Direto Eventos NBA no Topo, Fila Completa CBF (Copa do Brasil e Brasileirão) e Agenda NBA SharePoint"
body = (
    "### 🏀 Novidades e Correções da Versão 2.4.25:\n\n"
    "1. **Botão Direto '🏀 Eventos NBA' na Barra Superior:**\n"
    "   - Adicionado na barra principal `ESTRATÉGIA DE MONITORAMENTO` (ao lado de `Canais Live`) e corrigida a exibição contínua da aba `🏀 Eventos NBA`.\n\n"
    "2. **Atualização Completa da Escala do Brasileirão e Copa do Brasil:**\n"
    "   - O botão `📥 Preencher com Próximos Eventos` agora carrega todos os 5 slots com a escala atualizada de Outubro/Novembro (Vasco x Flamengo, Flamengo x Corinthians, Palmeiras x Vasco, Grêmio x Atlético-MG, Athletico-PR x Vasco, São Paulo x Corinthians, Cruzeiro x Bahia, etc.).\n\n"
    "3. **Publicação da Agenda Completa da NBA no SharePoint (`Relatorios_de_Jogos_NBA`):**\n"
    "   - Novo botão `📅 Publicar Agenda SharePoint` para registrar todas as partidas agendadas e finalizadas na lista do SharePoint.\n"
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
    print(f"Release {TAG} ja existe (ID: {release_id}).", flush=True)
else:
    payload = {
        "tag_name": TAG,
        "target_commitish": "main",
        "name": release_name,
        "body": body,
        "draft": False,
        "prerelease": False
    }
    r = requests.post(f"https://api.github.com/repos/{repo}/releases", headers=headers, json=payload)
    if r.status_code in (200, 201):
        release_data = r.json()
        release_id = release_data["id"]
        upload_url = release_data["upload_url"].split("{")[0]
        print(f"Release {TAG} criada com sucesso (ID: {release_id})!", flush=True)
    else:
        print(f"Erro ao criar release: {r.status_code} - {r.text}", flush=True)
        sys.exit(1)

if os.path.exists(EXE_PATH):
    size_mb = os.path.getsize(EXE_PATH) / (1024 * 1024)
    print(f"Enviando {EXE_PATH} ({size_mb:.2f} MB)...", flush=True)
    
    r_assets = requests.get(f"https://api.github.com/repos/{repo}/releases/{release_id}/assets", headers=headers)
    if r_assets.status_code == 200:
        for a in r_assets.json():
            if a.get("name") == "Monitor_Esportes.exe":
                print(f"Removendo asset antigo ID {a['id']}...", flush=True)
                requests.delete(a["url"], headers=headers)
    
    upload_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream"
    }
    with open(EXE_PATH, "rb") as f:
        r_up = requests.post(
            f"{upload_url}?name=Monitor_Esportes.exe",
            headers=upload_headers,
            data=f,
            timeout=600
        )
    if r_up.status_code in (200, 201):
        print(f"Executavel Monitor_Esportes.exe enviado com sucesso para a Release {TAG}!", flush=True)
    else:
        print(f"Falha no envio do asset: {r_up.status_code} - {r_up.text}", flush=True)
else:
    print(f"Aviso: {EXE_PATH} nao encontrado para upload.", flush=True)
