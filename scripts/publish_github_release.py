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
    tag = "v2.5.2"
    release_name = "v2.5.2 - Suporte a TempProfile/TempProfile2, Abertura Automática do Chrome & Correção de Logs"
    body = (
        "### Novidades da versão v2.5.2:\n"
        "- 📁 **Detecção Flexível de Perfis do Chrome (TempProfile e TempProfile2)**:\n"
        "  - O sistema agora detecta e utiliza automaticamente as pastas `TempProfile` e `TempProfile2` tanto se estiverem dentro da pasta `config/` (ex: `config\\TempProfile`) quanto na raiz da aplicação (ao lado do executável).\n"
        "  - Confirmação de suporte completo aos arquivos `auth.xml` e `config.xml` em `config/`.\n"
        "- 🌐 **Abertura Automática do Chrome (9222) ao Buscar Eventos**:\n"
        "  - Ao clicar em 'Buscar Eventos' (especialmente com 'Somente Relatório' ou plataformas ativas), o Chrome abre instantaneamente na tela utilizando o perfil autenticado `TempProfile` com depuração remota na porta 9222.\n"
        "  - Ativação de checagem ultrarrápida via socket (<1ms) para evitar qualquer travamento de rede.\n"
        "- 📺 **Scrapers de Streaming Integrados (Amazon Prime, Dazn, Max, Disney)**:\n"
        "  - Varredura de eventos ao vivo e agendados no Chrome 9222 com filtros de canais terceiros/Premiere e padronização de horários.\n"
        "- 📋 **Logs em Tempo Real e Histórico Completo na Aba Logs**:\n"
        "  - Gravação rotativa contínua via `RotatingFileHandler` em `log.txt` (até 5MB com 7 backups).\n"
        "  - Parser robusto que aceita múltiplos formatos de log e exibe histórico recente caso a data selecionada não contenha registros.\n"
        "- 🧪 **Cobertura de Testes E2E Expandida**:\n"
        "  - Suíte completa de 40 testes automatizados (unitários, integração e GUI E2E) 100% aprovada."
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
