import html
import re
import json

with open("config/sharepoint_homepage_content.aspx", "r", encoding="utf-8") as f:
    text = f.read()

# Extrai CanvasContent1
m = re.search(r'<mso:CanvasContent1[^>]*>(.*?)</mso:CanvasContent1>', text, re.DOTALL)
if not m:
    print("CanvasContent1 not found")
    exit(1)

raw_canvas = html.unescape(m.group(1))

# Encontra todos os webparts e dados JSON
webparts = []
wp_matches = re.findall(r'data-sp-controldata="([^"]+)"', raw_canvas)
for wp in wp_matches:
    try:
        decoded_wp = html.unescape(wp)
        data = json.loads(decoded_wp)
        webparts.append(data)
    except Exception as e:
        print("Error parsing wp:", e)

print(f"Total webparts encontrados: {len(webparts)}")

# Salva webparts decodificados
with open("config/sharepoint_homepage_webparts.json", "w", encoding="utf-8") as f:
    json.dump(webparts, f, indent=2, ensure_ascii=False)

# Também salva o HTML completo do canvas decodificado
with open("config/sharepoint_homepage_canvas_decoded.html", "w", encoding="utf-8") as f:
    f.write(raw_canvas)

print("Canvas decodificado salvo em config/sharepoint_homepage_canvas_decoded.html")

# Imprime resumo dos tipos de webparts e conteúdos de texto
for i, wp in enumerate(webparts):
    title = wp.get("title") or wp.get("webPartData", {}).get("title") or wp.get("controlType")
    server_props = wp.get("webPartData", {}).get("serverProcessedContent", {})
    props = wp.get("webPartData", {}).get("properties", {})
    print(f"\n[{i+1}] {title} (ID: {wp.get('id')})")
    
    # Textos pesquisáveis
    search_texts = server_props.get("searchablePlainTexts", {})
    if search_texts:
        print("   Textos:", search_texts)
    
    # Links
    links = server_props.get("links", {})
    if links:
        print("   Links:", links)
        
    # Imagens
    images = server_props.get("imageSources", {})
    if images:
        print("   Imagens:", images)

    # Propriedades específicas (ex: Quick Links, List, etc)
    items = props.get("items")
    if items:
        print(f"   Itens ({len(items)}):")
        for it in items:
            print("     *", it.get("title"), "->", it.get("sourceItem", {}).get("url") or it.get("description"))
