import os
import json

BASE_DIR = r"E:\desenvolvimento\Monitor_Esportes"
CONFIG_DIR = os.path.join(BASE_DIR, "config")

def prepare_data():
    # 1. Carregar Drives (Bibliotecas de Documentos)
    drives_file = os.path.join(CONFIG_DIR, "sharepoint_real_drives_data.json")
    with open(drives_file, "r", encoding="utf-8") as f:
        drives_data = json.load(f)
    
    # Dicionário de bibliotecas por chave amigável
    clean_drives = {}
    for drv in drives_data.get("drives", []):
        name = drv.get("name")
        clean_drives[name] = {
            "name": name,
            "drive_id": drv.get("drive_id"),
            "webUrl": drv.get("webUrl"),
            "items_count": drv.get("root_items_count", 0),
            "items": drv.get("items", [])
        }
    
    # 2. Carregar Listas do SharePoint
    lists_file = os.path.join(CONFIG_DIR, "sharepoint_real_lists_data.json")
    with open(lists_file, "r", encoding="utf-8") as f:
        lists_data = json.load(f)
        
    clean_lists = {}
    for lst in lists_data.get("lists", []):
        display_name = lst.get("displayName")
        name = lst.get("name")
        cols = lst.get("columns", [])
        items = lst.get("items", [])
        template = lst.get("template")
        
        # Selecionar as 6 a 10 colunas mais importantes
        priority_cols = []
        for c in cols:
            col_name = c.get("name")
            disp = c.get("displayName")
            if not c.get("hidden") and disp not in ["Tipo de Conteúdo", "Anexos"]:
                priority_cols.append({"name": col_name, "displayName": disp, "type": c.get("type")})
        
        # Limpar itens para manter apenas campos úteis
        clean_items = []
        for itm in items[:300]: # top 300 itens por lista para garantir velocidade
            fields = itm.get("fields", {})
            row = {}
            for col in priority_cols:
                cname = col["name"]
                val = fields.get(cname)
                if val is not None:
                    row[cname] = str(val)
            if row:
                clean_items.append(row)
                
        clean_lists[display_name] = {
            "displayName": display_name,
            "name": name,
            "template": template,
            "columns": priority_cols[:8],
            "items_count": len(items),
            "items": clean_items
        }

    output_summary = {
        "drives": clean_drives,
        "lists": clean_lists
    }
    
    out_file = os.path.join(CONFIG_DIR, "sharepoint_portal_master_data.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_summary, f, ensure_ascii=False)
        
    size_mb = os.path.getsize(out_file) / (1024 * 1024)
    print(f"Master data gerado com sucesso: {out_file} ({size_mb:.2f} MB)")
    print(f"Total bibliotecas: {len(clean_drives)} | Total listas: {len(clean_lists)}")

if __name__ == "__main__":
    prepare_data()
