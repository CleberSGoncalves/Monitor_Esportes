import os, sys, requests, json
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SharePointReporter

token = SharePointReporter.obter_token_graph()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
site_id = SharePointReporter._cached_site_id

orig_list_id = "ae3e2afa-d937-41ad-af48-ecd65fd86143"
nba_list_id = "fa332a4b-5c46-433f-953d-e0534a9f5ecd"

print("--- COLUNAS DA LISTA ORIGINAL (Relatorios_Auditoria_Jogos) ---")
r_orig = SharePointReporter.request_with_retry("GET", f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{orig_list_id}/columns", headers=headers)
orig_cols = r_orig.json().get("value", [])
custom_orig_cols = []
for c in orig_cols:
    if not c.get("readOnly") and not c.get("hidden"):
        custom_orig_cols.append(c)
        print(f"Name: {c.get('name')} | Display: {c.get('displayName')} | Type: {[k for k in ['text', 'choice', 'dateTime', 'boolean', 'number', 'lookup'] if k in c]}")
        for k in ['text', 'choice', 'dateTime', 'boolean', 'number']:
            if k in c:
                print(f"   Detail {k}: {c[k]}")

print("\n--- COLUNAS DA LISTA NBA (Relatorios_de_Jogos_NBA) ATUAIS ---")
r_nba = SharePointReporter.request_with_retry("GET", f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{nba_list_id}/columns", headers=headers)
nba_cols = r_nba.json().get("value", [])
for c in nba_cols:
    if not c.get("readOnly") and not c.get("hidden"):
        print(f"Name: {c.get('name')} | Display: {c.get('displayName')} | Type: {[k for k in ['text', 'choice', 'dateTime', 'boolean', 'number', 'lookup'] if k in c]}")

with open("scripts/orig_columns.json", "w", encoding="utf-8") as f:
    json.dump(custom_orig_cols, f, indent=2, ensure_ascii=False)
