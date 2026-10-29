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

from modules.sharepoint_reporter import SharePointReporter, SP_CONFIG, SharePointAuthRequiredError

logger = logging.getLogger(__name__)

class SharePointNBAReporter:
    _cached_nba_drive_id = "b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuBLKjP6Rlw_Q5U94FNKn17N"
    _cached_nba_list_id = "fa332a4b-5c46-433f-953d-e0534a9f5ecd"
    _cached_existing_cols = {
        "Title": "Título",
        "Partida": "Partida",
        "Campeonato": "Campeonato",
        "Plataforma": "Plataforma",
        "Data_Hora": "Data_Hora",
        "Confianca": "Confianca",
        "Auditado": "Auditado",
        "Placar": "Placar"
    }

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
        do SharePoint e sincroniza os metadados de forma canônica (1 item único por jogo).
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

            away_tri = (game.get("away_tri") or "AWAY").upper()
            home_tri = (game.get("home_tri") or "HOME").upper()
            date_clean = game.get("date_clean") or datetime.now().strftime("%Y%m%d")
            sp_filename = f"Relatorio_NBA_{away_tri}_at_{home_tri}_{date_clean}.pdf"
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

            # Normalização de Plataforma estritamente alinhada com as Opções da Biblioteca:
            # ['Amazon Prime', 'Disney', 'Escolha 3', 'ESPN', 'NBA', 'YouTube', 'Caze TV', 'Outro']
            raw_plat = (game.get("platform") or "").upper()
            if "AMAZON" in raw_plat or "PRIME" in raw_plat:
                plat_norm = "Amazon Prime"
            elif "DISNEY" in raw_plat:
                plat_norm = "Disney"
            elif "ESPN" in raw_plat:
                plat_norm = "ESPN"
            elif "CAZE" in raw_plat:
                plat_norm = "Caze TV"
            elif "YOUTUBE" in raw_plat:
                plat_norm = "YouTube"
            elif "LEAGUE" in raw_plat or "NBA" in raw_plat:
                plat_norm = "NBA"
            else:
                plat_norm = "NBA"

            # Data ISO UTC
            iso_utc = game.get("iso_utc") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            is_fin = bool(game.get("is_finished"))
            if is_fin:
                is_audited = True
                conf_val = confianca
                score_val = game.get("score")
                if not score_val and game.get("away_score") and game.get("home_score"):
                    score_val = f"{game.get('away_team', '')} {game.get('away_score')} x {game.get('home_score')} {game.get('home_team', '')}".strip()
                if not score_val:
                    score_val = game.get("score_display", "Finalizado")
            else:
                is_audited = False
                conf_val = "Agendado"
                score_val = f"Agendado ({game.get('time_brt', '—')} BRT)"

            fields_payload = {
                "Title": sp_filename,
                "Partida": game.get("match_display", f"{away_tri} @ {home_tri}"),
                "Campeonato": "NBA",
                "Plataforma": plat_norm,
                "Data_Hora": iso_utc,
                "Confianca": conf_val,
                "Auditado": is_audited,
                "Placar": score_val
            }

            fields_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{item_id}/listItem/fields"
            json_headers = dict(headers)
            json_headers["Content-Type"] = "application/json"

            # Executa com repetição e auto-reparo caso algum campo ainda não exista no SharePoint
            for attempt in range(4):
                r_fields = SharePointReporter.request_with_retry("PATCH", fields_url, headers=json_headers, json=fields_payload, timeout=20)
                if r_fields.status_code in (200, 201):
                    logger.info(f"🎉 [SharePoint NBA] Relatório '{sp_filename}' e metadados sincronizados com sucesso na biblioteca NBA!")
                    return True
                
                err_text = r_fields.text
                m_unrec = re.search(r"Field '([^']+)' is not recognized", err_text)
                if m_unrec:
                    bad_field = m_unrec.group(1)
                    logger.warning(f"[SharePoint NBA] Removendo campo não reconhecido '{bad_field}' e tentando novamente...")
                    fields_payload.pop(bad_field, None)
                    continue
                else:
                    logger.warning(f"[SharePoint NBA] Upload concluído, mas falha ao gravar metadados (tentativa {attempt+1}): {r_fields.status_code} - {err_text[:200]}")
                    break

            return True

        except SharePointAuthRequiredError:
            raise
        except Exception as e:
            logger.error(f"[SharePoint NBA] Exceção ao sincronizar relatório NBA: {e}")
            return False
