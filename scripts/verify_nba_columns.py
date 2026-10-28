import sys, json
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SharePointReporter

token = SharePointReporter.obter_token_graph()
headers = {"Authorization": f"Bearer {token}"}
site_id = SharePointReporter._cached_site_id
nba_list_id = "fa332a4b-5c46-433f-953d-e0534a9f5ecd"

url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{nba_list_id}/columns"
r = SharePointReporter.request_with_retry("GET", url, headers=headers)
print("Status:", r.status_code)
cols = r.json().get("value", [])
print(f"Total columns: {len(cols)}")
for c in cols:
    if not c.get("readOnly") and not c.get("hidden"):
        col_type = [k for k in ["text", "choice", "dateTime", "boolean", "number"] if k in c]
        print(f"Name (Internal): {c.get('name')} | Display: {c.get('displayName')} | Type: {col_type}")
