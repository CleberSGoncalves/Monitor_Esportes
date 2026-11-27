import os
import sys
import json
import time
import urllib.parse
import requests
import openpyxl

PROJECT_ROOT = r"E:\desenvolvimento\Monitor_Esportes"
sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter
from modules.sharepoint_inspector_sync import SITE_ID

DRIVES = {
    "SLA": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuAiMlxcWATcTY1l2wDjd68a", "sheets"),
    "Escala de trabalho": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuBSDMK_ees4RrJJcQIBJdUN", "sheets"),
    "Avaliação Técnica de Fornecedores": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuBHHSvyzw-RQY16RvbW2_5z", "sheets"),
    "Ficha de Capacitação": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuCUq-InqtU5Ra8eHg_ppkTx", "sheets"),
    "Acesso Remoto": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuCZQythstOgQIIcVHPouMa0", "sheets"),
    "Mapa Campeonatos 2026 SAM": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuDW4JyOVHcjQ5cIFzJdmQz-", "sheets"),
    "Tratativa de Problemas de captação": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuCus9HejWkNR6q5OxaX0vcZ", "sheets"),
    "Metas": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuCOqXJUf8YvQKhPgnpL8tlJ", "sheets"),
    "Documentos": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuCfnnbm2ArvQIsZIMnl-Ht-", "sheets"),
    "Analise de Dados": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuC_kInV8m4PQrj74AoBw8XI", "sheets"),
    "Análise de Notificações": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuBfN3VI4YsfSZ0Txv0wdguv", "sheets"),
    "Documentos Técnicos": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuBU2TOPPEfRR596kIedmaJc", "sheets"),
    "Procedimentos": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuCu9C_HBprRRbp1Rrhom4nZ", "sheets"),
    "Relatorio Jogos Youtube": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuB9cyT1xIdlTLVA1lg-2mHZ", "reports/youtube"),
    "Relatorios_de_Jogos": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuD6Kj6uN9mtQa9I7NZf2GFD", "reports/futebol"),
    "Relatorios_de_Jogos_NBA": ("b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuBLKjP6Rlw_Q5U94FNKn17N", "reports/nba"),
}

def graph_get(url, headers, stream=False):
    for attempt in range(6):
        try:
            r = requests.get(url, headers=headers, timeout=45, stream=stream)
            if r.status_code in (429, 502, 503, 504):
                wait = int(r.headers.get("Retry-After", 3 + attempt * 2))
                time.sleep(wait)
                continue
            return r
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            time.sleep(2 + attempt * 2)
    return requests.get(url, headers=headers, timeout=60, stream=stream)

def list_drive_items_recursive(drive_id, headers, item_id="root"):
    items = []
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/children?$top=200"
    while url:
        r = graph_get(url, headers)
        if r.status_code != 200:
            print(f"  WARN {r.status_code} on {url}")
            break
        data = r.json()
        for it in data.get("value", []):
            if "folder" in it:
                items.extend(list_drive_items_recursive(drive_id, headers, it["id"]))
            elif "file" in it:
                items.append(it)
        url = data.get("@odata.nextLink")
    return items

def parse_xlsx_to_json(filepath):
    wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
    sheets = {}
    for sname in wb.sheetnames:
        ws = wb[sname]
        rows = []
        for row in ws.iter_rows(values_only=True):
            if any(c is not None and str(c).strip() != "" for c in row):
                rows.append(["" if c is None else str(c) for c in row])
            if len(rows) >= 200:
                break
        if rows:
            # Normalize column count
            max_cols = max(len(r) for r in rows)
            max_cols = min(max_cols, 20)
            norm_rows = [r[:max_cols] + [""] * max(0, max_cols - len(r)) for r in rows]
            sheets[sname] = norm_rows
    wb.close()
    return sheets

def main():
    tok = SharePointReporter.obter_token_graph()
    headers = {"Authorization": f"Bearer {tok}"}

    docs_dir = os.path.join(PROJECT_ROOT, "docs")
    portal_dir = os.path.join(PROJECT_ROOT, "portal_web")
    sheets_dir = os.path.join(docs_dir, "assets", "sheets")
    os.makedirs(sheets_dir, exist_ok=True)

    authentic_sheets = {}
    master_path = os.path.join(PROJECT_ROOT, "config", "sharepoint_portal_master_data.json")
    with open(master_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    for drive_name, (drive_id, target_sub) in DRIVES.items():
        print(f"\n=== Syncing {drive_name} -> {target_sub} ===")
        items = list_drive_items_recursive(drive_id, headers)
        print(f"  Found {len(items)} files in SharePoint")

        dest_docs = os.path.join(docs_dir, target_sub)
        dest_portal = os.path.join(portal_dir, target_sub)
        os.makedirs(dest_docs, exist_ok=True)
        os.makedirs(dest_portal, exist_ok=True)

        # Map master_data items by name for webUrl updates
        md_items = master_data.get("drives", {}).get(drive_name, {}).get("items", [])
        md_by_name = {it.get("name"): it for it in md_items if it.get("name")}

        for it in items:
            fname = it.get("name", "")
            ext = os.path.splitext(fname)[1].lower()
            if target_sub.startswith("reports/") and ext != ".pdf":
                continue
            if target_sub == "sheets" and ext not in [".xlsx", ".xls", ".csv", ".pdf", ".docx"]:
                continue

            out_docs = os.path.join(dest_docs, fname)
            out_portal = os.path.join(dest_portal, fname)

            dl_url = it.get("@microsoft.graph.downloadUrl")
            if not os.path.exists(out_docs) or os.path.getsize(out_docs) == 0:
                if not dl_url:
                    r_meta = graph_get(f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{it['id']}", headers)
                    if r_meta.status_code == 200:
                        dl_url = r_meta.json().get("@microsoft.graph.downloadUrl")
                if dl_url:
                    r_dl = graph_get(dl_url, {})
                    if r_dl.status_code == 200:
                        with open(out_docs, "wb") as fw:
                            fw.write(r_dl.content)
                        with open(out_portal, "wb") as fw2:
                            fw2.write(r_dl.content)
                        print(f"  [DL] {fname} ({len(r_dl.content)} bytes)")
                    else:
                        print(f"  [ERR {r_dl.status_code}] {fname}")
            else:
                if not os.path.exists(out_portal):
                    with open(out_docs, "rb") as fr, open(out_portal, "wb") as fw2:
                        fw2.write(fr.read())

            # Update webUrl in master_data
            rel_url = f"{target_sub}/{fname}"
            if fname in md_by_name:
                md_by_name[fname]["webUrl"] = rel_url

            # Parse authentic xlsx
            if ext == ".xlsx" and os.path.exists(out_docs):
                try:
                    parsed = parse_xlsx_to_json(out_docs)
                    if parsed:
                        authentic_sheets[fname] = parsed
                except Exception as e:
                    print(f"  [XLSX PARSE ERR] {fname}: {e}")

    # Save authentic_sheets_data.json
    sheets_json_docs = os.path.join(docs_dir, "assets", "authentic_sheets_data.json")
    sheets_json_portal = os.path.join(portal_dir, "assets", "authentic_sheets_data.json")
    sheets_json_cfg = os.path.join(PROJECT_ROOT, "config", "authentic_sheets_data.json")
    for p in [sheets_json_docs, sheets_json_portal, sheets_json_cfg]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fw:
            json.dump(authentic_sheets, fw, ensure_ascii=False)

    with open(master_path, "w", encoding="utf-8") as fw:
        json.dump(master_data, fw, ensure_ascii=False, indent=2)

    print(f"\nDONE! Parsed {len(authentic_sheets)} authentic XLSX files.")

if __name__ == "__main__":
    main()
