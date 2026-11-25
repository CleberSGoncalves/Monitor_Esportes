"""
Módulo de Sincronização em Paralelo de Relatórios para o Portal Web (Google Sites / GitHub Pages).
Garante que todos os relatórios gerados pelo Monitor_Esportes (Futebol, YouTube e NBA)
sejam publicados simultaneamente no Microsoft SharePoint e no novo Portal Web.
"""

import os
import sys
import json
import uuid
import shutil
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_project_root() -> str:
    """Retorna o diretório raiz do projeto mesmo quando executado empacotado via PyInstaller."""
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        if os.path.basename(exe_dir).lower() == "dist":
            return os.path.dirname(exe_dir)
        if os.path.exists(os.path.join(exe_dir, "config")):
            return exe_dir
        parent = os.path.dirname(exe_dir)
        if os.path.exists(os.path.join(parent, "config")):
            return parent
        return exe_dir
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PROJECT_ROOT = get_project_root()


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
        confianca: str = "99.0%",
        data_hora: Optional[str] = None,
        auditado: bool = True,
        placar: Optional[str] = None,
        canal: Optional[str] = None
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
            project_root = get_project_root()
            
            # 1. Copiar o PDF para docs/reports/<category>/ e portal_web/reports/<category>/
            docs_dest_dir = os.path.join(project_root, "docs", "reports", category)
            portal_dest_dir = os.path.join(project_root, "portal_web", "reports", category)
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
            config_dir = os.path.join(project_root, "config")
            os.makedirs(config_dir, exist_ok=True)
            master_data_path = os.path.join(config_dir, "sharepoint_portal_master_data.json")
            
            # Auto-bootstrap resiliente para ambiente compilado (PyInstaller) e novas instalações
            if not os.path.exists(master_data_path):
                meipass = getattr(sys, "_MEIPASS", None)
                if meipass:
                    bundled_master = os.path.join(meipass, "config", "sharepoint_portal_master_data.json")
                    if os.path.exists(bundled_master):
                        try:
                            shutil.copy2(bundled_master, master_data_path)
                            logger.info(f"[PortalSync] Master data inicializado a partir do bundle PyInstaller: {master_data_path}")
                        except Exception as e_copy:
                            logger.warning(f"[PortalSync] Falha ao copiar master data do _MEIPASS: {e_copy}")
            
            if not os.path.exists(master_data_path):
                try:
                    initial_data = {
                        "last_sync": datetime.now(timezone.utc).isoformat(),
                        "drives": {},
                        "lists": {}
                    }
                    with open(master_data_path, "w", encoding="utf-8") as f_init:
                        json.dump(initial_data, f_init, ensure_ascii=False, indent=2)
                    logger.info(f"[PortalSync] Master data base criado com sucesso: {master_data_path}")
                except Exception as e_create:
                    logger.error(f"[PortalSync] Erro ao criar master data base em {master_data_path}: {e_create}")
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

            now_dt_str = data_hora or datetime.now().strftime("%d/%m/%Y %H:%M")
            fields_data = {
                "Data_Hora": now_dt_str,
                "Data_Jogo": now_dt_str,
                "Campeonato": campeonato or "Brasileiro Serie A",
                "Partida": partida or target_filename,
                "Plataforma": plataforma or canal or "Caze TV",
                "Canal": canal or plataforma or "Caze TV",
                "Confiança": confianca or "99.0%",
                "Auditado": auditado,
                "Placar": placar or "",
                # Aliases lowercase para compatibilidade retroativa
                "partida": partida or target_filename,
                "campeonato": campeonato or "Brasileiro Serie A",
                "plataforma": plataforma or canal or "Caze TV",
                "canal": canal or plataforma or "Caze TV",
                "confianca": confianca or "99.0%"
            }

            if existing_item:
                existing_item["size"] = file_size
                existing_item["lastModifiedDateTime"] = now_iso
                existing_item["webUrl"] = relative_web_url
                existing_item["lastModifiedBy"] = "Monitor_Esportes Auto-Audit"
                existing_item["fields"] = fields_data
                existing_item["meta"] = fields_data
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
                    "fields": fields_data,
                    "meta": fields_data
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
