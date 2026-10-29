import sys
import os
import requests

sys.path.insert(0, ".")
from modules.sharepoint_reporter import SharePointReporter

token = SharePointReporter.obter_token_graph()
site_id = SharePointReporter._cached_site_id
drive_id = SharePointReporter._cached_drive_id
headers = {"Authorization": f"Bearer {token}"}

url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children?$top=100"
r = SharePointReporter.request_with_retry("GET", url, headers=headers)
if r and r.status_code == 200:
    items = r.json().get("value", [])
    print(f"Total files in drive {drive_id}: {len(items)}")
    for it in items:
        f_id = it.get("id")
        name = it.get("name", "")
        print(f"FILE_ID: {f_id} | NAME: {name}")
else:
    print(f"Error {r.status_code if r else 'None'}: {r.text if r else ''}")
