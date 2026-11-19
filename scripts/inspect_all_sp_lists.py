import os, sys, requests, json
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SharePointReporter

def inspect_lists():
    token = SharePointReporter.obter_token_graph()
    headers = {"Authorization": f"Bearer {token}"}
    site_id = SharePointReporter._cached_site_id
    
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
    r = SharePointReporter.request_with_retry("GET", url, headers=headers)
    if not r or r.status_code != 200:
        print("Failed to get lists:", r.status_code if r else "None")
        return
        
    lists = r.json().get("value", [])
    print(f"Total SharePoint Lists found: {len(lists)}")
    
    results = []
    for l in sorted(lists, key=lambda x: x.get("displayName", "")):
        lid = l.get("id")
        title = l.get("displayName")
        name = l.get("name")
        webUrl = l.get("webUrl")
        
        # Get count of items
        item_count = 0
        try:
            r_items = SharePointReporter.request_with_retry("GET", f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{lid}/items?$top=1", headers=headers)
            if r_items and r_items.status_code == 200:
                # Some lists provide @odata.count or items list
                items_val = r_items.json().get("value", [])
                item_count = len(items_val)
        except Exception:
            pass
            
        print(f"- {title} (name: {name}) | ID: {lid}")
        results.append({
            "title": title,
            "name": name,
            "id": lid,
            "url": webUrl
        })
        
    with open("config/sharepoint_all_lists_catalog.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nCatalog saved to config/sharepoint_all_lists_catalog.json")

if __name__ == '__main__':
    inspect_lists()
