import sys
import os
import requests
import json

sys.path.insert(0, ".")
from modules.sharepoint_reporter import SharePointReporter

token = SharePointReporter.obter_token_graph()
site_id = SharePointReporter._cached_site_id
headers = {"Authorization": f"Bearer {token}"}

list_id = "ae3e2afa-d937-41ad-af48-ecd65fd86143"
url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?$expand=fields&$top=100"

r = requests.get(url, headers=headers)
print("Status:", r.status_code)
if r.status_code == 200:
    items = r.json().get("value", [])
    print(f"Total items in list: {len(items)}")
    for it in items:
        f = it.get("fields", {})
        partida = f.get("Partida") or f.get("Title") or ""
        data_hora = f.get("Data_Hora") or ""
        plat = f.get("Plataforma") or ""
        comp = f.get("Campeonato") or ""
        aud = f.get("Auditado")
        print(f"ID: {it.get('id')} | Data: {data_hora} | Comp: {comp} | Partida: {partida} | Plat: {plat} | Aud: {aud}")

# Also check drive items (files in library Relatorios_de_Jogos)
drive_id = SharePointReporter._cached_drive_id
url_drive = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children?$top=100"
r_d = requests.get(url_drive, headers=headers)
print(f"\nTotal files in drive {drive_id}:")
if r_d.status_code == 200:
    d_items = r_d.json().get("value", [])
    print(f"Total files: {len(d_items)}")
    for d in d_items:
        print(f"File ID: {d.get('id')} | Name: {d.get('name')}")
