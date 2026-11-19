import os
import sys
import json
import time
import requests
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.sharepoint_reporter import SharePointReporter

SITE_ID = "adgbl.sharepoint.com,a3e49747-9bb6-4c93-9930-dda26c8d1050,34c8fe55-2cfe-4efc-8ce0-2958fd775ee0"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "sharepoint_real_drives_data.json")

def format_item(item: dict) -> dict:
    is_folder = "folder" in item
    is_file = "file" in item
    item_type = "folder" if is_folder else ("file" if is_file else "other")
    
    mime_type = ""
    if is_file and "file" in item:
        mime_type = item["file"].get("mimeType", "")
    
    # Extension
    name = item.get("name", "")
    ext = ""
    if is_file and "." in name:
        ext = name.rsplit(".", 1)[-1].lower()
    
    modified_by = ""
    last_mod_user = item.get("lastModifiedBy", {}).get("user", {})
    if last_mod_user:
        modified_by = last_mod_user.get("displayName", "")
    if not modified_by:
        modified_by = item.get("lastModifiedBy", {}).get("application", {}).get("displayName", "")

    return {
        "id": item.get("id"),
        "name": name,
        "type": item_type,
        "extension": ext,
        "mime_type": mime_type,
        "size": item.get("size", 0),
        "lastModifiedDateTime": item.get("lastModifiedDateTime", ""),
        "lastModifiedBy": modified_by,
        "webUrl": item.get("webUrl", ""),
        "childCount": item.get("folder", {}).get("childCount", 0) if is_folder else None
    }

def fetch_children(drive_id: str, item_id: str = "root", headers: dict = None, max_items: int = 200) -> List[dict]:
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/{'root' if item_id == 'root' else f'items/{item_id}'}/children?$top={max_items}"
    items = []
    while url:
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 5))
                time.sleep(retry_after)
                continue
            r.raise_for_status()
            data = r.json()
            items.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
            if len(items) >= max_items:
                break
            time.sleep(0.25)
        except Exception as e:
            print(f"Erro ao buscar children (drive: {drive_id}, item: {item_id}): {e}", file=sys.stderr)
            break
    return items

def main():
    print(f"Conectando ao SharePoint Graph API...")
    token = SharePointReporter.obter_token_graph()
    if not token:
        print("ERRO: Falha ao obter token Graph!")
        sys.exit(1)
    
    headers = {"Authorization": f"Bearer {token}"}
    drives_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives"
    resp = requests.get(drives_url, headers=headers, timeout=30)
    resp.raise_for_status()
    drives_list = resp.json().get("value", [])
    
    print(f"Total de Drives encontrados: {len(drives_list)}")
    
    result = {
        "site_id": SITE_ID,
        "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_drives": len(drives_list),
        "drives": []
    }
    
    for idx, drive in enumerate(drives_list, 1):
        d_id = drive.get("id")
        d_name = drive.get("name")
        d_web_url = drive.get("webUrl")
        d_type = drive.get("driveType")
        
        print(f"\n[{idx}/{len(drives_list)}] Mapeando Drive: '{d_name}' (ID: {d_id})...")
        
        drive_entry = {
            "drive_id": d_id,
            "name": d_name,
            "driveType": d_type,
            "webUrl": d_web_url,
            "root_items_count": 0,
            "folders_count": 0,
            "files_count": 0,
            "items": []
        }
        
        time.sleep(0.25)
        raw_items = fetch_children(d_id, "root", headers=headers, max_items=200)
        formatted_items = []
        
        folders_cnt = 0
        files_cnt = 0
        
        for raw in raw_items:
            f_item = format_item(raw)
            if f_item["type"] == "folder":
                folders_cnt += 1
                # Se for pasta e tiver poucos itens, mapeia subitens nível 1
                # para maior riqueza e fidelidade
                sub_children = []
                try:
                    time.sleep(0.25)
                    raw_sub = fetch_children(d_id, raw["id"], headers=headers, max_items=100)
                    for s_raw in raw_sub:
                        sub_children.append(format_item(s_raw))
                except Exception as e:
                    print(f"  Erro ao buscar subpasta {f_item['name']}: {e}")
                f_item["children"] = sub_children
            elif f_item["type"] == "file":
                files_cnt += 1
            formatted_items.append(f_item)
            
        drive_entry["root_items_count"] = len(formatted_items)
        drive_entry["folders_count"] = folders_cnt
        drive_entry["files_count"] = files_cnt
        drive_entry["items"] = formatted_items
        
        print(f"  -> Sucesso: {len(formatted_items)} itens na raiz ({folders_cnt} pastas, {files_cnt} arquivos)")
        result["drives"].append(drive_entry)
        
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        
    print(f"\nDados consolidados salvos com sucesso em: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
