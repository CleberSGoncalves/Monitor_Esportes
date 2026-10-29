import os
import sys
import json
import subprocess
import requests

sys.stdout.reconfigure(encoding="utf-8")

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.28"
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
release_name = "v2.4.28 - Gestão Global de E-mails NBA, Auditoria Completa Desde 20/10 e Correção da Exclusão de Destinatários"
body = (
    "### 🏀 Novidades e Correções da Versão 2.4.28:\n\n"
    "1. **Correção Definitiva da Exclusão de E-mails (Aba Configurações):**\n"
    "   - Eliminada a re-inserção compulsória de e-mails padrão que impedia a remoção de destinatários.\n"
    "   - Ao clicar em `🗑️ Remover`, o e-mail é apagado de forma definitiva tanto do arquivo `config/saved_emails.json` quanto da interface gráfica.\n\n"
    "2. **Opção Global de E-mails na Aba NBA (`✉️ E-mails NBA`):**\n"
    "   - Adicionado botão dedicado no topo da aba NBA para gerenciamento centralizado de destinatários.\n"
    "   - Qualquer alteração (adicionar, remover ou marcar destinatários ativos) reflete automaticamente em todas as partidas e na auditoria autônoma em segundo plano, sem necessidade de configuração jogo a jogo.\n\n"
    "3. **Auditoria e Sincronização de Toda a Temporada da NBA (Desde o Início em 20/10/2026):**\n"
    "   - O motor autônomo agora cobre todas as partidas desde o início oficial da temporada regular em 20/10/2026.\n"
    "   - Novo botão **`🏆 Sincronizar Temporada (Desde 20/10)`** para auditar em lote todas as rodadas já finalizadas, baixar os Game Books oficiais e publicar os relatórios com nota de 99.0% e placares finais no SharePoint.\n"
    "   - Implementada limpeza preventiva contra arquivos duplicados legados na biblioteca `Relatorios_de_Jogos_NBA` do SharePoint, garantindo 1 item canônico por partida.\n"
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
            print(f"[OK] Asset {asset_name} enviado com sucesso para a Release {TAG}!", flush=True)
        else:
            print(f"[ERRO] Erro no upload do executável: {r_up.status_code} - {r_up.text}", flush=True)
else:
    print(f"Executável não encontrado em {EXE_PATH}.", flush=True)
