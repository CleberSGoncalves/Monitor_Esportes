# -*- coding: utf-8 -*-
"""
Módulo de Sincronização em Paralelo com Google Sheets.
Permite espelhar automaticamente confrontos e eventos cadastrados ou sincronizados
com o SharePoint diretamente para a planilha Google Sheets via Apps Script Web App.

Endpoint Oficial:
https://script.google.com/macros/s/AKfycbxzWKi1dNiGUiF15Ysl_69Pe2dt2vUpe1UBQ9xadPenmnsH68VOk6W1ZMwhRQkRpkBX/exec
"""

from __future__ import annotations

import os
import json
import logging
import threading
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import requests

logger = logging.getLogger(__name__)

DEFAULT_GOOGLE_SHEETS_WEBHOOK = (
    "https://script.google.com/macros/s/AKfycbxzWKi1dNiGUiF15Ysl_69Pe2dt2vUpe1UBQ9xadPenmnsH68VOk6W1ZMwhRQkRpkBX/exec"
)

MONTH_NAMES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

def obter_google_sheets_webhook_url() -> str:
    """Recupera o webhook do Google Sheets a partir do config.xml ou do valor padrão."""
    try:
        from modules.reporte_eventos.storage_manager import carrega_config_xml
        cfg = carrega_config_xml()
        if cfg and cfg.get("google_sheets_webhook"):
            url = str(cfg.get("google_sheets_webhook")).strip()
            if url.startswith("http"):
                return url
    except Exception as e:
        logger.debug(f"[GoogleSheetsSync] Erro ao ler config.xml: {e}")
    return os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", DEFAULT_GOOGLE_SHEETS_WEBHOOK)

def formatar_data_para_google_sheets(data_val: Any) -> str:
    """Converte datas em formatos ISO (2026-11-25T12:00:00Z) ou similares para DD/MM/YYYY."""
    if not data_val:
        return ""
    d_str = str(data_val).strip()
    if "/" in d_str and len(d_str.split("/")) == 3:
        return d_str  # Já está em DD/MM/YYYY
    try:
        d_clean = d_str[:10]
        dt = datetime.strptime(d_clean, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return d_str

def mapear_pvid_por_canal(canal: str, pvid_existente: str = "") -> str:
    """Retorna PVID TV BOX sugerido caso não informado."""
    if pvid_existente and str(pvid_existente).strip():
        return str(pvid_existente).strip()
    c = str(canal or "").lower()
    if "cazé" in c or "caze" in c:
        return "CAZETV - PV3623"
    elif "prime" in c or "amazon" in c:
        return "Prime Video - PV3687"
    elif "netflix" in c:
        return "Netflix - PV3679"
    elif "sportv" in c:
        return "SporTV - PV3101"
    elif "premiere" in c:
        return "Premiere - PV3102"
    elif "tnt" in c:
        return "TNT - 316"
    return f"{canal or 'TV'} - PVBOX"

def converter_evento_para_schema_google_sheets(ev: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza um dicionário de evento (seja de SharePoint, CBF ou interno)
    para o formato das 11 colunas do Google Sheets.
    """
    # Partida
    partida = str(ev.get("Partida") or ev.get("partida") or "").strip()
    
    # Campeonato
    camp = str(ev.get("Campeonato") or ev.get("Title") or ev.get("campeonato") or "CBF - Brasileirão Série A").strip()
    
    # Data & Mês
    data_raw = ev.get("Data") or ev.get("data") or ""
    data_fmt = formatar_data_para_google_sheets(data_raw)
    
    mes_str = str(ev.get("Mês") or ev.get("M_x00ea_s") or ev.get("mes") or "").strip()
    if not mes_str and data_fmt and "/" in data_fmt:
        try:
            m_idx = int(data_fmt.split("/")[1]) - 1
            if 0 <= m_idx < 12:
                mes_str = MONTH_NAMES_PT[m_idx]
        except Exception:
            pass
    if not mes_str:
        mes_str = "Novembro"
        
    # Horário
    hora_str = str(ev.get("Horário") or ev.get("Hor_x00e1_rio") or ev.get("horario") or ev.get("hora") or "").strip()
    
    # Canal
    canal_raw = ev.get("Canal de Transmissão") or ev.get("Transmiss_x00e3_o") or ev.get("canal") or "Amazon Prime"
    if isinstance(canal_raw, list):
        canal_str = ", ".join(str(c) for c in canal_raw if str(c).strip())
    else:
        canal_str = str(canal_raw).strip()
        
    # Responsável
    resp = (
        ev.get("Responsavel gravação")
        or ev.get("BKP_x0020__x0028_Uso_x0020_Supor")
        or ev.get("responsavel")
        or "Cleber BL01 e Backup"
    )
    if isinstance(resp, list):
        resp = ", ".join(resp)
        
    # PVID
    pvid_raw = ev.get("PVID TV BOX") or ev.get("PVID") or ev.get("pvid") or ""
    pvid_str = mapear_pvid_por_canal(canal_str, pvid_raw)
    
    # Status
    status_str = ev.get("Status de Entrega") or ev.get("StatusdeEntrega") or ev.get("status") or "Pendente"
    
    # Programado
    prog_str = (
        ev.get("Programado")
        or ev.get("Programado_x0020_TV_x0020_BOX_x0")
        or ev.get("Programado_x0020_ATRIA_x0020_Pri")
        or ev.get("programado")
        or "NÃO"
    )

    return {
        "anexos": "",
        "mes": mes_str,
        "data": data_fmt,
        "horario": hora_str,
        "campeonato": camp,
        "partida": partida,
        "responsavel": str(resp),
        "canal": canal_str,
        "pvid": pvid_str,
        "status": status_str,
        "programado": prog_str
    }

def converter_tupla_para_schema_google_sheets(row: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
    """Converte uma linha (tuple) do Treeview da UI para o schema do Google Sheets."""
    if not row or len(row) < 7:
        return None
    camp = str(row[0]).strip()
    part = str(row[1]).strip()
    data_raw = str(row[2]).strip()
    hora = str(row[3]).strip()
    canal = str(row[6]).strip() if len(row) > 6 else "Amazon Prime"
    return converter_evento_para_schema_google_sheets({
        "Campeonato": camp,
        "Partida": part,
        "Data": data_raw,
        "Horário": hora,
        "Canal de Transmissão": canal
    })

def sync_events_to_google_sheets(
    events: List[Dict[str, Any]],
    webhook_url: Optional[str] = None,
    timeout: int = 25
) -> Dict[str, Any]:
    """
    Envia lista de eventos para o Google Sheets de forma síncrona com desduplicação no Apps Script.
    """
    if not events:
        return {"status": "skipped", "message": "Nenhum evento para enviar", "inseridos": 0}

    url = webhook_url or obter_google_sheets_webhook_url()
    if not url:
        return {"status": "error", "message": "URL do Web App do Google Sheets não configurada"}

    payload_events = []
    for ev in events:
        if isinstance(ev, dict):
            conv = converter_evento_para_schema_google_sheets(ev)
            if conv.get("partida"):
                payload_events.append(conv)

    if not payload_events:
        return {"status": "skipped", "message": "Nenhum evento válido após filtragem", "inseridos": 0}

    logger.info(f"[GoogleSheetsSync] Enviando {len(payload_events)} eventos para o Google Sheets...")
    try:
        resp = requests.post(
            url,
            json={"events": payload_events},
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        if resp.status_code == 200:
            res_data = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") or "{" in resp.text else {}
            logger.info(f"[GoogleSheetsSync] Sucesso! Resposta: {resp.text[:150]}")
            return {
                "status": "success",
                "http_status": 200,
                "total_processados": len(payload_events),
                "inseridos": res_data.get("inseridos", len(payload_events)),
                "raw_response": resp.text
            }
        else:
            logger.warning(f"[GoogleSheetsSync] Retorno inesperado HTTP {resp.status_code}: {resp.text[:150]}")
            return {
                "status": "http_error",
                "http_status": resp.status_code,
                "error": resp.text
            }
    except Exception as e:
        logger.error(f"[GoogleSheetsSync] Erro na comunicação com Google Sheets: {e}")
        return {"status": "error", "error": str(e)}

def sync_tuples_to_google_sheets(
    rows: List[Tuple[Any, ...]],
    webhook_url: Optional[str] = None,
    timeout: int = 25
) -> Dict[str, Any]:
    """Recebe linhas do Treeview e envia para o Google Sheets."""
    evs = []
    for r in rows:
        conv = converter_tupla_para_schema_google_sheets(r)
        if conv:
            evs.append(conv)
    return sync_events_to_google_sheets(evs, webhook_url=webhook_url, timeout=timeout)

def trigger_parallel_google_sheets_sync(
    events_or_tuples: List[Any],
    webhook_url: Optional[str] = None
) -> threading.Thread:
    """
    Dispara o espelhamento em paralelo para o Google Sheets em uma thread separada.
    Garante execução 100% não bloqueante (não trava a GUI nem o pipeline do SharePoint).
    """
    def _worker():
        try:
            if not events_or_tuples:
                return
            primeiro = events_or_tuples[0]
            if isinstance(primeiro, (tuple, list)):
                sync_tuples_to_google_sheets(events_or_tuples, webhook_url=webhook_url)
            else:
                sync_events_to_google_sheets(events_or_tuples, webhook_url=webhook_url)
        except Exception as e:
            logger.debug(f"[GoogleSheetsSync Thread] Erro durante disparo em segundo plano: {e}")

    t = threading.Thread(target=_worker, daemon=True, name="GoogleSheetsParallelSyncThread")
    t.start()
    return t
