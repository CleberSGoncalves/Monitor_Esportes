import os
import sys
import json
import subprocess
import requests

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.24"
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
release_name = "v2.4.24 - Auditoria NBA Multi-Plataforma, Sincronização Dinâmica SharePoint e Seletor Interativo"
body = (
    "### 🏀 Novidades e Implementações da Versão 2.4.24:\n\n"
    "1. **Auditoria de Transmissão Segmentada por Plataforma no Relatório NBA:**\n"
    "   - Bloco 1: Cronologia Oficial da Partida baseada no NBA Game Book oficial.\n"
    "   - Blocos de Auditoria em Streaming (2, 3...) gerados exclusivamente para as plataformas onde o jogo foi de fato transmitido (Disney, Amazon Prime, ESPN ou NBA League Pass).\n"
    "   - Parecer de Governança dinâmico homologado com as plataformas participantes.\n\n"
    "2. **Integração e Normalização com a Biblioteca SharePoint 'Relatorios_de_Jogos_NBA':**\n"
    "   - Preenchimento 100% automático e correto da coluna `Plataforma` (com valores `Disney`, `Amazon Prime`, `ESPN` ou `NBA`).\n"
    "   - Gravação dos metadados de Partida, Campeonato, Horário, Placar, Auditado e Grau de Confiança (99.0%).\n\n"
    "3. **Seletor Interativo de Plataforma no Card de Jogo:**\n"
    "   - Dropdown visual no card de cada partida da NBA permitindo alternar a plataforma (`Disney`, `Amazon Prime`, `ESPN`, `Disney + ESPN`, `NBA League Pass`) com cores contextuais e regeneração automática do relatório.\n"
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
    r = requests.post(f"https://api.github.com/repos/{repo}/releases", headers=headers, json=payload)
    if r.status_code in (200, 201):
        release_data = r.json()
        release_id = release_data["id"]
        upload_url = release_data["upload_url"].split("{")[0]
        print(f"Release {TAG} criada com sucesso (ID: {release_id})!")
    else:
        print(f"Erro ao criar release: {r.status_code} - {r.text}")
        sys.exit(1)

# Upload do executavel se existir
if os.path.exists(EXE_PATH):
    size_mb = os.path.getsize(EXE_PATH) / (1024 * 1024)
    print(f"Enviando {EXE_PATH} ({size_mb:.2f} MB)...")
    
    # Deleta asset existente se houver
    r_assets = requests.get(f"https://api.github.com/repos/{repo}/releases/{release_id}/assets", headers=headers)
    if r_assets.status_code == 200:
        for a in r_assets.json():
            if a.get("name") == "Monitor_Esportes.exe":
                print(f"Removendo asset antigo ID {a['id']}...")
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
        print("Executavel Monitor_Esportes.exe enviado com sucesso para a Release v2.4.24!")
    else:
        print(f"Falha no envio do asset: {r_up.status_code} - {r_up.text}")
else:
    print(f"Aviso: {EXE_PATH} nao encontrado para upload.")
