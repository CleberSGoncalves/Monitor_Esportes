# -*- coding: utf-8 -*-
"""
INSPETOR HEADLESS DE ALTERAÇÕES & MOTOR DE SINCRONIZAÇÃO SHAREPOINT -> GOOGLE
Monitor_Esportes - Central Autônoma Suporte Captação

Executa em segundo plano (Headless) monitorando o Microsoft SharePoint
(todas as 46 listas e 21 bibliotecas de documentos).
Quando qualquer operador ou gestor atualiza, insere ou remove itens no SharePoint,
o inspetor detecta a modificação via sensor leve de metadados, extrai as alterações
incrementais e reflete de forma idêntica no ecossistema Google (Portal Web,
Google Sheets, JSONs mestres e alertas opcionais no Google Chat).
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("SharePointInspectorSync")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def get_project_root() -> str:
    """Retorna a raiz do projeto de forma dinâmica (suporta PyInstaller)."""
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
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter

ALL_LISTS_MAP = {
    "Acesso Remote Control - America Central": "16cdc917-70ce-4477-af69-30e6405e3294",
    "Acesso Remoto": "612b4399-d3b2-40a0-821c-5473e8b8c6b4",
    "Analise de Dados": "d58990bf-6ef2-420f-b8fb-e00a01c3c5c8",
    "Análise de Notificações": "4875375f-8be1-491f-9d13-c6fd30760baf",
    "Avaliação Técnica de Fornecedores": "f22b1d47-0fcf-4191-8d7a-46f6d6dbfe73",
    "Cadastro - Hosts": "f61d5727-9464-4d1e-9deb-133741ec64ee",
    "Cidades": "95057727-55a9-4c78-989e-e82fc4197b07",
    "Configurações de Rede do CS": "70dcceaa-be2f-4f2d-8b44-78d93cb56a72",
    "Confirmação de Falhas Suporte Captação": "3cdaadd3-cdc0-4b15-a389-98919be04da1",
    "Contato Técnico de Hospedeiros": "9f02aa6a-fb0c-4d6c-a2f6-f80708bbadac",
    "Contatos de Antenistas": "439bd00c-bf8a-4e40-ab5e-ec539ca4cb5e",
    "Contatos do Suporte Captação": "696a3406-3ae4-436e-808f-5c3eb4b3f80a",
    "Controle de contratos parceiros": "2ca95d72-da5b-4ae6-88d9-8060649b880c",
    "Documentos": "e6769e9f-0ad8-40ef-8b19-20c9e5f87b7e",
    "Documentos Técnicos": "8f33d954-473c-47d1-9f7a-90879d99a25c",
    "Escala de trabalho": "bfc20c52-eb79-4638-b249-71020125d50d",
    "Eventos": "4842641f-de4f-463e-9682-417c1be09ffe",
    "Extensões de Modelo da Web": "501d906f-64a6-401b-9a90-f6e2c82da5fd",
    "Ficha de Capacitação": "27e2ab94-d5aa-4539-af1e-1e0fe9a644f1",
    "Links de Internet dos Parceiros": "ba4dbfea-3224-4e2f-bbbd-5fc13d8abee2",
    "LogosEmissoras": "ba8b9c74-98ed-4e5f-90f3-36886989c5c5",
    "Mapa Campeonatos 2026 SAM": "8e9ce0d6-7754-4323-9708-17325d990cfe",
    "Mapeamento de Rede do CPD": "c8619e5a-d213-4b6a-ad49-3ece1888146a",
    "Mapeamento de Streaming CGD": "daf41a50-7230-429f-a548-9e50819c3226",
    "Metas": "5472a98e-c67f-402f-a84f-827a4bf2d949",
    "Monitoramento de Canais CS": "b0ffcdd7-a0e7-4eb0-a5e8-e2142776b8eb",
    "Painel de Ocorrências": "9d23cb01-b29c-45e6-9ae7-cfac1d1dd598",
    "Painel de gestão de serviços dos CS": "2e2afc16-dfd6-4277-a16c-cd78bdd2e769",
    "Procedimentos": "c72ff4ae-9a06-45d1-ba75-46b8689b89d9",
    "Programação de eventos - Streaming": "f7e25960-cf15-4ed8-b88c-bf607dc90a0f",
    "Projetos": "a0409b29-be0b-405a-92ba-5a8e341b1ebc",
    "Redmine": "dead8ceb-e9b7-455b-8b4f-e235127d956b",
    "Redmine_JSON": "00242f62-c62b-46c2-ab1f-de4218c1d1de",
    "Relatorio Jogos Youtube": "f524737d-87c4-4c65-b540-d6583eda61d9",
    "Relatorios_de_Jogos": "ae3e2afa-d937-41ad-af48-ecd65fd86143",
    "Relatorios_de_Jogos_NBA": "fa332a4b-5c46-433f-953d-e0534a9f5ecd",
    "Repositorio_Automacoes": "7c3aaf7b-8185-4c80-b872-62f848274886",
    "SLA": "5c5c3222-0458-4ddc-8d65-db00e377af1a",
    "Solicitações de Acesso": "f47e41ef-9da0-402e-b845-7ebb38fc200c",
    "Tratativa de Problemas de captação": "ded1b3ae-698d-470d-aab9-3b1697d2f719",
    "Validação de Backup": "304e3893-02b6-494f-8148-9690736aa0c0",
    "data_cidades": "3999da83-07cf-48c1-b5bd-355a8a2c01a3",
    "data_emissoras": "296caa9d-e324-4209-84db-89e953d9b5f1",
    "data_emissoras_logo": "9d120bb8-2ef2-484b-9ff0-7d78a6c2aabd",
    "data_hosts": "b2a846c5-e4b6-49fa-b0ff-3429ecd8b6b5",
    "data_unificado_pvs_cidade_regiao": "5011d066-68c2-49ba-8759-85f682d1f299",
}

PRIORITY_LISTS = [
    "Painel de Ocorrências",
    "Programação de eventos - Streaming",
    "Contato Técnico de Hospedeiros",
    "Contatos de Antenistas",
    "Links de Internet dos Parceiros",
    "Monitoramento de Canais CS",
    "Painel de gestão de serviços dos CS"
]

SITE_ID = "adgbl.sharepoint.com,a3e49747-9bb6-4c93-9930-dda26c8d1050,34c8fe55-2cfe-4efc-8ce0-2958fd775ee0"

SYSTEM_FIELDS_NOISE = {
    "@odata.etag", "_UIVersionString", "_ComplianceFlags", "_ComplianceTag",
    "_ComplianceTagWrittenTime", "_ComplianceTagUserId", "ItemChildCount",
    "FolderChildCount", "Edit", "LinkTitleNoMenu", "LinkTitle",
    "LinkFilenameNoMenu", "LinkFilename", "DocIcon", "AppAuthor", "AppEditor"
}


class SharePointInspectorSync:
    """
    Inspetor Headless de Alterações e Sincronizador Bidirecional SharePoint -> Google.
    """

    def __init__(
        self,
        state_file: Optional[str] = None,
        master_data_file: Optional[str] = None,
        site_id: str = SITE_ID
    ):
        self.project_root = get_project_root()
        self.site_id = site_id
        self.state_file = state_file or os.path.join(self.project_root, "config", "sharepoint_sync_state.json")
        self.master_data_file = master_data_file or os.path.join(self.project_root, "config", "sharepoint_portal_master_data.json")
        self.painel_ocorrencias_file = os.path.join(self.project_root, "config", "painel_ocorrencias_clean_live.json")
        self.clean_migrated_events_file = os.path.join(self.project_root, "config", "sharepoint_clean_migrated_events.json")
        self.google_sheets_api_url = "https://script.google.com/macros/s/AKfycbxzWKi1dNiGUiF15Ysl_69Pe2dt2vUpe1UBQ9xadPenmnsH68VOk6W1ZMwhRQkRpkBX/exec"
        self.escala_excel_file = os.path.join(self.project_root, "config", "Escala de trabalho 2026.xlsx")
        self.escala_json_file = os.path.join(self.project_root, "config", "escala_completa_2026.json")
        self.chat_webhook_file = os.path.join(self.project_root, "config", "google_chat_webhook.json")
        self.session = requests.Session()
        self._token: Optional[str] = None

    def get_token(self) -> str:
        """Obtém token de autorização do Microsoft Graph com cache e renovação automática."""
        if not self._token:
            self._token = SharePointReporter.obter_token_graph()
        return self._token

    def _request_graph(
        self,
        url: str,
        method: str = "GET",
        json_payload: Optional[dict] = None,
        extra_headers: Optional[dict] = None,
        max_retries: int = 4
    ) -> requests.Response:
        """Executa chamada HTTP ao Graph API com backoff inteligente anti-throttling (429)."""
        token = self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        if extra_headers:
            headers.update(extra_headers)

        for attempt in range(max_retries):
            try:
                time.sleep(0.6)  # Espaçamento preventivo
                if method.upper() == "GET":
                    resp = self.session.get(url, headers=headers, timeout=25)
                elif method.upper() == "POST":
                    resp = self.session.post(url, headers=headers, json=json_payload, timeout=25)
                else:
                    resp = self.session.request(method, url, headers=headers, json=json_payload, timeout=25)

                if resp.status_code == 200:
                    return resp
                elif resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 6))
                    wait_sec = min(max(retry_after + 1, 6), 25)
                    logger.warning(f"[Graph 429 Throttled] Aguardando {wait_sec}s (tentativa {attempt+1}/{max_retries})...")
                    time.sleep(wait_sec)
                elif resp.status_code == 401:
                    logger.warning("[Graph 401] Renovando token expirado...")
                    self._token = SharePointReporter.obter_token_graph()
                    headers["Authorization"] = f"Bearer {self._token}"
                    time.sleep(1)
                else:
                    logger.warning(f"[Graph HTTP {resp.status_code}] Falha em {url[:100]}: {resp.text[:150]}")
                    return resp
            except Exception as e:
                logger.warning(f"[Graph Exception] Tentativa {attempt+1}/{max_retries} falhou: {e}")
                time.sleep(2)

        # Fallback dummy response
        dummy = requests.Response()
        dummy.status_code = 500
        return dummy

    def load_state(self) -> dict:
        """Carrega estado persistente da última sincronização."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Erro ao ler estado de sincronização ({self.state_file}): {e}")
        return {
            "last_scan_utc": "",
            "lists": {},
            "drives": {},
            "sync_history": []
        }

    def save_state(self, state: dict) -> None:
        """Salva o estado persistente."""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Falha ao salvar estado de sincronização: {e}")

    def inspect_live_changes(self, state: Optional[dict] = None) -> dict:
        """
        Sensor leve de metadados: consulta em ~1s o carimbo lastModifiedDateTime
        de todas as listas e drives do SharePoint, comparando com o cache.
        """
        state = state or self.load_state()
        cached_lists = state.get("lists", {})
        cached_drives = state.get("drives", {})

        changed_lists = []
        changed_drives = []

        # 1. Checar Listas
        lists_url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/lists"
        resp_lists = self._request_graph(lists_url)
        live_lists = []
        if resp_lists.status_code == 200:
            live_lists = resp_lists.json().get("value", [])
        else:
            # Fallback resiliente: consultar listas operacionais prioritárias diretamente por ID
            logger.info("ℹ️ Utilizando fallback resiliente de listas prioritárias por ID...")
            for p_name in PRIORITY_LISTS:
                p_id = ALL_LISTS_MAP.get(p_name)
                if p_id:
                    p_url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/lists/{p_id}?$select=id,displayName,lastModifiedDateTime"
                    p_resp = self._request_graph(p_url)
                    if p_resp.status_code == 200:
                        live_lists.append(p_resp.json())

        is_first_run = not cached_lists

        for l in live_lists:
            list_id = l.get("id")
            disp_name = l.get("displayName")
            mod_time = l.get("lastModifiedDateTime", "")
            
            cached_entry = cached_lists.get(disp_name) or {}
            last_synced = cached_entry.get("last_synced_modified", "")

            if is_first_run:
                # Na primeira execução, estabelece a linha de base para todas as listas
                # e sincroniza de imediato as listas prioritárias operacionais
                if disp_name in PRIORITY_LISTS:
                    changed_lists.append({
                        "id": list_id,
                        "displayName": disp_name,
                        "lastModifiedDateTime": mod_time,
                        "previous_synced": ""
                    })
                else:
                    if "lists" not in state:
                        state["lists"] = {}
                    state["lists"][disp_name] = {
                        "id": list_id,
                        "lastModifiedDateTime": mod_time,
                        "last_synced_modified": mod_time,
                        "last_synced_at": datetime.now(timezone.utc).isoformat()
                    }
            elif not last_synced or mod_time > last_synced:
                changed_lists.append({
                    "id": list_id,
                    "displayName": disp_name,
                    "lastModifiedDateTime": mod_time,
                    "previous_synced": last_synced
                })

        # 2. Checar Bibliotecas (Drives)
        drives_url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drives"
        resp_drives = self._request_graph(drives_url)
        live_drives = []
        if resp_drives.status_code == 200:
            live_drives = resp_drives.json().get("value", [])

        is_first_drive_run = not cached_drives
        for d in live_drives:
            drive_id = d.get("id")
            drive_name = d.get("name")
            mod_time = d.get("lastModifiedDateTime", "")

            cached_entry = cached_drives.get(drive_name) or {}
            last_synced = cached_entry.get("last_synced_modified", "")

            if is_first_drive_run:
                if any(k in drive_name.lower() for k in ["escala", "nba", "jogos", "youtube"]):
                    changed_drives.append({
                        "id": drive_id,
                        "name": drive_name,
                        "lastModifiedDateTime": mod_time,
                        "previous_synced": ""
                    })
                else:
                    if "drives" not in state:
                        state["drives"] = {}
                    state["drives"][drive_name] = {
                        "id": drive_id,
                        "lastModifiedDateTime": mod_time,
                        "last_synced_modified": mod_time,
                        "last_synced_at": datetime.now(timezone.utc).isoformat()
                    }
            elif not last_synced or mod_time > last_synced:
                changed_drives.append({
                    "id": drive_id,
                    "name": drive_name,
                    "lastModifiedDateTime": mod_time,
                    "previous_synced": last_synced
                })

        has_changes = bool(changed_lists or changed_drives)
        return {
            "has_changes": has_changes,
            "changed_lists": changed_lists,
            "changed_drives": changed_drives,
            "total_lists_checked": len(live_lists),
            "total_drives_checked": len(live_drives),
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }

    def clean_item_fields(self, fields: dict) -> dict:
        """Limpa campos de ruído do SharePoint mantendo dados de negócio."""
        return {k: v for k, v in fields.items() if k not in SYSTEM_FIELDS_NOISE}

    def sync_list_items(self, list_meta: dict, top_n: int = 50) -> Tuple[int, int]:
        """
        Sincroniza itens de uma lista específica de forma incremental (Upsert).
        Retorna (novos_inseridos, atualizados).
        """
        list_id = list_meta["id"]
        list_name = list_meta["displayName"]
        last_mod = list_meta["lastModifiedDateTime"]

        logger.info(f"🔄 Sincronizando lista '{list_name}' ({list_id})...")

        # Buscar itens ordenados por Modified desc
        extra_headers = {"Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly"}
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/lists/{list_id}/items?$expand=fields&$orderby=fields/Modified desc&$top={top_n}"
        resp = self._request_graph(url, extra_headers=extra_headers)

        if resp.status_code != 200:
            logger.warning(f"Fallback buscando itens sem orderby para '{list_name}'...")
            url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/lists/{list_id}/items?$expand=fields&$top={top_n}"
            resp = self._request_graph(url)

        if resp.status_code != 200:
            logger.error(f"Falha ao obter itens da lista '{list_name}': HTTP {resp.status_code}")
            return (0, 0)

        raw_items = resp.json().get("value", [])
        if not raw_items:
            logger.info(f"Nenhum item retornado para '{list_name}'.")
            return (0, 0)

        # 1. Atualizar config/sharepoint_portal_master_data.json
        master_data = {}
        if os.path.exists(self.master_data_file):
            try:
                with open(self.master_data_file, "r", encoding="utf-8") as f_m:
                    master_data = json.load(f_m)
            except Exception:
                master_data = {}

        if "lists" not in master_data:
            master_data["lists"] = {}

        if list_name not in master_data["lists"]:
            master_data["lists"][list_name] = {
                "displayName": list_name,
                "name": list_name,
                "id": list_id,
                "lastModifiedDateTime": last_mod,
                "items_count": 0,
                "items": []
            }

        target_list_obj = master_data["lists"][list_name]
        existing_items = target_list_obj.get("items", [])
        existing_by_id = {str(it.get("id")): it for it in existing_items if "id" in it}

        inserted_count = 0
        updated_count = 0

        for r_item in raw_items:
            item_id = str(r_item.get("id"))
            raw_fields = r_item.get("fields", {})
            cleaned_fields = self.clean_item_fields(raw_fields)
            cleaned_fields["id"] = item_id

            if item_id in existing_by_id:
                existing_by_id[item_id].update(cleaned_fields)
                updated_count += 1
            else:
                existing_items.insert(0, cleaned_fields)
                existing_by_id[item_id] = cleaned_fields
                inserted_count += 1

        target_list_obj["items"] = existing_items
        target_list_obj["items_count"] = len(existing_items)
        target_list_obj["lastModifiedDateTime"] = last_mod
        target_list_obj["last_sync_utc"] = datetime.now(timezone.utc).isoformat()

        try:
            with open(self.master_data_file, "w", encoding="utf-8") as f_out:
                json.dump(master_data, f_out, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar master data: {e}")

        # 2. Tratamento Especial para 'Painel de Ocorrências' e 'Programação de eventos - Streaming'
        if list_name == "Painel de Ocorrências":
            self._sync_painel_ocorrencias_clean(raw_items)
        elif list_name == "Programação de eventos - Streaming":
            self._sync_streaming_clean(raw_items)

        logger.info(f"✅ Lista '{list_name}' sincronizada: +{inserted_count} novos, {updated_count} atualizados.")
        return (inserted_count, updated_count)

    def _sync_painel_ocorrencias_clean(self, raw_items: List[dict]) -> None:
        """Atualiza config/painel_ocorrencias_clean_live.json com as ocorrências mais recentes."""
        clean_items = []
        if os.path.exists(self.painel_ocorrencias_file):
            try:
                with open(self.painel_ocorrencias_file, "r", encoding="utf-8") as f:
                    clean_items = json.load(f)
            except Exception:
                clean_items = []

        existing_clean_by_id = {str(it.get("id")): it for it in clean_items}

        for r_item in raw_items:
            item_id = str(r_item.get("id"))
            f = r_item.get("fields", {})

            # Mapeamento canônico
            formatted_item = {
                "id": item_id,
                "Status": f.get("Problema") or "Em andamento",
                "Criado": f.get("Created") or datetime.now(timezone.utc).isoformat(),
                "hostLookupId": str(f.get("hostLookupId") or ""),
                "CS": f.get("CS") or ["01"],
                "Veiculo": f.get("Veiculoo") or f.get("Veiculo") or "Todos",
                "Equipamento": f.get("Equipamento") or ["Maquina"],
                "TipoProblema": f.get("Problema0") or f.get("TipoProblema") or "Sem comunicação",
                "EmRecuperacao": f.get("Emrecupera_x00e7__x00e3_o") or "Não",
                "GravacaoStreaming": f.get("Graca_x00e7__x00e3_o_x0020_por_x") or "Não",
                "InformarOperacao": bool(f.get("Informar_x0020_Opera_x00e7__x00e", False)),
                "AcoesExecutadas": f.get("A_x00e7__x00f5_esexecutadas") or f.get("AcoesExecutadas") or "",
                "AreaResponsavel": f.get("Area_x002f_Usuarioresponsavel") or f.get("AreaResponsavel") or "N1",
                "Redmine": f.get("RedmineUser") or f.get("Resolucao") or f.get("Redmine") or ""
            }

            if item_id in existing_clean_by_id:
                existing_clean_by_id[item_id].update(formatted_item)
            else:
                clean_items.insert(0, formatted_item)
                existing_clean_by_id[item_id] = formatted_item

        # Ordenar por ID decrescente
        try:
            clean_items.sort(key=lambda x: int(x["id"]) if str(x.get("id", "")).isdigit() else 0, reverse=True)
        except Exception:
            pass

        try:
            with open(self.painel_ocorrencias_file, "w", encoding="utf-8") as f_out:
                json.dump(clean_items, f_out, indent=2, ensure_ascii=False)
            logger.info(f"📋 Painel de Ocorrências clean atualizado com sucesso ({len(clean_items)} ocorrências totais).")
        except Exception as e:
            logger.error(f"Erro ao salvar painel_ocorrencias_clean_live.json: {e}")

    def _patch_sharepoint_item_streaming(self, item_id: str, responsavel: str, pvid: str) -> bool:
        """Atualiza no SharePoint o Responsável pela Gravação e o PVID caso estejam vazios."""
        try:
            list_id = ALL_LISTS_MAP.get("Programação de eventos - Streaming")
            if not list_id or not item_id:
                return False
            url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/lists/{list_id}/items/{item_id}/fields"
            payload = {}
            if responsavel:
                payload["BKP_x0020__x0028_Uso_x0020_Supor"] = responsavel
            if pvid:
                payload["PVID"] = pvid
            if not payload:
                return False
            resp = self._request_graph(url, method="PATCH", json_payload=payload)
            if resp.status_code == 200:
                logger.info(f"✨ SharePoint Item #{item_id} enriquecido com sucesso (Responsável: '{responsavel}', PVID: '{pvid}').")
                return True
            return False
        except Exception as e:
            logger.warning(f"Não foi possível efetuar patch no SharePoint Item #{item_id}: {e}")
            return False

    def _push_to_google_sheets(self, events: List[dict]) -> bool:
        """Envia eventos novos/atualizados para a planilha Google Sheets oficial via Web App."""
        try:
            if not events:
                return True
            payload = {"events": events}
            resp = self.session.post(self.google_sheets_api_url, json=payload, timeout=25)
            if resp.status_code == 200:
                logger.info(f"📊 Google Sheets sincronizado com sucesso: {len(events)} eventos transmitidos.")
                return True
            else:
                logger.warning(f"Google Sheets retornou HTTP {resp.status_code}: {resp.text[:200]}")
                return False
        except Exception as e:
            logger.warning(f"Falha ao enviar eventos para Google Sheets Web App: {e}")
            return False

    def _sync_streaming_clean(self, raw_items: List[dict]) -> Tuple[int, int]:
        """
        Sincroniza a programação de streaming com o dataset canônico:
        config/sharepoint_clean_migrated_events.json e Google Sheets.
        Garante associação de responsável da escala e PVID se vazios no SharePoint.
        """
        clean_events = []
        if os.path.exists(self.clean_migrated_events_file):
            try:
                with open(self.clean_migrated_events_file, "r", encoding="utf-8") as f:
                    clean_events = json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar sharepoint_clean_migrated_events.json: {e}")

        existing_by_id = {}
        existing_by_key = {}
        for idx, ev in enumerate(clean_events):
            sp_id = str(ev.get("id_sharepoint", "")).strip()
            if sp_id:
                existing_by_id[sp_id] = idx
            partida = str(ev.get("partida", "")).strip().lower()
            data = str(ev.get("data", "")).strip()
            if partida and data:
                existing_by_key[(partida, data)] = idx

        meses_nomes = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]

        def parse_date_to_br(raw_date: Any) -> Tuple[str, str, str]:
            """Retorna (data_dd_mm_yyyy, mes_nome, ano_yyyy)."""
            if not raw_date:
                return ("", "", "")
            s = str(raw_date).strip()
            if "T" in s:
                d_part = s.split("T")[0]
                p = d_part.split("-")
                if len(p) == 3:
                    y, m, d = p[0], p[1], p[2]
                    m_idx = int(m) - 1
                    m_nome = meses_nomes[m_idx] if 0 <= m_idx < 12 else ""
                    return (f"{d}/{m}/{y}", m_nome, y)
            elif "/" in s:
                p = s.split("/")
                if len(p) == 3:
                    d, m, y = p[0].zfill(2), p[1].zfill(2), p[2]
                    m_idx = int(m) - 1
                    m_nome = meses_nomes[m_idx] if 0 <= m_idx < 12 else ""
                    return (f"{d}/{m}/{y}", m_nome, y)
            return (s, "", "")

        inserted_count = 0
        updated_count = 0
        events_to_push = []

        for r_item in raw_items:
            item_id = str(r_item.get("id", ""))
            f = r_item.get("fields", {})

            partida = str(f.get("Partida") or "").strip()
            campeonato = str(f.get("Title") or f.get("LinkTitle") or "").strip()
            horario = str(f.get("Hor_x00e1_rio") or "16:00").strip()

            raw_data = f.get("Data")
            data_br, mes_calc, ano_calc = parse_date_to_br(raw_data)
            mes = str(f.get("M_x00ea_s") or mes_calc or "").strip()

            canal_raw = f.get("Transmiss_x00e3_o")
            if isinstance(canal_raw, list):
                canal = ", ".join(str(c) for c in canal_raw if c).strip()
            else:
                canal = str(canal_raw or "Amazon Prime").strip()
            if not canal:
                canal = "Amazon Prime"

            # Responsável pela gravação
            responsavel = str(f.get("BKP_x0020__x0028_Uso_x0020_Supor") or "").strip()
            orig_resp_empty = not bool(responsavel)
            if not responsavel:
                # Regra de ouro da escala: Cleber BL01 e Backup padrão
                responsavel = "Cleber BL01 e Backup"

            # PVID TV BOX
            pvid = str(f.get("PVID") or "").strip()
            orig_pvid_empty = not bool(pvid)
            if not pvid:
                c_low = canal.lower()
                if "prime" in c_low or "amazon" in c_low:
                    pvid = "Prime Video - PV3687"
                elif "cazé" in c_low or "caze" in c_low:
                    pvid = "CAZETV - PV3625"
                elif "netflix" in c_low:
                    pvid = "Netflix - PV3679"
                elif "tnt" in c_low or "max" in c_low:
                    pvid = "TNT - 316"
                elif "record" in c_low:
                    pvid = "Record - 58"
                elif "dazn" in c_low:
                    pvid = "DAZN - PVBOX"
                else:
                    pvid = f"{canal} - PVBOX"

            # Sort key (YYYY-MM-DD_HH:MM)
            if data_br and "/" in data_br:
                dp = data_br.split("/")
                sort_key = f"{dp[2]}-{dp[1]}-{dp[0]}_{horario}"
            else:
                sort_key = f"9999-12-31_{horario}"

            # Enriquecer o SharePoint de volta apenas para confrontos vigentes/futuros ou recém-criados
            # (evita sobrecarga de throttling do Graph API com jogos retroativos antigos)
            today_str = datetime.now().strftime("%Y-%m-%d")
            is_upcoming_or_new = (sort_key >= today_str) or (item_id not in existing_by_id)
            if (orig_resp_empty or orig_pvid_empty) and item_id and is_upcoming_or_new:
                self._patch_sharepoint_item_streaming(item_id, responsavel, pvid)

            status_entrega = str(f.get("StatusdeEntrega") or "Pendente").strip()
            programado_raw = str(f.get("Programado_x0020_TV_x0020_BOX_x0") or "NÃO").strip().upper()
            programado = "SIM" if programado_raw in ["SIM", "S", "TRUE", "1"] else "NÃO"

            formatted_item = {
                "id_sharepoint": item_id,
                "anexos": "",
                "mes": mes,
                "data": data_br,
                "horario": horario,
                "campeonato": campeonato,
                "partida": partida,
                "responsavel": responsavel,
                "canal": canal,
                "pvid": pvid,
                "status_entrega": status_entrega,
                "programado": programado,
                "_sort_key": sort_key
            }

            match_key = (partida.lower(), data_br)
            if item_id in existing_by_id:
                idx = existing_by_id[item_id]
                clean_events[idx].update(formatted_item)
                updated_count += 1
                events_to_push.append(formatted_item)
            elif match_key in existing_by_key:
                idx = existing_by_key[match_key]
                clean_events[idx].update(formatted_item)
                updated_count += 1
                events_to_push.append(formatted_item)
            else:
                clean_events.append(formatted_item)
                existing_by_id[item_id] = len(clean_events) - 1
                existing_by_key[match_key] = len(clean_events) - 1
                inserted_count += 1
                events_to_push.append(formatted_item)

        # Ordenar cronologicamente por _sort_key
        try:
            clean_events.sort(key=lambda x: x.get("_sort_key", ""))
        except Exception:
            pass

        # Salvar dataset limpo
        try:
            with open(self.clean_migrated_events_file, "w", encoding="utf-8") as f_out:
                json.dump(clean_events, f_out, indent=2, ensure_ascii=False)
            logger.info(f"⚽ Programação Streaming clean atualizada ({len(clean_events)} eventos totais, +{inserted_count} novos, {updated_count} atualizados).")
        except Exception as e:
            logger.error(f"Erro ao salvar sharepoint_clean_migrated_events.json: {e}")

        # Enviar eventos novos para a nuvem Google Sheets
        if events_to_push:
            self._push_to_google_sheets(events_to_push)

        return (inserted_count, updated_count)

    def sync_drive_items(self, drive_meta: dict) -> int:
        """Sincroniza bibliotecas de arquivos/relatórios (ex: Escala de trabalho ou relatórios)."""
        drive_name = drive_meta["name"]
        drive_id = drive_meta["id"]

        logger.info(f"📁 Verificando alterações na biblioteca '{drive_name}' ({drive_id})...")

        # Caso especial: Escala de trabalho
        if "escala" in drive_name.lower():
            try:
                from scripts.sync_escala_excel import sync_from_sharepoint_if_possible, parse_escala_excel
                logger.info("📥 Baixando versão mais recente de 'Escala de trabalho 2026.xlsx'...")
                sync_from_sharepoint_if_possible(self.escala_excel_file)
                parse_escala_excel(self.escala_excel_file, self.escala_json_file)
                return 1
            except Exception as e:
                logger.error(f"Erro ao sincronizar Escala de Trabalho: {e}")
                return 0

        # Outras bibliotecas: registrar última modificação
        return 0

    def rebuild_portal_web(self) -> bool:
        """Recompila o portal web (portal_web/ e docs/) com os dados atualizados."""
        try:
            logger.info("🚀 Recompilando Portal Web com os novos dados sincronizados...")
            from scripts.build_portal_web import generate_portal
            generate_portal()
            logger.info("✅ Portal Web Suporte Captação recompilado com sucesso!")
            return True
        except Exception as e:
            logger.error(f"Falha ao recompilar Portal Web: {e}")
            return False

    def notify_chat_if_configured(self, summary_text: str) -> None:
        """Envia aviso para o Google Chat caso haja webhook ativo."""
        if not os.path.exists(self.chat_webhook_file):
            return
        try:
            with open(self.chat_webhook_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            url = cfg.get("webhook_url")
            if not url or not url.startswith("https://chat.googleapis.com/"):
                return

            payload = {
                "cardsV2": [{
                    "cardId": "sharepoint-sync-alert",
                    "card": {
                        "header": {
                            "title": "⚡ Suporte Captação | Sincronizador Automático",
                            "subtitle": "Alterações no SharePoint refletidas no Portal Google",
                            "imageUrl": "https://img.icons8.com/color/48/000000/synchronize.png",
                            "imageType": "CIRCLE"
                        },
                        "sections": [{
                            "header": "Resumo da Sincronização",
                            "widgets": [
                                {"textParagraph": {"text": summary_text}},
                                {"buttonList": {
                                    "buttons": [{
                                        "text": "🌐 Acessar Portal Web",
                                        "onClick": {
                                            "openLink": {"url": "https://sites.google.com/ibope.com/suportecaptacao"}
                                        }
                                    }]
                                }}
                            ]
                        }]
                    }
                }]
            }
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.warning(f"Aviso no Google Chat não enviado: {e}")

    def run_sync_cycle(self, force_all: bool = False, rebuild: bool = True) -> dict:
        """
        Executa um ciclo completo de inspeção e sincronização:
        1. Sensor leve de metadados
        2. Extração incremental das listas/drives alterados
        3. Atualização do estado persistente
        4. Recompilação do Portal Web (docs/ e portal_web/)
        """
        start_time = time.time()
        state = self.load_state()

        logger.info("🔍 [SharePoint Live Inspector] Verificando alterações no site...")
        inspection = self.inspect_live_changes(state)

        changed_lists = inspection["changed_lists"]
        changed_drives = inspection["changed_drives"]

        if force_all:
            # Forçar checagem das principais listas
            priority_lists = ["Painel de Ocorrências", "Programação de eventos - Streaming", "Contato Técnico de Hospedeiros", "Escala de trabalho"]
            for l in inspection.get("live_lists", []):
                if l.get("displayName") in priority_lists and not any(cl["id"] == l.get("id") for cl in changed_lists):
                    changed_lists.append(l)

        if not changed_lists and not changed_drives and not force_all:
            logger.info("✨ Nenhuma alteração detectada no SharePoint. Portal está 100% atualizado.")
            elapsed = time.time() - start_time
            return {
                "has_changes": False,
                "elapsed_seconds": round(elapsed, 2),
                "message": "Nenhuma alteração detectada."
            }

        logger.info(f"🔔 Alterações detectadas: {len(changed_lists)} listas, {len(changed_drives)} bibliotecas.")

        total_inserted = 0
        total_updated = 0
        synced_list_names = []

        # Sincronizar listas alteradas
        for l_meta in changed_lists:
            disp_name = l_meta["displayName"]
            l_id = l_meta["id"]
            ins, upd = self.sync_list_items(l_meta)
            total_inserted += ins
            total_updated += upd
            synced_list_names.append(disp_name)

            # Atualizar estado da lista
            if "lists" not in state:
                state["lists"] = {}
            state["lists"][disp_name] = {
                "id": l_id,
                "lastModifiedDateTime": l_meta.get("lastModifiedDateTime"),
                "last_synced_modified": l_meta.get("lastModifiedDateTime"),
                "last_synced_at": datetime.now(timezone.utc).isoformat(),
                "inserted_count": ins,
                "updated_count": upd
            }

        # Sincronizar bibliotecas alteradas
        for d_meta in changed_drives:
            d_name = d_meta["name"]
            d_id = d_meta["id"]
            self.sync_drive_items(d_meta)

            if "drives" not in state:
                state["drives"] = {}
            state["drives"][d_name] = {
                "id": d_id,
                "lastModifiedDateTime": d_meta.get("lastModifiedDateTime"),
                "last_synced_modified": d_meta.get("lastModifiedDateTime"),
                "last_synced_at": datetime.now(timezone.utc).isoformat()
            }

        # Atualizar histórico de sincronização
        state["last_scan_utc"] = datetime.now(timezone.utc).isoformat()
        if "sync_history" not in state:
            state["sync_history"] = []
        state["sync_history"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lists_synced": synced_list_names,
            "items_inserted": total_inserted,
            "items_updated": total_updated
        })
        # Manter apenas os últimos 50 registros de histórico
        state["sync_history"] = state["sync_history"][-50:]
        self.save_state(state)

        # Recompilar portal se solicitado
        if rebuild and (total_inserted > 0 or total_updated > 0 or changed_drives):
            self.rebuild_portal_web()

        elapsed = time.time() - start_time
        summary_msg = f"Sincronização concluída em {round(elapsed, 2)}s: {total_inserted} itens inseridos, {total_updated} atualizados em: {', '.join(synced_list_names)}."
        logger.info(summary_msg)

        return {
            "has_changes": True,
            "items_inserted": total_inserted,
            "items_updated": total_updated,
            "lists_synced": synced_list_names,
            "elapsed_seconds": round(elapsed, 2),
            "message": summary_msg
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Inspetor Headless de Alterações SharePoint -> Google")
    parser.add_argument("--once", action="store_true", help="Executa uma única verificação e sincronização")
    parser.add_argument("--force", action="store_true", help="Força a sincronização completa mesmo sem alteração de data")
    parser.add_argument("--status", action="store_true", help="Exibe status da última sincronização e listas monitoradas")
    parser.add_argument("--loop", action="store_true", help="Executa em modo contínuo (daemon/polling) em segundo plano")
    parser.add_argument("--interval", type=int, default=300, help="Intervalo de polling em segundos para o modo --loop (padrão: 300s = 5 min)")
    args = parser.parse_args()

    inspector = SharePointInspectorSync()

    if args.status:
        state = inspector.load_state()
        print(f"📊 Status do Inspetor SharePoint:")
        print(f"  Último scan UTC: {state.get('last_scan_utc', 'Nunca')}")
        print(f"  Listas mapeadas no estado: {len(state.get('lists', {}))}")
        print(f"  Drives mapeados no estado: {len(state.get('drives', {}))}")
        hist = state.get("sync_history", [])
        if hist:
            print(f"  Último evento: {hist[-1]}")
        sys.exit(0)

    if args.loop:
        print(f"🚀 Iniciando Inspetor SharePoint em modo contínuo (intervalo: {args.interval}s)... Pressione Ctrl+C para encerrar.")
        try:
            while True:
                inspector.run_sync_cycle(force_all=args.force)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n🛑 Inspetor finalizado pelo usuário.")
            sys.exit(0)

    # Modo padrão: --once
    res = inspector.run_sync_cycle(force_all=args.force)
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
