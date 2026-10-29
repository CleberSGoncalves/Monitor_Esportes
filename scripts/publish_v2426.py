import os
import sys
import json
import subprocess
import requests

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.26"
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
release_name = "v2.4.26 - Auditoria Autônoma NBA em Background, Modal de E-mail Interativo, SharePoint Instantâneo e Tabela Oficial CBF"
body = (
    "### 🏀 Novidades e Correções da Versão 2.4.26:\n\n"
    "1. **Auditoria e Sincronização 100% Autônoma da NBA (`NBAAutonomousAuditor`):**\n"
    "   - Monitoramento contínuo em segundo plano da tabela e grade oficial da NBA.\n"
    "   - Sincronização automática de partidas agendadas e atualizações dinâmicas de data, hora e plataforma na biblioteca `Relatorios_de_Jogos_NBA` do SharePoint.\n"
    "   - Para jogos finalizados: download automático do NBA Game Book oficial, geração do PDF de auditoria técnica executivo, arquivamento no SharePoint e disparo automático de e-mail aos destinatários.\n\n"
    "2. **Modal Interativo de E-mail na Aba NBA:**\n"
    "   - O botão `✉️ E-mail` agora abre um modal completo para selecionar com checkboxes os destinatários cadastrados em `saved_emails.json` antes do envio, com feedback e alerta de confirmação.\n\n"
    "3. **Feedback Visual e Confirmação no Botão SharePoint:**\n"
    "   - O botão `☁️ SharePoint` agora fornece feedback imediato (`⏳ Enviando...` -> `✅ Sincronizado`) e exibe popup detalhado de confirmação com os metadados sincronizados.\n\n"
    "4. **Purga Definitiva de Jogos Fictícios e Alinhamento CBF 2026:**\n"
    "   - Removido qualquer confronto fictício (como Corinthians x Flamengo em 31/10). A fila oficial agora segue estritamente a tabela oficial da CBF (Vasco x Flamengo 29/10 Prime, Palmeiras x Vasco 01/11 Copa do Brasil, Grêmio x Atlético-MG 01/11 Copa do Brasil, Athletico-PR x Vasco 04/11 CazéTV, Cruzeiro x Bahia 05/11 Prime).\n"
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
