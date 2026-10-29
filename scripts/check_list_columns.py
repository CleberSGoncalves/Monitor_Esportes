import sys
import os
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter

token = SharePointReporter.obter_token_graph()
site_id = SharePointReporter._cached_site_id
list_id = "ae3e2afa-d937-41ad-af48-ecd65fd86143"

url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/columns"
r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
if r.status_code == 200:
    for c in r.json().get("value", []):
        print(f"{c.get('name')}: {c.get('displayName')}")
else:
    print(f"Error: {r.status_code} - {r.text}")
