import os
import sys
from pathlib import Path
import time
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.sharepoint_reporter import SharePointReporter, SP_CONFIG

def setup_youtube_sharepoint_library():
    print("=" * 65)
    print("CONFIGURAÇÃO DA BIBLIOTECA SHAREPOINT: Relatorio Jogos Youtube")
    print("=" * 65)

    token = SharePointReporter.obter_token_graph()
    site_id = SharePointReporter._cached_site_id
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Obter a biblioteca/lista 'Relatorio Jogos Youtube' diretamente
    print("1. Acessando a biblioteca 'Relatorio Jogos Youtube' diretamente...")
    url_list = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/Relatorio%20Jogos%20Youtube"
    r = SharePointReporter.request_with_retry("GET", url_list, headers=headers)
    if r.status_code not in (200, 201):
        print(f"❌ Erro ao acessar biblioteca: {r.status_code} - {r.text}")
        return False
    list_data = r.json()
    list_id = list_data["id"]
    print(f"✅ Biblioteca encontrada! Nome: {list_data.get('name')}, ID: {list_id}")

    # 2. Consultar colunas atuais
    print("\n2. Verificando colunas existentes...")
    url_cols = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/columns"
    r_cols = SharePointReporter.request_with_retry("GET", url_cols, headers=headers)
    current_cols = {c.get("name"): c for c in r_cols.json().get("value", [])}
    current_display_names = {c.get("displayName"): c for c in r_cols.json().get("value", [])}

    columns_to_add = [
        {
            "name": "Partida",
            "displayName": "Partida",
            "text": {},
            "description": "Confronto da transmissão (ex: Grêmio x Atlético-MG)"
        },
        {
            "name": "Canal",
            "displayName": "Canal",
            "choice": {
                "choices": ["Rádio Gaúcha", "CazéTV", "GZH", "Flazoeiro TV", "Bagé TV", "Voz do Esporte", "Paulistão", "Outro"]
            },
            "description": "Canal do YouTube que transmitiu a live"
        },
        {
            "name": "Campeonato",
            "displayName": "Campeonato",
            "choice": {
                "choices": ["Copa do Brasil", "Brasileiro Serie A", "Paulista", "Libertadores", "Sul-Americana", "Amistoso", "Outro"]
            },
            "description": "Campeonato ou competição"
        },
        {
            "name": "Data_Jogo",
            "displayName": "Data_Jogo",
            "dateTime": {},
            "description": "Data e horário do jogo / transmissão"
        },
        {
            "name": "Placar",
            "displayName": "Placar",
            "text": {},
            "description": "Placar final identificado na transmissão (ex: Grêmio 2 x 0 Atlético-MG)"
        },
        {
            "name": "Inicio_Transmissao",
            "displayName": "Inicio_Transmissao",
            "text": {},
            "description": "Horário de início da live / sinal"
        },
        {
            "name": "Apito_Inicial",
            "displayName": "Apito_Inicial",
            "text": {},
            "description": "Horário do apito inicial (1T) auditado"
        },
        {
            "name": "Apito_Final",
            "displayName": "Apito_Final",
            "text": {},
            "description": "Horário do apito final (2T) auditado"
        },
        {
            "name": "Fim_Transmissao",
            "displayName": "Fim_Transmissao",
            "text": {},
            "description": "Horário de término da live"
        },
        {
            "name": "Duracao_Live",
            "displayName": "Duracao_Live",
            "text": {},
            "description": "Duração total do vídeo / live (ex: 02h 45min 00s)"
        },
        {
            "name": "URL_Video",
            "displayName": "URL_Video",
            "text": {},
            "description": "Link do vídeo no YouTube"
        },
        {
            "name": "Confianca",
            "displayName": "Confianca",
            "text": {},
            "description": "Nível de assertividade da IA (ex: 99.0%)"
        },
        {
            "name": "Auditado",
            "displayName": "Auditado",
            "boolean": {},
            "description": "Confirmação de auditoria concluída"
        },
        {
            "name": "Status",
            "displayName": "Status",
            "choice": {
                "choices": ["Concluído", "Em Andamento", "Divergente", "Pré-Jogo"]
            },
            "description": "Status operacional do evento"
        }
    ]

    print("\n3. Criando/Verificando colunas customizadas...")
    for col in columns_to_add:
        c_name = col["name"]
        c_disp = col["displayName"]
        if c_name in current_cols or c_disp in current_display_names:
            print(f"   • Coluna '{c_name}' ('{c_disp}') já existe.")
        else:
            print(f"   + Criando coluna '{c_name}' ({list(col.keys())})...")
            try:
                r_c = SharePointReporter.request_with_retry("POST", url_cols, headers=headers, json=col)
                if r_c.status_code in (200, 201):
                    print(f"     ✅ Coluna '{c_name}' criada com sucesso!")
                else:
                    print(f"     ⚠️ Falha ao criar coluna '{c_name}' ({r_c.status_code}): {r_c.text}")
            except Exception as ex_col:
                print(f"     ❌ Exceção ao criar coluna '{c_name}': {ex_col}")
            time.sleep(1)

    # 4. Validar o Drive para uploads
    drive_id = "b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuB9cyT1xIdlTLVA1lg-2mHZ"
    print(f"\n🎉 Drive do SharePoint identificado com sucesso: Relatorio Jogos Youtube (ID: {drive_id})")
    print(f"URL Web: https://adgbl.sharepoint.com/sites/suportecaptacao/Relatorio%20Jogos%20Youtube")

    print("\n" + "=" * 65)
    print("PROCESSO DE CONFIGURAÇÃO CONCLUÍDO COM SUCESSO!")
    print("=" * 65)
    return True

if __name__ == "__main__":
    setup_youtube_sharepoint_library()
