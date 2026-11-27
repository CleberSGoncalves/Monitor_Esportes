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
from typing import Dict, Any, Optional, List

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
    def sync_nba_report(cls, pdf_path: str, game: Dict[str, Any], confianca: str = "99.0%", defer_portal_push: bool = False) -> bool:
        """
        Envia o PDF de relatório da NBA para a biblioteca 'Relatorios_de_Jogos_NBA'
        do SharePoint e sincroniza simultaneamente com o Google Sites / Portal Web.
        A publicação no Google Sites ocorre mesmo em caso de indisponibilidade do SharePoint.
        """
        if not os.path.exists(pdf_path):
            logger.error(f"[SharePoint NBA] PDF não encontrado: {pdf_path}")
            return False

        away_tri = (game.get("away_tri") or "AWAY").upper()
        home_tri = (game.get("home_tri") or "HOME").upper()
        date_clean = game.get("date_clean") or datetime.now().strftime("%Y%m%d")
        sp_filename = f"Relatorio_NBA_{away_tri}_at_{home_tri}_{date_clean}.pdf"

        # Normalização de Plataforma estritamente alinhada com as Opções da Biblioteca
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

        iso_utc = game.get("iso_utc") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        match_display = game.get("match_display") or f"{away_tri} @ {home_tri}"

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

        sp_ok = False
        auth_err = None
        try:
            token = SharePointReporter.obter_token_graph()
            site_id = SharePointReporter._cached_site_id
            drive_id = cls.get_nba_drive_id(token, site_id)

            if not drive_id:
                logger.error("[SharePoint NBA] Nenhum drive disponível para sincronização.")
            else:
                upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{sp_filename}:/content"
                headers = {"Authorization": f"Bearer {token}"}
                put_headers = dict(headers)
                put_headers["Content-Type"] = "application/pdf"

                # Limpeza preventiva de duplicatas legadas com nomenclaturas antigas (pula em lote agendado para poupar Graph API)
                if not defer_portal_push:
                    try:
                        children_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children?$select=id,name"
                        r_children = SharePointReporter.request_with_retry("GET", children_url, headers=headers, timeout=15)
                        if r_children and r_children.status_code == 200:
                            items = r_children.json().get("value", [])
                            match_sub = f"{away_tri}_at_{home_tri}_{date_clean}".lower()
                            for it in items:
                                it_name = it.get("name", "").lower()
                                it_id = it.get("id")
                                if match_sub in it_name and it.get("name") != sp_filename:
                                    logger.info(f"[SharePoint NBA] Removendo arquivo duplicado legado: {it.get('name')}")
                                    del_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{it_id}"
                                    SharePointReporter.request_with_retry("DELETE", del_url, headers=headers, timeout=15)
                    except Exception as e_dup:
                        logger.debug(f"[SharePoint NBA] Checagem de duplicatas: {e_dup}")

                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                r_up = SharePointReporter.request_with_retry("PUT", upload_url, headers=put_headers, data=pdf_bytes, timeout=60)
                if not r_up or r_up.status_code not in (200, 201):
                    logger.error(f"[SharePoint NBA] Falha no upload: HTTP {r_up.status_code if r_up else 'None'}")
                else:
                    item_id = r_up.json().get("id")
                    if item_id:
                        fields_payload = {
                            "Title": sp_filename,
                            "Partida": match_display,
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

                        for attempt in range(4):
                            r_fields = SharePointReporter.request_with_retry("PATCH", fields_url, headers=json_headers, json=fields_payload, timeout=20)
                            if r_fields.status_code in (200, 201):
                                logger.info(f"🎉 [SharePoint NBA] Relatório '{sp_filename}' e metadados sincronizados com sucesso na biblioteca NBA!")
                                sp_ok = True
                                break
                            err_text = r_fields.text
                            m_unrec = re.search(r"Field '([^']+)' is not recognized", err_text)
                            if m_unrec:
                                bad_field = m_unrec.group(1)
                                logger.warning(f"[SharePoint NBA] Removendo campo não reconhecido '{bad_field}' e tentando novamente...")
                                fields_payload.pop(bad_field, None)
                                continue
                            else:
                                logger.warning(f"[SharePoint NBA] Upload concluído, mas falha ao gravar metadados (tentativa {attempt+1}): {r_fields.status_code} - {err_text[:200]}")
                                sp_ok = True
                                break
        except SharePointAuthRequiredError as e_auth:
            auth_err = e_auth
        except Exception as e:
            logger.error(f"[SharePoint NBA] Exceção ao sincronizar relatório NBA no SharePoint (Google Sites seguirá normalmente): {e}")

        # Publicação obrigatória em paralelo no Google Sites / Portal Web (100% independente do SharePoint)
        portal_ok = False
        try:
            from modules.portal_sync import PortalSyncManager, iso_utc_to_brt_str
            # Data/Hora real do jogo em BRT (idêntica ao SharePoint)
            if game.get("date_display") and game.get("time_brt") and ":" in str(game.get("time_brt")):
                data_hora_brt = f"{game['date_display']} {game['time_brt']}"
            else:
                data_hora_brt = iso_utc_to_brt_str(iso_utc)

            portal_ok = PortalSyncManager.sync_report_to_portal(
                pdf_path=pdf_path,
                drive_name="Relatorios_de_Jogos_NBA",
                category="nba",
                filename=sp_filename,
                partida=match_display,
                campeonato="NBA",
                plataforma=plat_norm,
                confianca=conf_val,
                data_hora=data_hora_brt,
                auditado=is_audited,
                placar=score_val,
                defer_github_push=defer_portal_push
            )
            if portal_ok:
                logger.info(f"🌐 [Portal Web / Google Sites] Relatório '{sp_filename}' publicado com sucesso (NBA)!")
        except Exception as e_portal:
            logger.warning(f"[PortalSync] Erro ao sincronizar NBA com Google Sites: {e_portal}")

        if auth_err and not portal_ok:
            raise auth_err
        return bool(sp_ok or portal_ok)

    @classmethod
    def sync_all_scheduled_games(cls, games: List[Dict[str, Any]], max_future_games: int = 60) -> int:
        """
        Sincroniza antecipadamente os jogos agendados da NBA no SharePoint e no Google Sites.
        Usa publicação em lote atômica (1 único commit no GitHub) para todos os jogos futuros.
        """
        from modules.nba_report_generator import NBAReportGenerator
        from modules.portal_sync import PortalSyncManager

        synced_count = 0
        scheduled_games = [g for g in games if not g.get("is_finished")]

        for g in scheduled_games[:max_future_games]:
            try:
                sheet_pdf = NBAReportGenerator.generate_schedule_sheet(g)
                if sheet_pdf and os.path.exists(sheet_pdf):
                    ok = cls.sync_nba_report(sheet_pdf, g, confianca="Agendado", defer_portal_push=True)
                    if ok:
                        synced_count += 1
                        logger.info(f"[SharePoint & Portal NBA] Jogo agendado sincronizado: {g.get('match_display')} ({g.get('date_display')})")
            except Exception as e_s:
                logger.warning(f"[SharePoint NBA] Falha ao sincronizar agenda de {g.get('match_display')}: {e_s}")
                continue

        if synced_count > 0:
            try:
                batch_ok = PortalSyncManager.flush_github_batch("nba")
                logger.info(f"🌐 [Portal Web / Google Sites] Lote de {synced_count} jogos agendados da NBA publicado: {'OK' if batch_ok else 'PENDENTE'}")
            except Exception as e_flush:
                logger.warning(f"[PortalSync] Erro ao publicar lote NBA no Google Sites: {e_flush}")

        return synced_count
