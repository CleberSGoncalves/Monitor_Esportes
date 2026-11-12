import os
import sys
import json
import subprocess
import requests

def publish_release():
    print("=== PUBLICANDO RELEASE NO GITHUB ===")
    
    # 1. Extrair token do git remote
    res = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
    remote_url = res.stdout.strip()
    if "@" in remote_url and "://" in remote_url:
        auth_part = remote_url.split("://")[1].split("@")[0]
        token = auth_part.split(":")[1] if ":" in auth_part else auth_part
    else:
        print("Erro: não foi possível extrair o token do git remote.")
        return False

    repo = "CleberSGoncalves/Monitor_Esportes"
    tag = "v2.5.9"
    release_name = "v2.5.9 - Fidelidade Estrita ao Streaming_Scheduler no Reporte de Eventos"
    body = (
        "### Novidades da versão v2.5.9:\n"
        "- 🎬 **Alinhamento e Fidelidade Estrita ao Streaming_Scheduler**:\n"
        "  - Grade de eventos inicia 100% limpa ao abrir a aplicação, exatamente como no projeto original.\n"
        "  - Botão 'Buscar Eventos' abre e navega de verdade nos portais oficiais das plataformas ativas (Amazon Prime Video, CazéTV, etc.).\n"
        "  - Sincronização e suporte completo aos perfis de autenticação `TempProfile` e `TempProfile2` para manter sessões ativas sem exigir logins manuais repetidos.\n"
        "- 🔗 **Prioridade das URLs Oficiais de Streaming**:\n"
        "  - Confrontos encontrados na Amazon Prime Video agora capturam as URLs canônicas autênticas (ex: `https://www.primevideo.com/-/pt/detail/...`).\n"
        "  - O pipeline da CBF (PDF) atua estritamente como retaguarda/fallback e nunca sobrepõe nem substitui eventos já encontrados nos carrosséis oficiais de streaming.\n"
        "- 📅 **Parser de Datas Avançado em Português e Inglês**:\n"
        "  - Suporte completo a formatos com abreviações de dias e meses (ex: `sáb., 14 de nov. 17:30 BRT`), formatos numéricos (`sábado, 1/08 17:00`), relativos (`Hoje às 20:00`) e formatos AM/PM em inglês.\n"
        "- 🛡️ **Isolamento e Estabilidade de Runtime**:\n"
        "  - Remoção de qualquer dependência externa ou acoplamento a caminhos absolutos fora do repositório.\n"
        "  - Instalação e empacotamento completo de `selenium 4.52.0`, `webdriver-manager 4.1.2`, `PyGetWindow 0.0.9` e `amazoncaptcha`.\n"
        "- 🧪 **118 Testes Automatizados Aprovados (100% de sucesso)**."
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 2. Verificar se release já existe
    r = requests.get(f"https://api.github.com/repos/{repo}/releases/tags/{tag}", headers=headers)
    if r.status_code == 200:
        release_data = r.json()
        release_id = release_data["id"]
        upload_url = release_data["upload_url"].split("{")[0]
        print(f"Release {tag} já existe (ID: {release_id}).")
    else:
        # Criar release
        payload = {
            "tag_name": tag,
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
            return False
        release_data = r_create.json()
        release_id = release_data["id"]
        upload_url = release_data["upload_url"].split("{")[0]
        print(f"Release {tag} criada com sucesso (ID: {release_id}).")

    # 3. Excluir asset anterior se existir
    r_assets = requests.get(f"https://api.github.com/repos/{repo}/releases/{release_id}/assets", headers=headers)
    if r_assets.status_code == 200:
        for asset in r_assets.json():
            if asset.get("name") == "Monitor_Esportes.exe":
                asset_id = asset.get("id")
                print(f"Removendo asset anterior (ID: {asset_id})...")
                requests.delete(f"https://api.github.com/repos/{repo}/releases/assets/{asset_id}", headers=headers)

    # 4. Fazer upload do executável
    exe_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist", "Monitor_Esportes.exe")
    if not os.path.exists(exe_path):
        print(f"Erro: Arquivo {exe_path} não encontrado!")
        return False

    exe_size = os.path.getsize(exe_path)
    print(f"Fazendo upload de {exe_path} ({exe_size / (1024*1024):.2f} MB)...")

    upload_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }

    with open(exe_path, "rb") as f:
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
        print("RELEASE PUBLICADA COM SUCESSO!")
        print(f"Versão: {tag}")
        print(f"Download URL: {download_url}")
        print("==================================================")
        return True
    else:
        print("Erro no upload do executável:", upload_resp.text)
        return False

if __name__ == "__main__":
    success = publish_release()
    sys.exit(0 if success else 1)
