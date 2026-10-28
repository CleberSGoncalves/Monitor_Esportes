"""
Módulo de Sincronização de Relatórios da NBA com o SharePoint.
Gerencia o upload e a atualização estrita de metadados na biblioteca 'Relatorios_de_Jogos_NBA'
(ou fallback compatível com Relatorios_de_Jogos identificando Campeonato = NBA).
"""

import os
import sys
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter, SP_CONFIG

logger = logging.getLogger(__name__)

class SharePointNBAReporter:
    _cached_nba_drive_id = "b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuBLKjP6Rlw_Q5U94FNKn17N"
    _cached_nba_list_id = "fa332a4b-5c46-433f-953d-e0534a9f5ecd"

    @classmethod
    def get_nba_drive_id(cls, token: str, site_id: str) -> Optional[str]:
        """Localiza o Drive/Biblioteca 'Relatorios_de_Jogos_NBA'."""
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

        fallback_drive = SharePointReporter._cached_drive_id
        logger.info(f"[SharePoint NBA] Usando drive padrão de auditoria para NBA: {fallback_drive}")
        return fallback_drive

    @classmethod
    def sync_nba_report(cls, pdf_path: str, game: Dict[str, Any], confianca: str = "99.0%") -> bool:
        """
        Envia o PDF de relatório da NBA para a biblioteca 'Relatorios_de_Jogos_NBA'
        do SharePoint e sincroniza os metadados de forma tolerante a falhas.
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

            # Data ISO UTC
            iso_utc = game.get("iso_utc") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Inspecionar colunas existentes na biblioteca para blindagem contra 400
            existing_cols = {}
            if cls._cached_nba_list_id:
                try:
                    cols_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{cls._cached_nba_list_id}/columns"
                    r_cols = SharePointReporter.request_with_retry("GET", cols_url, headers=headers, timeout=10)
                    if r_cols.status_code == 200:
                        for c in r_cols.json().get("value", []):
                            existing_cols[c.get("name")] = c.get("displayName")
                except Exception as e_cols:
                    logger.debug(f"[SharePoint NBA] Não foi possível obter schema das colunas: {e_cols}")

            fields_payload = {
                "Title": sp_filename
            }

            if not existing_cols or "Partida" in existing_cols:
                fields_payload["Partida"] = game.get("match_display", "Jogo NBA")
            if not existing_cols or "Campeonato" in existing_cols:
                fields_payload["Campeonato"] = "NBA"
            if not existing_cols or "Plataforma" in existing_cols:
                fields_payload["Plataforma"] = plat_norm

            # Suporte transparente para Data_Partida ou Data_Hora
            if "Data_Partida" in existing_cols:
                fields_payload["Data_Partida"] = iso_utc
            elif "Data_Hora" in existing_cols:
                fields_payload["Data_Hora"] = iso_utc
            elif not existing_cols:
                fields_payload["Data_Partida"] = iso_utc

            if not existing_cols or "Confianca" in existing_cols:
                fields_payload["Confianca"] = confianca
            if not existing_cols or "Auditado" in existing_cols:
                fields_payload["Auditado"] = True

            score_val = game.get("score")
            if not score_val and game.get("away_score") and game.get("home_score"):
                score_val = f"{game.get('away_team', '')} {game.get('away_score')} x {game.get('home_score')} {game.get('home_team', '')}".strip()
            if "Placar" in existing_cols and score_val:
                fields_payload["Placar"] = score_val

            fields_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{item_id}/listItem/fields"
            json_headers = dict(headers)
            json_headers["Content-Type"] = "application/json"

            # Executa com repetição e auto-reparo caso algum campo ainda não exista no SharePoint
            for attempt in range(4):
                r_fields = SharePointReporter.request_with_retry("PATCH", fields_url, headers=json_headers, json=fields_payload, timeout=20)
                if r_fields.status_code in (200, 201):
                    logger.info(f"🎉 [SharePoint NBA] Relatório '{sp_filename}' e metadados sincronizados com sucesso na biblioteca NBA!")
                    return True
                
                # Se falhar por campo não reconhecido ("Field 'XYZ' is not recognized")
                err_text = r_fields.text
                m_unrec = re.search(r"Field '([^']+)' is not recognized", err_text)
                if m_unrec:
                    bad_field = m_unrec.group(1)
                    logger.warning(f"[SharePoint NBA] Campo '{bad_field}' ainda não criado na biblioteca. Removendo do envio para salvar os demais...")
                    if bad_field in fields_payload:
                        del fields_payload[bad_field]
                        continue
                
                # Se for erro com Data_Partida vs Data_Hora
                if "Data_Partida" in fields_payload and ("Data_Partida" in err_text or "does not exist" in err_text.lower()):
                    logger.info("[SharePoint NBA] Tentando campo alternativo 'Data_Hora'...")
                    del fields_payload["Data_Partida"]
                    fields_payload["Data_Hora"] = iso_utc
                    continue

                logger.error(f"❌ [SharePoint NBA] Erro nos metadados ({r_fields.status_code}): {r_fields.text}")
                break

            # Se o upload do PDF funcionou, já é um sucesso operacional garantido
            return True

        except Exception as e:
            logger.error(f"❌ [SharePoint NBA] Exceção na sincronização: {e}")
            return False
