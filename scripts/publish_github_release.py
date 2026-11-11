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
    tag = "v2.4.48"
    release_name = "v2.4.48 - Modalidade Cobertura & Debate ao Vivo (Nome do Programa & Timeline Temática)"
    body = (
        "### Novidades da versão v2.4.48:\n"
        "- 🎙️ **Novo Modo 'Cobertura & Debate Esportivo ao Vivo' (YouTube)**:\n"
        "  - Suporte completo para transmissões ao vivo sem narração de bola rolando lance a lance (Central do Torcedor, Vamo Colorado, Baldasso Night Show, É o Grêmio, Os Donos da Bola, Bate-Bola, Resenha Fora da Sala, etc.).\n"
        "  - **Nome do Programa**: Reconhecimento automático e exibição proeminente no cabeçalho do laudo, na caixa de metadados, na interface gráfica e no SharePoint.\n"
        "  - **Timeline Temática por Blocos**: Divisão cronológica da live em capítulos temáticos com síntese das opiniões e análises da bancada, em vez de marcos fictícios de apito.\n"
        "  - **Auditoria de Marcas & Patrocinadores**: Mapeamento de todas as marcas, anúncios e merchandisings falados no estúdio.\n"
        "  - **Comprovação Visual Contínua**: Frames da transmissão ao vivo com tarja oficial de auditoria técnica no fuso de Brasília (BRT).\n"
        "- ⚽ **Modos Tradicionais 100% Preservados**:\n"
        "  - Brasileirão, Copa do Brasil (CBF / Streaming) e Jornadas com Narração Lance a Lance operando com 10/10 marcos intactos.\n"
        "- 🏀 **NBA Autônoma**: Sincronismo do Game Book, barreira anti-stub e canal oficial mantidos.\n"
        "- 🧪 **Testes Automatizados**: Suíte expandida com 61/61 testes 100% aprovados."
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
        print(f"  RELEASE {tag} PUBLICADA COM SUCESSO NO GITHUB! ")
        print(f"  URL de Download: {download_url}")
        print("==================================================")
        return True
    else:
        print("Erro no upload do executável:", upload_resp.text)
        return False

if __name__ == "__main__":
    publish_release()
