import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_nba_reporter import SharePointNBAReporter
from modules.sharepoint_reporter import SharePointReporter

token = SharePointReporter.obter_token_graph()
site_id = SharePointReporter._cached_site_id
drive_id = SharePointNBAReporter.get_nba_drive_id(token, site_id)

url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children?$select=name,size,lastModifiedDateTime&$top=100"
headers = {"Authorization": f"Bearer {token}"}
r = SharePointReporter.request_with_retry("GET", url, headers=headers)
if r and r.status_code == 200:
    items = r.json().get("value", [])
    print(f"Total items in SharePoint NBA library: {len(items)}")
    for it in items:
        print(f"  {it.get('name')} | {it.get('size')} bytes | {it.get('lastModifiedDateTime')}")
else:
    print("Error:", r.status_code if r else "None")
