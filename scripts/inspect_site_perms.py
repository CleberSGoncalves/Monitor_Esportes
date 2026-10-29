import sys, requests, json, time
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SharePointReporter

time.sleep(3)
token = SharePointReporter.obter_token_graph()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
site_id = SharePointReporter._cached_site_id
nba_list_id = "fa332a4b-5c46-433f-953d-e0534a9f5ecd"

# Check list info
r_list = SharePointReporter.request_with_retry("GET", f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{nba_list_id}", headers=headers)
print("List status:", r_list.status_code)
print("List data:", json.dumps(r_list.json(), indent=2))
