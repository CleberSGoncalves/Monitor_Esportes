import os
import sys
import json
import requests

PROJECT_ROOT = r"e:\desenvolvimento\Monitor_Esportes"
sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter, SP_CONFIG

token = SharePointReporter.obter_token_graph()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

site_id = SharePointReporter._cached_site_id
print("Site ID:", site_id)

r_lists = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists", headers=headers)
lists = r_lists.json().get("value", [])

orig_list = None
nba_list = None

for l in lists:
    name = l.get("name")
    disp = l.get("displayName")
    lid = l.get("id")
    print(f"List: {name} | DisplayName: {disp} | ID: {lid}")
    if name in ["Relatorios_Auditoria_Jogos", "Relatorios_de_Jogos"] or "Relatorio" in (name or ""):
        if "NBA" not in (name or "").upper() and "NBA" not in (disp or "").upper():
            orig_list = l
    if "NBA" in (name or "").upper() or "NBA" in (disp or "").upper():
        nba_list = l

print("\n--- Original List ---")
print(orig_list)

print("\n--- NBA List ---")
print(nba_list)

if orig_list:
    r_cols_orig = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{orig_list['id']}/columns", headers=headers)
    print("\n--- Columns in Original List ---")
    for col in r_cols_orig.json().get("value", []):
        if not col.get("readOnly") and not col.get("hidden"):
            print(f"Name: {col.get('name')} | Display: {col.get('displayName')} | Type: {list(col.keys())}")
            # print column schema
            for k in ["text", "choice", "dateTime", "boolean", "number"]:
                if k in col:
                    print(f"   Details ({k}): {col[k]}")

if nba_list:
    r_cols_nba = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{nba_list['id']}/columns", headers=headers)
    print("\n--- Columns in NBA List ---")
    for col in r_cols_nba.json().get("value", []):
        if not col.get("readOnly") and not col.get("hidden"):
            print(f"Name: {col.get('name')} | Display: {col.get('displayName')}")
