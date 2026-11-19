import html
import re
import json

with open("config/sharepoint_homepage_canvas_decoded.html", "r", encoding="utf-8") as f:
    content = f.read()

wp_data = re.findall(r'data-sp-controldata="([^"]+)"', content)
print(f"Total de controles encontrados: {len(wp_data)}")

for i, raw in enumerate(wp_data):
    try:
        data = json.loads(html.unescape(raw))
        wpd = data.get("webPartData", {})
        spc = wpd.get("serverProcessedContent", {})
        props = wpd.get("properties", {})
        title = wpd.get("title") or props.get("title") or data.get("controlType")
        print(f"\n==========================================")
        print(f"CONTROLE #{i+1}: {title} (ID: {data.get('id')})")
        print(f"==========================================")
        
        texts = spc.get("searchablePlainTexts", {})
        if texts:
            print("--- TEXTOS ---")
            for k, v in texts.items():
                print(f"  [{k}]: {v}")
                
        links = spc.get("links", {})
        if links:
            print("--- LINKS ---")
            for k, v in links.items():
                print(f"  [{k}]: {v}")
                
        images = spc.get("imageSources", {})
        if images:
            print("--- IMAGENS ---")
            for k, v in images.items():
                print(f"  [{k}]: {v}")

        items = props.get("items")
        if items:
            print(f"--- ITENS ({len(items)}) ---")
            for idx, item in enumerate(items):
                i_title = item.get("title") or item.get("rawTitle")
                i_desc = item.get("description")
                link_key = f"items[{idx}].sourceItem.url"
                link_val = links.get(link_key) or item.get("sourceItem", {}).get("url")
                print(f"  * {i_title} | {i_desc} -> {link_val}")

    except Exception as e:
        print("Erro:", e)
