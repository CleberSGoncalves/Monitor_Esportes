import os
import sys
import json
import subprocess
import requests

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.27"
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
release_name = "v2.4.27 - Correção de Layout Fullscreen NBA, Relatórios Concisos de Canais e Autenticação Interativa SharePoint"
body = (
    "### 🏀 Novidades e Correções da Versão 2.4.27:\n\n"
    "1. **Correção Definitiva de Layout na Aba NBA e Canais Live:**\n"
    "   - Eliminada a compressão vertical da tabela da NBA provocada pelo aparecimento indevido dos painéis manuais de auditoria e busca do YouTube na base da janela.\n"
    "   - Ao alternar para as abas fullscreen (`🏀 Eventos NBA`, `Canais Live`), todos os painéis manuais e sidebars são ocultados incondicionalmente, liberando 100% da altura da janela para a grade de jogos.\n\n"
    "2. **Higienização Executiva dos Relatórios de Canais do YouTube (`Canais Live`):**\n"
    "   - Filtragem estrita: eliminados do relatório lances de jogo comuns (gols, cartões amarelos, cartões vermelhos, faltas, substituições).\n"
    "   - Foco exclusivo nos 8 marcos regulamentares de transmissão: pré-jogo (abertura de sinal), apito inicial (1º tempo), acréscimos 1ºT, intervalo (halftime), início 2ºT, acréscimos 2ºT, fim de jogo e encerramento de transmissão.\n"
    "   - Remoção de poluição visual do PDF: eliminado o despejo massivo de transcrição bruta e linhas pontilhadas excessivas, mantendo o documento executivo e direto.\n"
    "   - Desativado o envio automático ao SharePoint para lives de canais do YouTube (apenas geração de PDF local mantida; envio ao SharePoint permanece manual via botão).\n\n"
    "3. **Autenticação Interativa Corporativa do SharePoint (Microsoft Device Code Flow):**\n"
    "   - Correção do crash no validador de token JWT (`import time`).\n"
    "   - Novo modal interativo nativo para conexão com o Microsoft Graph / SharePoint: ao clicar em `🔑 SharePoint` (no header do app) ou `🔑 Conectar SharePoint` (na aba NBA), um código amigável de 8 dígitos é copiado para a área de transferência e o navegador é aberto automaticamente em `https://login.microsoft.com/device`.\n"
    "   - Ao autorizar a conta institucional (`svc.captacao@adgbl.com`), o assistente salva os novos tokens e conclui a sincronização instantaneamente.\n"
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
        print(f"Release {TAG} criada com sucesso (ID: {release_id}).", flush=True)
    else:
        print(f"Erro ao criar release: {r.status_code} - {r.text}", flush=True)
        sys.exit(1)

# Upload do executável Monitor_Esportes.exe
asset_name = "Monitor_Esportes.exe"
print(f"Verificando assets existentes para {asset_name}...", flush=True)
r_assets = requests.get(f"https://api.github.com/repos/{repo}/releases/{release_id}/assets", headers=headers)
if r_assets.status_code == 200:
    for asset in r_assets.json():
        if asset["name"] == asset_name:
            print(f"Removendo asset antigo {asset_name} (ID: {asset['id']})...", flush=True)
            requests.delete(f"https://api.github.com/repos/{repo}/releases/assets/{asset['id']}", headers=headers)

if os.path.exists(EXE_PATH):
    print(f"Iniciando upload de {EXE_PATH} ({os.path.getsize(EXE_PATH) / (1024*1024):.1f} MB)...", flush=True)
    with open(EXE_PATH, "rb") as f_exe:
        upload_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream"
        }
        r_up = requests.post(
            f"{upload_url}?name={asset_name}",
            headers=upload_headers,
            data=f_exe,
            timeout=300
        )
        if r_up.status_code in (200, 201):
            print(f"🎉 Asset {asset_name} enviado com sucesso para a Release {TAG}!", flush=True)
        else:
            print(f"❌ Erro no upload do executável: {r_up.status_code} - {r_up.text}", flush=True)
else:
    print(f"⚠️ Executável não encontrado em {EXE_PATH}. Execute o build primeiro.", flush=True)
