import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import requests
from modules.sharepoint_reporter import SharePointReporter

token = SharePointReporter.obter_token_graph()
site_id = SharePointReporter._cached_site_id
drive_id = SharePointReporter._cached_drive_id

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children?$top=50&$expand=listItem($expand=fields)"
r = SharePointReporter.request_with_retry("GET", url, headers=headers)
data = r.json()
items = data.get("value", [])

print(f"Total itens encontrados: {len(items)}")
for it in items:
    name = it.get("name")
    fields = it.get("listItem", {}).get("fields", {})
    plat = fields.get("Plataforma")
    partida = fields.get("Partida")
    dt = fields.get("Data_Partida")
    item_id = it.get("id")
    print(f"Arquivo: {name} | Partida: {partida} | Plataforma: {plat} | Data: {dt} | ID: {item_id}")
