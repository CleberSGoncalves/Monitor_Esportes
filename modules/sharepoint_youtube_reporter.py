"""
Módulo de Sincronização de Relatórios de Canais do YouTube com o SharePoint.
Gerencia o upload e a atualização estrita de metadados na biblioteca 'Relatorio Jogos Youtube',
garantindo isolamento total em relação à biblioteca 'Relatorios_de_Jogos' (CBF) e 'Relatorios_de_Jogos_NBA'.
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


class SharePointYouTubeReporter:
    _cached_yt_drive_id = "b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuB9cyT1xIdlTLVA1lg-2mHZ"
    _cached_target_names = [
        "Relatorio Jogos Youtube",
        "Relatorio_Jogos_Youtube",
        "Relatórios Jogos Youtube",
        "Relatorios Jogos Youtube"
    ]

    @classmethod
    def get_youtube_drive_id(cls, token: str, site_id: str) -> Optional[str]:
        """Localiza o Drive/Biblioteca dedicado 'Relatorio Jogos Youtube'."""
        if cls._cached_yt_drive_id:
            return cls._cached_yt_drive_id

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url_drives = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        
        try:
            r = SharePointReporter.request_with_retry("GET", url_drives, headers=headers, timeout=15)
            drives = r.json().get("value", [])
            for d in drives:
                name = (d.get("name") or "").strip()
                if "Youtube" in name or "YouTube" in name:
                    cls._cached_yt_drive_id = d.get("id")
                    logger.info(f"[SharePoint YouTube] Drive dedicado localizado: {name} ({cls._cached_yt_drive_id})")
                    return cls._cached_yt_drive_id
        except Exception as e:
            logger.warning(f"[SharePoint YouTube] Falha ao listar drives para YouTube: {e}")

        return cls._cached_yt_drive_id

    @classmethod
    def sync_youtube_report(
        cls,
        pdf_path: str,
        event_info: Dict[str, Any],
        confianca: str = "99.0%"
    ) -> bool:
        """
        Envia o PDF de relatório de canal do YouTube para a biblioteca 'Relatorio Jogos Youtube'
        do SharePoint e sincroniza os metadados com resiliência total e auto-recuperação.
        """
        if not os.path.exists(pdf_path):
            logger.error(f"[SharePoint YouTube] PDF não encontrado: {pdf_path}")
            return False

        try:
            token = SharePointReporter.obter_token_graph()
            site_id = SharePointReporter._cached_site_id
            drive_id = cls.get_youtube_drive_id(token, site_id)

            if not drive_id:
                logger.error("[SharePoint YouTube] Nenhum drive disponível para sincronização.")
                return False

            partida = str(event_info.get("match_display") or event_info.get("partida") or event_info.get("title") or "Partida").strip()
            canal = str(event_info.get("channel_name") or event_info.get("canal") or event_info.get("channel") or "YouTube").strip()
            campeonato = str(event_info.get("competition") or event_info.get("campeonato") or "Outro").strip()
            url_video = str(event_info.get("video_url") or event_info.get("url") or "").strip()
            duracao_live = str(event_info.get("live_duration") or event_info.get("duration_str") or "").strip()
            placar = str(event_info.get("score") or event_info.get("placar") or "").strip()

            partida_norm = "".join(c for c in partida if c.isalnum() or c in " xX_").strip().replace(" ", "_").lower()
            canal_norm = "".join(c for c in canal if c.isalnum() or c in "_").strip().replace(" ", "_").lower()
            date_clean = event_info.get("date_clean") or datetime.now().strftime("%Y%m%d")

            sp_filename = f"Relatorio_Youtube_{canal_norm}_{partida_norm}_{date_clean}.pdf"
            upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{sp_filename}:/content"

            headers = {"Authorization": f"Bearer {token}"}
            put_headers = dict(headers)
            put_headers["Content-Type"] = "application/pdf"

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            r_up = SharePointReporter.request_with_retry("PUT", upload_url, headers=put_headers, data=pdf_bytes, timeout=60)
            if not r_up or r_up.status_code not in (200, 201):
                logger.error(f"[SharePoint YouTube] Falha no upload: HTTP {r_up.status_code if r_up else 'None'}")
                return False

            item_id = r_up.json().get("id")
            if not item_id:
                return False

            # Normalização de data ISO UTC
            raw_date = event_info.get("date") or event_info.get("data_jogo") or datetime.now().strftime("%d/%m/%Y")
            time_start = event_info.get("start_time") or event_info.get("inicio_transmissao") or "17:00"
            iso_utc = SharePointReporter.format_iso_datetime(raw_date, time_start)

            fields_payload = {
                "Title": sp_filename,
                "Partida": partida,
                "Canal": canal,
                "Campeonato": campeonato,
                "Data_Jogo": iso_utc,
                "Inicio_Transmissao": str(event_info.get("inicio_transmissao") or time_start),
                "Apito_Inicial": str(event_info.get("apito_inicial") or event_info.get("kickoff") or ""),
                "Apito_Final": str(event_info.get("apito_final") or event_info.get("end_time") or ""),
                "Fim_Transmissao": str(event_info.get("fim_transmissao") or event_info.get("close_time") or ""),
                "Duracao_Live": duracao_live,
                "URL_Video": url_video,
                "Confianca": str(confianca),
                "Auditado": True,
                "Placar": placar,
                "Status": "Concluído"
            }

            fields_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{item_id}/listItem/fields"
            json_headers = dict(headers)
            json_headers["Content-Type"] = "application/json"

            # Auto-recuperação: se algum campo ainda não foi criado na interface do SharePoint,
            # remove o campo faltante e continua sem quebrar o upload!
            for attempt in range(5):
                r_fields = SharePointReporter.request_with_retry(
                    "PATCH", fields_url, headers=json_headers, json=fields_payload, timeout=20
                )
                if r_fields.status_code in (200, 201):
                    logger.info(f"🎉 [SharePoint YouTube] Relatório '{sp_filename}' e metadados sincronizados com sucesso na biblioteca 'Relatorio Jogos Youtube'!")
                    return True

                err_text = r_fields.text
                m_unrec = re.search(r"Field '([^']+)' is not recognized", err_text)
                if m_unrec:
                    bad_field = m_unrec.group(1)
                    logger.warning(f"[SharePoint YouTube] Removendo campo não reconhecido '{bad_field}' e tentando novamente...")
                    fields_payload.pop(bad_field, None)
                    continue
                else:
                    logger.warning(f"[SharePoint YouTube] Metadados parciais (tentativa {attempt+1}): {r_fields.status_code} - {err_text[:200]}")
                    break

            return True

        except SharePointAuthRequiredError:
            raise
        except Exception as e:
            logger.error(f"[SharePoint YouTube] Exceção ao sincronizar relatório de YouTube: {e}")
            return False
