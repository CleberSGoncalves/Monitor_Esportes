import os
import sys
import time
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter

def graph_call(method, url, **kwargs):
    max_attempts = 15
    for attempt in range(max_attempts):
        try:
            r = requests.request(method, url, **kwargs)
            if r.status_code == 429:
                wait_sec = int(r.headers.get("Retry-After", 10))
                try:
                    body = r.json()
                    wait_sec = int(body.get("retryAfterSeconds") or wait_sec)
                except Exception:
                    pass
                wait_sec = max(wait_sec, 5)
                print(f"[Graph API 429] Throttled. Aguardando {wait_sec}s (tentativa {attempt+1}/{max_attempts})...", flush=True)
                time.sleep(wait_sec)
                continue
            return r
        except Exception as e:
            print(f"[Graph API Exception] {e}. Aguardando 5s...", flush=True)
            time.sleep(5)
    return None

def main():
    token = SharePointReporter.obter_token_graph()
    site_id = SharePointReporter._cached_site_id
    drive_id = SharePointReporter._cached_drive_id
    list_id = "ae3e2afa-d937-41ad-af48-ecd65fd86143"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    print(f"Site ID: {site_id}")
    print(f"List ID: {list_id}")
    print(f"Drive ID: {drive_id}")

    # 1. Fetch list items
    url_items = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?$expand=fields&$top=150"
    r = graph_call("GET", url_items, headers=headers)
    if r and r.status_code == 200:
        items = r.json().get("value", [])
        print(f"\n=== LIST ITEMS IN Relatorios_de_Jogos ({len(items)} items) ===")
        for it in sorted(items, key=lambda x: str(x.get("fields", {}).get("Data_Partida", "")), reverse=True):
            f = it.get("fields", {})
            item_id = it.get("id")
            data_hora = f.get("Data_Partida", "SEM_DATA")
            partida = f.get("Partida", "SEM_PARTIDA")
            camp = f.get("Campeonato", "")
            plat = f.get("Plataforma", "")
            auditado = f.get("Auditado", "")
            conf = f.get("Confianca", "")
            print(f"ID {item_id:3s} | {data_hora:20s} | {partida:35s} | {plat:15s} | {conf:7s} | Auditado: {auditado}")
    else:
        print(f"Error fetching list items: {r.status_code if r else 'None'}")

    # 2. Fetch drive files
    url_drive = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children?$top=150"
    r_d = graph_call("GET", url_drive, headers=headers)
    if r_d and r_d.status_code == 200:
        files = r_d.json().get("value", [])
        print(f"\n=== DRIVE FILES IN Relatorios_de_Jogos ({len(files)} files) ===")
        for f in sorted(files, key=lambda x: x.get("name", "")):
            print(f" - {f.get('name')}")
    else:
        print(f"Error fetching drive files: {r_d.status_code if r_d else 'None'}")

if __name__ == "__main__":
    main()
