import os, sys, requests, json, time

sys.path.insert(0, '.')
from modules.sharepoint_reporter import SharePointReporter

def run_delta():
    print("Obtendo token Graph...")
    token = SharePointReporter.obter_token_graph()
    headers = {'Authorization': f'Bearer {token}'}
    drive_id = 'b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuCZQythstOgQIIcVHPouMa0'

    url = f'https://graph.microsoft.com/v1.0/drives/{drive_id}/root/delta'
    all_raw_items = []
    page = 1

    while url:
        print(f"Buscando página {page} do Delta...")
        for attempt in range(5):
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 429:
                wait_time = int(r.headers.get("Retry-After", 10))
                print(f"  [429 Throttled] Aguardando {wait_time}s...")
                time.sleep(wait_time)
                continue
            break

        if r.status_code != 200:
            print(f"Erro ao buscar delta: HTTP {r.status_code} - {r.text[:200]}")
            return False

        data = r.json()
        val = data.get("value", [])
        all_raw_items.extend(val)
        print(f"  Página {page}: +{len(val)} itens (total acumulado: {len(all_raw_items)})")
        url = data.get("@odata.nextLink")
        page += 1
        time.sleep(0.5)

    print(f"\nTotal bruto de itens coletados via Delta: {len(all_raw_items)}")

    # Mapear itens por ID
    items_by_id = {}
    root_id = None
    root_items = []
    rdp_count = 0

    # 1ª passada: formatar e indexar
    for it in all_raw_items:
        it_id = it.get("id")
        name = it.get("name", "")
        is_folder = "folder" in it
        is_file = "file" in it
        is_root = it.get("root") is not None

        if is_root:
            root_id = it_id
            continue

        item_type = "folder" if is_folder else ("file" if is_file else "other")
        mime = it.get("file", {}).get("mimeType", "") if is_file else ""
        ext = name.rsplit(".", 1)[-1].lower() if (is_file and "." in name) else ""
        if ext == "rdp":
            rdp_count += 1

        user = it.get("lastModifiedBy", {}).get("user", {}) or it.get("lastModifiedBy", {}).get("application", {})
        author = user.get("displayName", "Equipe Captação")

        parent_id = it.get("parentReference", {}).get("id")

        items_by_id[it_id] = {
            "id": it_id,
            "parent_id": parent_id,
            "name": name,
            "type": item_type,
            "extension": ext,
            "mime_type": mime,
            "size": it.get("size", 0),
            "lastModifiedDateTime": it.get("lastModifiedDateTime", ""),
            "lastModifiedBy": author,
            "webUrl": it.get("webUrl", ""),
            "childCount": it.get("folder", {}).get("childCount", 0) if is_folder else None,
            "children": [] if is_folder else None
        }

    print(f"Total de itens indexados: {len(items_by_id)} (Arquivos .RDP encontrados: {rdp_count})")

    # 2ª passada: montar a árvore hierárquica
    for it_id, it in items_by_id.items():
        parent_id = it["parent_id"]
        if parent_id == root_id or parent_id not in items_by_id:
            root_items.append(it)
        else:
            parent = items_by_id[parent_id]
            if parent["children"] is not None:
                parent["children"].append(it)

    print(f"Total de itens na raiz de Acesso Remoto: {len(root_items)}")

    # Limpar campo interno parent_id
    def clean_tree(items):
        for x in items:
            x.pop("parent_id", None)
            if x.get("children"):
                clean_tree(x["children"])

    clean_tree(root_items)

    # Atualizar master data
    master_path = os.path.join("config", "sharepoint_portal_master_data.json")
    with open(master_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    master_data["drives"]["Acesso Remoto"]["items"] = root_items
    master_data["drives"]["Acesso Remoto"]["items_count"] = len(root_items)

    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)

    print("config/sharepoint_portal_master_data.json atualizado com sucesso com toda a árvore RDP!")
    return True

if __name__ == "__main__":
    time.sleep(6) # Esperar cooldown do 429
    run_delta()
