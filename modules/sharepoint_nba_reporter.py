"""
Módulo de Sincronização de Relatórios da NBA com o SharePoint.
Gerencia o upload e a atualização estrita de metadados na biblioteca 'Relatorios_de_Jogos_NBA'
(ou fallback compatível com Relatorios_de_Jogos identificando Campeonato = NBA).
"""

import os
import sys
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter, SP_CONFIG

logger = logging.getLogger(__name__)

class SharePointNBAReporter:
    _cached_nba_drive_id = None

    @classmethod
    def get_nba_drive_id(cls, token: str, site_id: str) -> Optional[str]:
        """Localiza o Drive/Biblioteca 'Relatorios_de_Jogos_NBA' ou 'Relatorios_Auditoria_NBA'."""
        if cls._cached_nba_drive_id:
            return cls._cached_nba_drive_id

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url_drives = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        
        try:
            r = SharePointReporter.request_with_retry("GET", url_drives, headers=headers, timeout=15)
            drives = r.json().get("value", [])
            for d in drives:
                name_upper = (d.get("name") or "").upper()
                if "NBA" in name_upper:
                    cls._cached_nba_drive_id = d.get("id")
                    logger.info(f"[SharePoint NBA] Drive dedicado NBA localizado: {d.get('name')} ({cls._cached_nba_drive_id})")
                    return cls._cached_nba_drive_id
        except Exception as e:
            logger.warning(f"[SharePoint NBA] Falha ao listar drives para NBA: {e}")

        # Se ainda não existir a biblioteca dedicada NBA, utiliza a biblioteca oficial de auditoria
        fallback_drive = SharePointReporter._cached_drive_id
        logger.info(f"[SharePoint NBA] Usando drive padrão de auditoria para NBA: {fallback_drive}")
        return fallback_drive

    @classmethod
    def sync_nba_report(cls, pdf_path: str, game: Dict[str, Any], confianca: str = "99.0%") -> bool:
        """
        Envia o PDF de relatório da NBA para o SharePoint e sincroniza os metadados oficiais.
        """
        if not os.path.exists(pdf_path):
            logger.error(f"[SharePoint NBA] PDF não encontrado: {pdf_path}")
            return False

        try:
            token = SharePointReporter.obter_token_graph()
            site_id = SharePointReporter._cached_site_id
            drive_id = cls.get_nba_drive_id(token, site_id)

            if not drive_id:
                logger.error("[SharePoint NBA] Nenhum drive disponível para sincronização.")
                return False

            sp_filename = os.path.basename(pdf_path)
            upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{sp_filename}:/content"
            
            headers = {"Authorization": f"Bearer {token}"}
            put_headers = dict(headers)
            put_headers["Content-Type"] = "application/pdf"

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            r_up = SharePointReporter.request_with_retry("PUT", upload_url, headers=put_headers, data=pdf_bytes, timeout=60)
            if not r_up or r_up.status_code not in (200, 201):
                logger.error(f"[SharePoint NBA] Falha no upload: HTTP {r_up.status_code if r_up else 'None'}")
                return False

            item_id = r_up.json().get("id")
            if not item_id:
                return False

            # Normalização de Plataforma
            raw_plat = (game.get("platform") or "").upper()
            if "AMAZON" in raw_plat or "PRIME" in raw_plat:
                plat_norm = "Amazon Prime"
            elif "DISNEY" in raw_plat or "ESPN" in raw_plat:
                plat_norm = "Disney"
            else:
                plat_norm = "Outro"

            # Data ISO
            iso_utc = game.get("iso_utc") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            fields_payload = {
                "Title": sp_filename,
                "Partida": game.get("match_display", "Jogo NBA"),
                "Campeonato": "NBA",
                "Plataforma": plat_norm,
                "Data_Partida": iso_utc,
                "Confianca": confianca,
                "Auditado": True
            }

            fields_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{item_id}/listItem/fields"
            json_headers = dict(headers)
            json_headers["Content-Type"] = "application/json"

            r_fields = SharePointReporter.request_with_retry("PATCH", fields_url, headers=json_headers, json=fields_payload, timeout=20)
            if r_fields.status_code in (200, 201):
                logger.info(f"🎉 [SharePoint NBA] Relatório '{sp_filename}' sincronizado com sucesso!")
                return True
            else:
                logger.error(f"❌ [SharePoint NBA] Erro nos metadados ({r_fields.status_code}): {r_fields.text}")
                return False

        except Exception as e:
            logger.error(f"❌ [SharePoint NBA] Exceção na sincronização: {e}")
            return False
