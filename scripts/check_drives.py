import os, sys, requests, json, time
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SharePointReporter

token = SharePointReporter.obter_token_graph()
headers = {"Authorization": f"Bearer {token}"}
site_id = SharePointReporter._cached_site_id

print("Obtendo Drives...")
r = SharePointReporter.request_with_retry("GET", f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives", headers=headers)
print("Drives status:", r.status_code)
drives = r.json().get("value", [])
for d in drives:
    print(f"Drive: {d.get('name')} | ID: {d.get('id')} | URL: {d.get('webUrl')}")

print("\nObtendo Lists...")
r_lists = SharePointReporter.request_with_retry("GET", f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists", headers=headers)
print("Lists status:", r_lists.status_code)
lists = r_lists.json().get("value", [])
for l in lists:
    print(f"List: {l.get('name')} | Title: {l.get('displayName')} | ID: {l.get('id')} | URL: {l.get('webUrl')}")
