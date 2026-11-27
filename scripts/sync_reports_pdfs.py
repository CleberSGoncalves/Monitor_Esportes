import sys
import os
import requests

PROJECT_ROOT = r"E:\desenvolvimento\Monitor_Esportes"
sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter
from scripts.sync_authentic_docs_from_sharepoint import DRIVES

def sync_reports():
    tok = SharePointReporter.obter_token_graph()
    headers = {"Authorization": f"Bearer {tok}"}

    drives_to_sync = {
        "Relatorios_de_Jogos": "futebol",
        "Relatorio Jogos Youtube": "youtube",
        "Relatorios_de_Jogos_NBA": "nba"
    }

    total_downloaded = 0

    for dname, cat in drives_to_sync.items():
        drive_id = DRIVES[dname][0]
        dest_docs = os.path.join(PROJECT_ROOT, "docs", "reports", cat)
        dest_portal = os.path.join(PROJECT_ROOT, "portal_web", "reports", cat)
        os.makedirs(dest_docs, exist_ok=True)
        os.makedirs(dest_portal, exist_ok=True)

        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children?$top=200"
        items = []
        while url:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code != 200:
                print(f"[ERR] Failed to list items from {dname}: {r.status_code}")
                break
            data = r.json()
            for it in data.get("value", []):
                if "file" in it and it["name"].lower().endswith(".pdf"):
                    items.append(it)
            url = data.get("@odata.nextLink")

        print(f"\n[INFO] Drive {dname} ({cat}): found {len(items)} PDFs in SharePoint.")
        newly_dl = 0
        for it in items:
            fn = it["name"]
            item_id = it["id"]
            f_docs = os.path.join(dest_docs, fn)
            f_portal = os.path.join(dest_portal, fn)

            if not os.path.exists(f_docs) or os.path.getsize(f_docs) == 0:
                dl_url = it.get("@microsoft.graph.downloadUrl")
                if not dl_url:
                    r_meta = requests.get(f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}", headers=headers, timeout=20)
                    if r_meta.status_code == 200:
                        dl_url = r_meta.json().get("@microsoft.graph.downloadUrl")
                if dl_url:
                    try:
                        r_dl = requests.get(dl_url, timeout=45)
                        if r_dl.status_code == 200:
                            with open(f_docs, "wb") as fw:
                                fw.write(r_dl.content)
                            with open(f_portal, "wb") as fw:
                                fw.write(r_dl.content)
                            newly_dl += 1
                            total_downloaded += 1
                            print(f"  [DL] {fn} ({len(r_dl.content)} bytes)")
                    except Exception as e:
                        print(f"  [ERR] {fn}: {e}")
            else:
                if not os.path.exists(f_portal) or os.path.getsize(f_portal) == 0:
                    with open(f_docs, "rb") as fr, open(f_portal, "wb") as fw:
                        fw.write(fr.read())

        print(f"[OK] {dname}: downloaded {newly_dl} missing files.")

    print(f"\n[SUCCESS] Total downloaded: {total_downloaded}")

if __name__ == "__main__":
    sync_reports()
