import os, sys
sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_nba_reporter import SharePointNBAReporter
from modules.sharepoint_reporter import SharePointReporter

token = SharePointReporter.obter_token_graph()
site_id = SharePointReporter._cached_site_id
drive_id = SharePointNBAReporter.get_nba_drive_id(token, site_id)
name = sys.argv[1] if len(sys.argv) > 1 else "Relatorio_NBA_BKN_at_BOS_20261027.pdf"
url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{name}?$select=name,size,lastModifiedDateTime"
r = SharePointReporter.request_with_retry("GET", url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
if r is not None and r.status_code == 200:
    d = r.json()
    print("SharePoint:", d.get("name"), d.get("size"), "bytes |", d.get("lastModifiedDateTime"))
else:
    print("Falha:", r.status_code if r is not None else None)
