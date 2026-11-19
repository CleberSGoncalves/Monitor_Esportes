"""
Módulo de Sincronização em Paralelo de Relatórios para o Portal Web (Google Sites / GitHub Pages).
Garante que todos os relatórios gerados pelo Monitor_Esportes (Futebol, YouTube e NBA)
sejam publicados simultaneamente no Microsoft SharePoint e no novo Portal Web.
"""

import os
import json
import uuid
import shutil
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PortalSyncManager:
    """
    Gerencia a esteira de reporte em paralelo para o novo site do Suporte Captação.
    """

    @classmethod
    def sync_report_to_portal(
        cls,
        pdf_path: str,
        drive_name: str,
        category: str,
        filename: Optional[str] = None,
        partida: str = "",
        campeonato: str = "",
        plataforma: str = "",
        confianca: str = "99.0%"
    ) -> bool:
        """
        Publica o PDF no repositório local do Portal Web (docs/reports/),
        atualiza o master data (sharepoint_portal_master_data.json)
        e recompila o portal para visualização imediata.
        """
        if not pdf_path or not os.path.exists(pdf_path):
            logger.warning(f"[PortalSync] PDF não encontrado para publicação no portal: {pdf_path}")
            return False

        try:
            target_filename = filename or os.path.basename(pdf_path)
            
            # 1. Copiar o PDF para docs/reports/<category>/ e portal_web/reports/<category>/
            docs_dest_dir = os.path.join(PROJECT_ROOT, "docs", "reports", category)
            portal_dest_dir = os.path.join(PROJECT_ROOT, "portal_web", "reports", category)
            os.makedirs(docs_dest_dir, exist_ok=True)
            os.makedirs(portal_dest_dir, exist_ok=True)

            docs_file_path = os.path.join(docs_dest_dir, target_filename)
            portal_file_path = os.path.join(portal_dest_dir, target_filename)

            shutil.copy2(pdf_path, docs_file_path)
            shutil.copy2(pdf_path, portal_file_path)

            file_size = os.path.getsize(pdf_path)
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Link web relativo servido pelo GitHub Pages / Portal
            relative_web_url = f"reports/{category}/{target_filename}"

            # 2. Atualizar config/sharepoint_portal_master_data.json
            master_data_path = os.path.join(PROJECT_ROOT, "config", "sharepoint_portal_master_data.json")
            if not os.path.exists(master_data_path):
                logger.error(f"[PortalSync] Arquivo master data não encontrado: {master_data_path}")
                return False

            with open(master_data_path, "r", encoding="utf-8") as f:
                master_data = json.load(f)

            drives = master_data.setdefault("drives", {})
            drive = drives.setdefault(drive_name, {
                "name": drive_name,
                "drive_id": f"DRIVE_{category.upper()}",
                "webUrl": f"https://sites.google.com/ibope.com/suportecaptacao/{drive_name}",
                "items_count": 0,
                "items": []
            })

            items = drive.setdefault("items", [])

            # Verificar se já existe item com mesmo nome
            existing_item = None
            for it in items:
                if it.get("name") == target_filename:
                    existing_item = it
                    break

            if existing_item:
                existing_item["size"] = file_size
                existing_item["lastModifiedDateTime"] = now_iso
                existing_item["webUrl"] = relative_web_url
                existing_item["lastModifiedBy"] = "Monitor_Esportes Auto-Audit"
            else:
                new_item = {
                    "id": f"PORTAL_{uuid.uuid4().hex[:12].upper()}",
                    "name": target_filename,
                    "type": "file",
                    "extension": "pdf",
                    "mime_type": "application/pdf",
                    "size": file_size,
                    "lastModifiedDateTime": now_iso,
                    "lastModifiedBy": "Monitor_Esportes Auto-Audit",
                    "webUrl": relative_web_url,
                    "childCount": None,
                    "meta": {
                        "partida": partida,
                        "campeonato": campeonato,
                        "plataforma": plataforma,
                        "confianca": confianca
                    }
                }
                # Inserir no topo para aparecer primeiro
                items.insert(0, new_item)

            drive["items_count"] = len(items)

            with open(master_data_path, "w", encoding="utf-8") as f:
                json.dump(master_data, f, ensure_ascii=False, indent=2)

            # 3. Recompilar portal_web e docs/index.html
            try:
                from scripts.build_portal_web import generate_portal
                generate_portal()
            except Exception as e_build:
                logger.warning(f"[PortalSync] Aviso ao recompilar portal web: {e_build}")

            logger.info(f"🚀 [PortalSync] Relatório '{target_filename}' publicado com sucesso no Portal Web ({drive_name})!")
            return True

        except Exception as e:
            logger.error(f"[PortalSync] Erro ao sincronizar relatório com portal web: {e}")
            return False
