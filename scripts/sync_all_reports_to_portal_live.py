"""
Sincroniza 1:1 todas as 3 bibliotecas oficiais de relatórios do SharePoint
('Relatorios_de_Jogos', 'Relatorio Jogos Youtube', 'Relatorios_de_Jogos_NBA')
para o repositório do Portal Web / Google Sites:
  - Baixa todos os PDFs novos ou atualizados para docs/reports/<cat>/ e portal_web/reports/<cat>/
  - Gera os 3 índices ao vivo: docs/reports/index_<cat>.json e portal_web/reports/index_<cat>.json
  - Atualiza config/sharepoint_portal_master_data.json (drives + lists) com 100% de fidelidade
"""

import os
import sys
import json
import shutil
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter
from modules.sharepoint_youtube_reporter import SharePointYouTubeReporter
from modules.sharepoint_nba_reporter import SharePointNBAReporter
from modules.portal_sync import PortalSyncManager, iso_utc_to_brt_str, _parse_item_sort_ts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_all_reports_live")

LIBRARIES = [
    ("Relatorios_de_Jogos", "futebol", SharePointReporter._cached_drive_id),
    ("Relatorio Jogos Youtube", "youtube", SharePointYouTubeReporter._cached_yt_drive_id),
    ("Relatorios_de_Jogos_NBA", "nba", SharePointNBAReporter._cached_nba_drive_id),
]


def download_sp_pdf(it: Dict[str, Any], site_id: str, drive_id: str, headers: Dict[str, str], dest_path: str) -> bool:
    dl_url = it.get("@microsoft.graph.downloadUrl")
    try:
        if dl_url:
            r = requests.get(dl_url, timeout=60)
            if r.status_code == 200 and len(r.content) > 500:
                with open(dest_path, "wb") as f:
                    f.write(r.content)
                return True
        item_id = it.get("id")
        content_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{item_id}/content"
        r2 = SharePointReporter.request_with_retry("GET", content_url, headers=headers, timeout=60)
        if r2 and r2.status_code == 200 and len(r2.content) > 500:
            with open(dest_path, "wb") as f:
                f.write(r2.content)
            return True
    except Exception as e:
        logger.warning(f"Falha ao baixar '{it.get('name')}': {e}")
    return False


def sync_all_three_libraries() -> Dict[str, Any]:
    token = SharePointReporter.obter_token_graph()
    site_id = SharePointReporter._cached_site_id
    headers = {"Authorization": f"Bearer {token}"}

    master_path = os.path.join(PROJECT_ROOT, "config", "sharepoint_portal_master_data.json")
    with open(master_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    summary = {}
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for drive_name, category, drive_id in LIBRARIES:
        logger.info(f"=== Sincronizando '{drive_name}' (categoria: {category}) ===")
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children?$top=999&$expand=listItem($expand=fields)"
        raw_items: List[Dict[str, Any]] = []
        while url:
            r = SharePointReporter.request_with_retry("GET", url, headers=headers, timeout=30).json()
            raw_items.extend(r.get("value", []))
            url = r.get("@odata.nextLink")

        docs_dir = os.path.join(PROJECT_ROOT, "docs", "reports", category)
        portal_dir = os.path.join(PROJECT_ROOT, "portal_web", "reports", category)
        os.makedirs(docs_dir, exist_ok=True)
        os.makedirs(portal_dir, exist_ok=True)

        clean_items: List[Dict[str, Any]] = []
        list_items: List[Dict[str, Any]] = []
        downloaded = 0
        reused = 0
        skipped = 0

        for it in raw_items:
            name = (it.get("name") or "").strip()
            if not name.lower().endswith(".pdf"):
                skipped += 1
                continue
            sp_size = int(it.get("size") or 0)
            if sp_size < 1000:
                logger.warning(f"  Ignorando arquivo corrompido/mock (<1KB): {name} ({sp_size} bytes)")
                skipped += 1
                continue

            docs_file = os.path.join(docs_dir, name)
            portal_file = os.path.join(portal_dir, name)

            need_download = True
            if os.path.exists(docs_file) and os.path.getsize(docs_file) == sp_size:
                need_download = False
                reused += 1
                if not os.path.exists(portal_file) or os.path.getsize(portal_file) != sp_size:
                    shutil.copy2(docs_file, portal_file)
            elif os.path.exists(portal_file) and os.path.getsize(portal_file) == sp_size:
                need_download = False
                reused += 1
                shutil.copy2(portal_file, docs_file)

            if need_download:
                ok_dl = download_sp_pdf(it, site_id, drive_id, headers, docs_file)
                if ok_dl:
                    shutil.copy2(docs_file, portal_file)
                    downloaded += 1
                else:
                    # Fallback: se já existir arquivo válido local > 1KB, mantém
                    if os.path.exists(docs_file) and os.path.getsize(docs_file) >= 1000:
                        reused += 1
                    else:
                        logger.error(f"  Não foi possível obter PDF '{name}'. Pulando item para evitar 404.")
                        skipped += 1
                        continue

            final_size = os.path.getsize(docs_file)
            f_sp = (it.get("listItem") or {}).get("fields") or {}
            lm_iso = it.get("lastModifiedDateTime") or now_iso
            lm_by = ((it.get("lastModifiedBy") or {}).get("user") or {}).get("displayName") or ((it.get("lastModifiedBy") or {}).get("application") or {}).get("displayName") or "SharePoint App"
            cr_by = ((it.get("createdBy") or {}).get("user") or {}).get("displayName") or ((it.get("createdBy") or {}).get("application") or {}).get("displayName") or "svc.captacao"

            if category == "futebol":
                raw_dt = f_sp.get("Data_Partida") or f_sp.get("Data_Hora") or lm_iso
                partida = f_sp.get("Partida") or name.replace(".pdf", "")
                camp = f_sp.get("Campeonato") or "Brasileiro Serie A"
                plat = f_sp.get("Plataforma") or "Amazon Prime"
                canal = plat
                conf = f_sp.get("Confianca") or f_sp.get("Confiança") or "99.0%"
                audit = bool(f_sp.get("Auditado", True))
                placar = f_sp.get("Placar") or ""
            elif category == "youtube":
                raw_dt = f_sp.get("Data_Jogo") or f_sp.get("Data_Partida") or f_sp.get("Data_Hora") or lm_iso
                partida = f_sp.get("Partida") or name.replace(".pdf", "")
                camp = f_sp.get("Campeonato") or "Copa do Brasil"
                canal = f_sp.get("Canal") or f_sp.get("Plataforma") or "Gaúcha"
                plat = canal
                conf = f_sp.get("Placar") or f_sp.get("Confianca") or f_sp.get("Confiança") or "99.0%"
                audit = bool(f_sp.get("Auditado", True))
                placar = conf
            else:  # nba
                raw_dt = f_sp.get("Data_Hora") or f_sp.get("Data_Jogo") or lm_iso
                partida = f_sp.get("Partida") or name.replace(".pdf", "")
                camp = f_sp.get("Campeonato") or "NBA"
                plat = f_sp.get("Plataforma") or "NBA"
                canal = plat
                conf = f_sp.get("Confianca") or f_sp.get("Confiança") or "Agendado"
                audit = bool(f_sp.get("Auditado", False))
                placar = f_sp.get("Placar") or ("Homologado Oficial" if audit else "Agendado")

            item_obj = PortalSyncManager._build_drive_item(
                target_filename=name,
                category=category,
                file_size=final_size,
                now_iso=lm_iso,
                partida=partida,
                campeonato=camp,
                plataforma=plat,
                confianca=conf,
                data_hora=raw_dt,
                auditado=audit,
                placar=placar,
                canal=canal,
                item_id=it.get("id"),
                modified_by=lm_by,
                created_by=cr_by,
            )
            clean_items.append(item_obj)

            f_built = item_obj["fields"]
            list_items.append({
                "Data_Hora": f_built["Data_Hora"],
                "Data_Partida": f_built["Data_Hora"],
                "Data_Jogo": f_built["Data_Jogo"],
                "Campeonato": f_built["Campeonato"],
                "Partida": f_built["Partida"],
                "Plataforma": f_built["Plataforma"],
                "Canal": f_built["Canal"],
                "Confianca": f_built["Confiança"],
                "Confiança": f_built["Confiança"],
                "Placar": f_built["Placar"],
                "Auditado": f_built["Auditado"],
                "Modified": lm_iso,
                "Created": it.get("createdDateTime") or lm_iso,
                "CriadoPor": cr_by,
                "ModificadoPor": lm_by,
                "Title": name,
                "FileLeafRef": name,
                "pdfUrl": item_obj["webUrl"],
                "webUrl": item_obj["webUrl"],
            })

        clean_items.sort(key=_parse_item_sort_ts, reverse=True)
        list_items.sort(key=lambda x: _parse_item_sort_ts({"fields": x, "lastModifiedDateTime": x.get("Modified")}), reverse=True)

        # Salvar índices leves em docs/reports/ e portal_web/reports/
        PortalSyncManager._save_local_index(PROJECT_ROOT, category, drive_name, clean_items)

        # Atualizar master_data
        drives = master_data.setdefault("drives", {})
        drv = drives.setdefault(drive_name, {"name": drive_name, "drive_id": drive_id})
        drv["items"] = clean_items
        drv["items_count"] = len(clean_items)

        lists_d = master_data.setdefault("lists", {})
        if drive_name in lists_d and isinstance(lists_d[drive_name], dict):
            lists_d[drive_name]["items"] = list_items
        else:
            lists_d[drive_name] = {
                "name": drive_name,
                "displayName": drive_name,
                "columns": [],
                "items": list_items,
            }

        top_dt = clean_items[0]["fields"]["Data_Hora"] if clean_items else "-"
        top_match = clean_items[0]["fields"]["Partida"] if clean_items else "-"
        logger.info(
            f"✅ '{drive_name}': {len(clean_items)} itens sincronizados "
            f"(baixados: {downloaded}, reaproveitados: {reused}, pulados: {skipped}) | Topo: {top_dt} - {top_match}"
        )
        summary[drive_name] = {
            "total": len(clean_items),
            "downloaded": downloaded,
            "reused": reused,
            "skipped": skipped,
            "top": f"{top_dt} | {top_match}",
        }

    master_data["last_sync"] = now_iso
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 Master data salvo com sucesso em {master_path}")
    return summary


if __name__ == "__main__":
    res = sync_all_three_libraries()
    print(json.dumps(res, ensure_ascii=False, indent=2))
