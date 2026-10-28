import os
import sys
from pathlib import Path
import time
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.sharepoint_reporter import SharePointReporter, SP_CONFIG

def setup_nba_sharepoint_library():
    print("=" * 60)
    print("CONFIGURAÇÃO DA BIBLIOTECA SHAREPOINT: Relatorios_de_Jogos_NBA")
    print("=" * 60)

    token = SharePointReporter.obter_token_graph()
    site_id = SharePointReporter._cached_site_id
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Verificar se a biblioteca já existe
    print("1. Verificando se a biblioteca 'Relatorios_de_Jogos_NBA' já existe...")
    url_lists = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
    r = SharePointReporter.request_with_retry("GET", url_lists, headers=headers)
    
    existing = None
    for l in r.json().get("value", []):
        if l.get("name") == "Relatorios_de_Jogos_NBA" or l.get("displayName") == "Relatorios_de_Jogos_NBA":
            existing = l
            break

    if existing:
        print(f"✅ Biblioteca 'Relatorios_de_Jogos_NBA' já existe! ID: {existing['id']}")
        list_id = existing["id"]
    else:
        print("Criando nova Document Library 'Relatorios_de_Jogos_NBA' no SharePoint...")
        payload = {
            "displayName": "Relatorios_de_Jogos_NBA",
            "list": {
                "template": "documentLibrary"
            }
        }
        r_create = SharePointReporter.request_with_retry("POST", url_lists, headers=headers, json=payload)
        if r_create.status_code in (200, 201):
            list_id = r_create.json()["id"]
            print(f"✅ Biblioteca criada com sucesso! ID: {list_id}")
        else:
            print(f"❌ Erro ao criar biblioteca ({r_create.status_code}): {r_create.text}")
            return False

    # 2. Configurar colunas customizadas
    print("\n2. Verificando e criando colunas customizadas...")
    url_cols = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/columns"
    r_cols = SharePointReporter.request_with_retry("GET", url_cols, headers=headers)
    current_cols = {c.get("name"): c for c in r_cols.json().get("value", [])}

    columns_to_add = [
        {
            "name": "Partida",
            "displayName": "Partida",
            "text": {}
        },
        {
            "name": "Campeonato",
            "displayName": "Campeonato",
            "choice": {
                "choices": ["NBA", "NBA Playoffs", "NBA Finals", "NBA Cup", "WNBA"]
            }
        },
        {
            "name": "Plataforma",
            "displayName": "Plataforma",
            "choice": {
                "choices": ["Amazon Prime", "Disney", "ESPN", "Outro"]
            }
        },
        {
            "name": "Data_Partida",
            "displayName": "Data_Hora",
            "dateTime": {}
        },
        {
            "name": "Confianca",
            "displayName": "Confianca",
            "text": {}
        },
        {
            "name": "Auditado",
            "displayName": "Auditado",
            "boolean": {}
        },
        {
            "name": "Placar",
            "displayName": "Placar",
            "text": {}
        }
    ]

    for col in columns_to_add:
        c_name = col["name"]
        if c_name in current_cols:
            print(f"   • Coluna '{c_name}' já existe.")
        else:
            print(f"   + Criando coluna '{c_name}'...")
            try:
                r_c = SharePointReporter.request_with_retry("POST", url_cols, headers=headers, json=col)
                if r_c.status_code in (200, 201):
                    print(f"     ✅ Coluna '{c_name}' criada com sucesso!")
                else:
                    print(f"     ⚠️ Falha ao criar coluna '{c_name}' ({r_c.status_code}): {r_c.text}")
            except Exception as ex_col:
                print(f"     ❌ Exceção ao criar coluna '{c_name}': {ex_col}")
            time.sleep(1)

    # 3. Localizar o Drive correspondente para uploads
    url_drives = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    r_dr = SharePointReporter.request_with_retry("GET", url_drives, headers=headers)
    nba_drive = None
    for d in r_dr.json().get("value", []):
        if "NBA" in d.get("name", ""):
            nba_drive = d
            break

    if nba_drive:
        print(f"\n🎉 Drive do SharePoint identificado com sucesso: {nba_drive.get('name')} (ID: {nba_drive.get('id')})")
        print(f"URL Web: {nba_drive.get('webUrl')}")
    else:
        print("\n⚠️ Drive NBA ainda não indexado no cache de drives (estará disponível em instantes).")

    return True

if __name__ == "__main__":
    setup_nba_sharepoint_library()
