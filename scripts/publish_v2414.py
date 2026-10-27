import os
import sys
import subprocess
import requests

CWD = r"e:\desenvolvimento\Monitor_Esportes"
TAG = "v2.4.14"
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
release_name = "v2.4.14 - Publicação SharePoint no Módulo de Lives, Relatórios de Ocorrências e Correção de E-mails"
body = (
    "### O que há de novo na v2.4.14:\n\n"
    "- ☁️ **Sincronização Nativa com o SharePoint na aba 'Canais Live':** Todos os relatórios gerados a partir de lives do YouTube agora são sincronizados automaticamente com a biblioteca `Relatorios_de_Jogos` do SharePoint com 7 metadados estritos.\n"
    "- ☁️ **Botão SharePoint por Card:** Cada transmissão agora conta com botão dedicado `☁️ SharePoint` para envio/sincronização direta com 1 clique (exibindo `☁️ No SharePoint` em verde quando já sincronizado).\n"
    "- 📄 **Relatório Técnico de Ocorrências (Debates, Pré-Jogos e Programas):** Quando um evento é classificado como programa/debate (ou seja, não é partida narrada lance a lance), o sistema agora disponibiliza o botão `📄 Relatório do Caso (Ocorrência)`, gerando parecer executivo oficial documentando diagnóstico da IA, marcas e inserções comerciais, também publicado no SharePoint.\n"
    "- 📋 **Relatório Geral de Auditoria de Lives:** Novo botão master na barra superior que consolida o histórico de todas as transmissões monitoradas em um relatório executivo PDF com parecer metodológico e estatísticas de cobertura, sincronizado com o SharePoint.\n"
    "- ✉️ **Correção Crítica no Envio de E-mails e Lista de Destinatários:** Resolvido o blacklist que impedia Arthur (`arthur@mediadna.com.br`) de receber notificações; restaurado o envio simultâneo para `cleber.goncalves@ibope.com` e `arthur@mediadna.com.br` com fallback defensivo para credenciais SMTP válidas.\n"
    "- 🔄 **Botão de Reprocessamento:** Adicionado botão `🔄 Reprocessar` nos cards para reexecutar transcrição e análise de IA sob demanda.\n"
    "- 🎨 **Layout da Barra Superior Aprimorado:** Estrutura dividida em 2 linhas funcionais sem corte de botões em qualquer resolução de tela."
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
