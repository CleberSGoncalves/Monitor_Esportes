import sys, requests, json
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SharePointReporter

token = SharePointReporter.obter_token_graph()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
site_id = SharePointReporter._cached_site_id

r_site_cols = SharePointReporter.request_with_retry("GET", f"https://graph.microsoft.com/v1.0/sites/{site_id}/columns", headers=headers)
print("Site columns status:", r_site_cols.status_code)
if r_site_cols.status_code == 200:
    for c in r_site_cols.json().get("value", []):
        if not c.get("readOnly") and not c.get("hidden"):
            print(f"Site Column: name={c.get('name')} disp={c.get('displayName')} group={c.get('columnGroup')}")
