import os
import sys
import json
import subprocess
import requests

sys.stdout.reconfigure(encoding="utf-8")

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.33"
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
release_name = "v2.4.33 - Homogeneidade Estrita e Ordenação Cronológica de Agendamentos & Validação E2E do Próximo Jogo"
body = (
    "### 🚀 Novidades e Correções da Versão 2.4.33:\n\n"
    "1. **Homogeneidade Estrita entre Tela Principal e Modal de Agendamentos:**\n"
    "   - Resolvida a divergência de ordem e partidas entre o painel lateral ('FILA DE AGENDAMENTOS') e o modal de agendamento.\n"
    "   - Implementada ordenação cronológica obrigatória (`_sort_games_chronologically`) em todos os pontos do ciclo de vida: carregamento, salvamento, renderização de cards e preenchimento automático.\n"
    "   - O próximo confronto oficial (`Vasco da Gama x Flamengo`, 29/10/2026 às 20:00 pelo Brasileirão Série A no Amazon Prime) é garantido de forma determinística como Jogo #1 no topo de ambas as telas.\n\n"
    "2. **Validação E2E de Ponta a Ponta para o Próximo Jogo (Vasco da Gama x Flamengo):**\n"
    "   - Temporizadores de countdown com contagem regressiva precisa em horas, minutos e segundos até o pontapé inicial.\n"
    "   - Transição automática de status: `Aguardando Kickoff` ➔ `Ao Vivo (Em Andamento)` ➔ `Auditoria Autônoma pós-jogo (+110 min)`.\n"
    "   - Consulta nativa da súmula no portal oficial da CBF com tolerância inteligente (`allow_web_fallback`), assegurando geração ininterrupta do relatório mesmo em caso de atraso na publicação pela federação.\n"
    "   - Relatório PDF de 2 páginas validado com marcos técnicos na Página 1 e parecer oficial de transmissão com links na Página 2.\n"
    "   - Sincronização automática com a lista e biblioteca `Relatorios_de_Jogos` do SharePoint e disparo por e-mail.\n"
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
