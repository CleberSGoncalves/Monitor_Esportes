import sys
import os
import time
import json
import logging
from datetime import datetime, timezone
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SharePointListsMapper")

SITE_ID = "adgbl.sharepoint.com,a3e49747-9bb6-4c93-9930-dda26c8d1050,34c8fe55-2cfe-4efc-8ce0-2958fd775ee0"
SITE_URL = "https://adgbl.sharepoint.com/sites/suportecaptacao"
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "config", "sharepoint_real_lists_data.json")

SYSTEM_NOISE_COLS = {
    "_ColorTag", "_ComplianceFlags", "_ComplianceTag", "_ComplianceTagWrittenTime",
    "_ComplianceTagUserId", "_CommentCount", "_LikeCount", "_DisplayName",
    "_IsRecord", "_UIVersionString", "_CopySource", "_CheckinComment",
    "ComplianceAssetId", "DocIcon", "Edit", "LinkTitleNoMenu", "LinkTitle",
    "LinkFilenameNoMenu", "LinkFilename", "ItemChildCount", "FolderChildCount",
    "AppAuthor", "AppEditor", "ParentVersionString", "ParentLeafName",
    "FileSizeDisplay", "CheckoutUser"
}

SYSTEM_FIELDS_NOISE = {
    "@odata.etag", "_UIVersionString", "_ComplianceFlags", "_ComplianceTag",
    "_ComplianceTagWrittenTime", "_ComplianceTagUserId", "ItemChildCount",
    "FolderChildCount", "Edit", "LinkTitleNoMenu", "LinkTitle",
    "LinkFilenameNoMenu", "LinkFilename", "DocIcon", "AppAuthor", "AppEditor"
}

class SharePointListsMapper:
    def __init__(self):
        self.token = SharePointReporter.obter_token_graph()
        self.session = requests.Session()
        self._update_session_token(self.token)

    def _update_session_token(self, token: str):
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def request_with_retry(self, url: str, max_retries: int = 5) -> dict:
        for attempt in range(max_retries):
            try:
                # Delay preventivo entre requisições
                time.sleep(0.35)
                r = self.session.get(url, timeout=30)
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 429:
                    retry_after = int(r.headers.get("Retry-After", 5))
                    wait_time = max(retry_after + 2, 6)
                    logger.warning(f"[429 Throttled] Microsoft Graph rate limit. Aguardando {wait_time}s (tentativa {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                elif r.status_code == 401:
                    logger.warning("[401 Unauthorized] Renovando access token do Microsoft Graph...")
                    self.token = SharePointReporter.obter_token_graph()
                    self._update_session_token(self.token)
                    time.sleep(1)
                else:
                    logger.error(f"[HTTP {r.status_code}] Falha na URL {url}: {r.text[:200]}")
                    return {}
            except Exception as e:
                logger.warning(f"[Exception] Erro na requisição (tentativa {attempt+1}/{max_retries}): {e}")
                time.sleep(2)
        return {}

    def is_useful_column(self, col: dict) -> bool:
        name = col.get("name", "")
        if name in SYSTEM_NOISE_COLS:
            return False
        if name.startswith("_") and col.get("readOnly", True) and not col.get("choice"):
            return False
        return True

    def parse_column_metadata(self, col: dict) -> dict:
        col_type = "unknown"
        for t in ["text", "choice", "number", "dateTime", "boolean", "lookup", "currency", "calculated", "hyperlinkOrPicture"]:
            if t in col:
                col_type = t
                break
        
        info = {
            "name": col.get("name"),
            "displayName": col.get("displayName"),
            "type": col_type,
            "required": bool(col.get("required", False)),
            "readOnly": bool(col.get("readOnly", False)),
            "hidden": bool(col.get("hidden", False)),
            "description": col.get("description", "")
        }
        if "choice" in col and "choices" in col["choice"]:
            info["choices"] = col["choice"]["choices"]
        if "lookup" in col:
            info["lookup"] = {
                "listId": col["lookup"].get("listId"),
                "columnName": col["lookup"].get("columnName")
            }
        return info

    def clean_item_fields(self, fields: dict) -> dict:
        return {
            k: v for k, v in fields.items()
            if k not in SYSTEM_FIELDS_NOISE
        }

    def map_all_lists(self) -> dict:
        logger.info(f"Iniciando mapeamento de listas do SharePoint Site: {SITE_ID}")
        lists_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/lists"
        data_lists = self.request_with_retry(lists_url)
        all_lists_raw = data_lists.get("value", [])
        logger.info(f"Total de {len(all_lists_raw)} listas encontradas no site.")

        structured_lists = []
        summary = {}

        for idx, l in enumerate(all_lists_raw):
            list_id = l.get("id")
            name = l.get("name")
            display_name = l.get("displayName")
            description = l.get("description", "")
            web_url = l.get("webUrl", "")
            hidden = l.get("list", {}).get("hidden", False)
            template = l.get("list", {}).get("template", "genericList")

            logger.info(f"[{idx+1}/{len(all_lists_raw)}] Mapeando lista: '{display_name}' (name='{name}', id={list_id})...")

            # 1. Obter Colunas
            cols_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/lists/{list_id}/columns"
            cols_data = self.request_with_retry(cols_url)
            raw_cols = cols_data.get("value", [])
            filtered_cols = [
                self.parse_column_metadata(c)
                for c in raw_cols
                if self.is_useful_column(c)
            ]

            # 2. Obter Itens Reais ($expand=fields&$top=500)
            items_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/lists/{list_id}/items?$expand=fields&$top=500"
            items_data = self.request_with_retry(items_url)
            raw_items = items_data.get("value", [])
            has_next = bool("@odata.nextLink" in items_data)

            extracted_items = []
            for itm in raw_items:
                extracted_items.append({
                    "id": itm.get("id"),
                    "createdDateTime": itm.get("createdDateTime"),
                    "lastModifiedDateTime": itm.get("lastModifiedDateTime"),
                    "webUrl": itm.get("webUrl"),
                    "fields": self.clean_item_fields(itm.get("fields", {}))
                })

            list_obj = {
                "list_id": list_id,
                "name": name,
                "displayName": display_name,
                "description": description,
                "template": template,
                "hidden": hidden,
                "webUrl": web_url,
                "columns_count": len(filtered_cols),
                "columns": filtered_cols,
                "items_count": len(extracted_items),
                "has_more_items": has_next,
                "items": extracted_items
            }

            structured_lists.append(list_obj)
            summary[display_name] = {
                "name": name,
                "list_id": list_id,
                "template": template,
                "columns_count": len(filtered_cols),
                "items_count": len(extracted_items),
                "hidden": hidden
            }
            logger.info(f"   -> OK: {len(filtered_cols)} colunas úteis, {len(extracted_items)} itens capturados.")

        final_payload = {
            "site_id": SITE_ID,
            "site_url": SITE_URL,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "total_lists": len(structured_lists),
            "summary": summary,
            "lists": structured_lists
        }

        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(final_payload, f, ensure_ascii=False, indent=2)

        file_size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
        logger.info(f"Mapeamento concluído com sucesso! Arquivo salvo em: {OUTPUT_FILE} ({file_size_mb:.2f} MB)")
        return final_payload

if __name__ == "__main__":
    mapper = SharePointListsMapper()
    mapper.map_all_lists()
