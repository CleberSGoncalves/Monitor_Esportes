import os, sys, requests, json
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SharePointReporter

token = SharePointReporter.obter_token_graph()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
site_id = SharePointReporter._cached_site_id
nba_list_id = "fa332a4b-5c46-433f-953d-e0534a9f5ecd"

columns_to_create = [
    {
        "name": "Partida",
        "displayName": "Partida",
        "text": {
            "allowMultipleLines": False,
            "maxLength": 255
        }
    },
    {
        "name": "Campeonato",
        "displayName": "Campeonato",
        "choice": {
            "allowTextEntry": True,
            "choices": ["NBA", "NBA Temporada Regular", "NBA In-Season Tournament", "NBA Playoffs", "NBA Finals", "WNBA", "Outro"],
            "displayAs": "dropDownMenu"
        }
    },
    {
        "name": "Plataforma",
        "displayName": "Plataforma",
        "choice": {
            "allowTextEntry": True,
            "choices": ["Amazon Prime", "Disney", "ESPN", "NBA League Pass", "YouTube", "Caze TV", "Outro"],
            "displayAs": "dropDownMenu"
        }
    },
    {
        "name": "Data_Partida",
        "displayName": "Data_Hora",
        "dateTime": {
            "displayAs": "standard",
            "format": "dateTime"
        }
    },
    {
        "name": "Auditado",
        "displayName": "Auditado",
        "boolean": {}
    },
    {
        "name": "Confianca",
        "displayName": "Confianca",
        "text": {
            "allowMultipleLines": False,
            "maxLength": 255
        }
    },
    {
        "name": "Placar",
        "displayName": "Placar",
        "text": {
            "allowMultipleLines": False,
            "maxLength": 255
        }
    }
]

for col in columns_to_create:
    col_name = col["name"]
    print(f"\nCriando coluna '{col_name}' ({col['displayName']})...")
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{nba_list_id}/columns"
    resp = SharePointReporter.request_with_retry("POST", url, headers=headers, json=col)
    print(f"Status: {resp.status_code}")
    if resp.status_code in (200, 201):
        print(f"✅ Coluna '{col_name}' criada com sucesso!")
    else:
        print(f"❌ Resposta: {resp.text}")
