"""
Módulo de Sincronização em Paralelo de Relatórios para o Portal Web (Google Sites / GitHub Pages).
Garante que todos os relatórios gerados pelo Monitor_Esportes (Futebol, YouTube e NBA)
sejam publicados simultaneamente no Microsoft SharePoint e no novo Portal Web (Google Sites),
inclusive quando executado como executável standalone (.exe PyInstaller) sem git instalado.
"""

import os
import sys
import json
import uuid
import base64
import hashlib
import shutil
import logging
import subprocess
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Repositório oficial que alimenta o GitHub Pages / Google Sites do Suporte Captação
GITHUB_OWNER = "CleberSGoncalves"
GITHUB_REPO = "Monitor_Esportes"
GITHUB_BRANCH = "main"

# Token cifrado em AES-256-CBC (mesmo padrão seguro do SharePointReporter)
# Permite publicação direta na GitHub API pelo .exe em qualquer máquina da equipe.
RAW_PORTAL_GH_TOKEN = "ENC:ImVjG0J3BwQlkgSEr3rnlGR9oGuMtjWVWAAX3zwD4WB4mz6S+6jBnZwFre3Bktpiy+TPASeozEvn3TtCY88jiQ=="

CATEGORY_TO_DRIVE = {
    "futebol": "Relatorios_de_Jogos",
    "youtube": "Relatorio Jogos Youtube",
    "nba": "Relatorios_de_Jogos_NBA",
}

DRIVE_TO_CATEGORY = {
    "Relatorios_de_Jogos": "futebol",
    "Relatorio Jogos Youtube": "youtube",
    "Relatorios_de_Jogos_NBA": "nba",
}

_GITHUB_PUBLISH_LOCK = threading.RLock()
_PENDING_BATCHES: Dict[str, List[Dict[str, Any]]] = {}


def _decrypt_portal_gh_token() -> str:
    try:
        if not RAW_PORTAL_GH_TOKEN.startswith("ENC:"):
            return ""
        raw_bytes = base64.b64decode(RAW_PORTAL_GH_TOKEN[4:])
        key = b"DNA_MONITOR_FLEET_SEC_2026_ADGBL"
        iv = raw_bytes[:16]
        cipher_bytes = raw_bytes[16:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(cipher_bytes) + decryptor.finalize()
        pad = decrypted[-1]
        return decrypted[:-pad].decode("utf-8")
    except Exception as e:
        logger.warning(f"[PortalSync] Falha ao decifrar credencial de publicação do Portal: {e}")
        return ""


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


def iso_utc_to_brt_str(iso_str: Optional[str]) -> str:
    """Converte data ISO UTC (ex: '2026-12-01T00:30:00Z') para horário de Brasília ('30/11/2026 21:30')."""
    if not iso_str:
        return datetime.now().strftime("%d/%m/%Y %H:%M")
    s = str(iso_str).strip()
    if not s:
        return datetime.now().strftime("%d/%m/%Y %H:%M")
    # Se já está no formato DD/MM/YYYY [HH:MM]
    if "/" in s and len(s) >= 10:
        return s[:16] if ":" in s else s[:10]
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt_brt = dt.astimezone(timezone(timedelta(hours=-3)))
        else:
            dt_brt = dt
        return dt_brt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return s


def _git_blob_sha(content_bytes: bytes) -> str:
    """Calcula o SHA-1 exato usado pelo Git para um blob."""
    header = f"blob {len(content_bytes)}\0".encode("utf-8")
    return hashlib.sha1(header + content_bytes).hexdigest()


def _parse_item_sort_ts(item: Dict[str, Any]) -> float:
    """Retorna timestamp numérico para ordenar sempre o mais recente no topo."""
    f = item.get("fields") or {}
    d_str = f.get("Data_Hora") or f.get("Data_Jogo") or item.get("lastModifiedDateTime") or ""
    if d_str:
        s = str(d_str).strip()
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                return datetime.strptime(s[:len(fmt) + 2].strip(), fmt).timestamp()
            except Exception:
                pass
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
    lm = item.get("lastModifiedDateTime")
    if lm:
        try:
            return datetime.fromisoformat(str(lm).replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
    return 0.0


class PortalSyncManager:
    """
    Gerencia a esteira de reporte em paralelo para o Portal Web (Google Sites / GitHub Pages).
    Publica tanto no repositório local quanto diretamente no GitHub (branch main -> GitHub Pages),
    atualizando o PDF em docs/reports/<category>/ e o índice ao vivo docs/reports/index_<category>.json.
    """

    @classmethod
    def _get_github_token(cls) -> str:
        env_tok = os.getenv("PORTAL_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") or ""
        if env_tok.strip():
            return env_tok.strip()
        dec = _decrypt_portal_gh_token()
        if dec:
            return dec
        try:
            res = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=get_project_root(),
            )
            remote_url = (res.stdout or "").strip()
            if "@" in remote_url and "://" in remote_url:
                auth_part = remote_url.split("://")[1].split("@")[0]
                return auth_part.split(":")[1] if ":" in auth_part else auth_part
        except Exception:
            pass
        return ""

    @classmethod
    def _gh_headers(cls, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MonitorEsportes-PortalSync/2.5",
        }

    @classmethod
    def _build_drive_item(
        cls,
        target_filename: str,
        category: str,
        file_size: int,
        now_iso: str,
        partida: str,
        campeonato: str,
        plataforma: str,
        confianca: str,
        data_hora: str,
        auditado: bool,
        placar: Optional[str],
        canal: Optional[str],
        item_id: Optional[str] = None,
        modified_by: str = "Monitor_Esportes Auto-Audit",
        created_by: str = "svc.captacao",
    ) -> Dict[str, Any]:
        relative_web_url = f"reports/{category}/{target_filename}"
        dt_display = iso_utc_to_brt_str(data_hora) if data_hora else datetime.now().strftime("%d/%m/%Y %H:%M")
        plat_final = plataforma or canal or ("NBA" if category == "nba" else "Caze TV")
        canal_final = canal or plataforma or plat_final
        camp_final = campeonato or ("NBA" if category == "nba" else "Brasileiro Serie A")
        conf_final = confianca or "99.0%"
        placar_final = placar if placar is not None else ("" if category != "youtube" else conf_final)

        fields_data = {
            "Data_Hora": dt_display,
            "Data_Jogo": dt_display,
            "Campeonato": camp_final,
            "Partida": partida or target_filename,
            "Plataforma": plat_final,
            "Canal": canal_final,
            "Confiança": conf_final,
            "Confianca": conf_final,
            "Auditado": bool(auditado),
            "Placar": placar_final,
            "Criado_Por": created_by,
            # Aliases lowercase para compatibilidade retroativa
            "partida": partida or target_filename,
            "campeonato": camp_final,
            "plataforma": plat_final,
            "canal": canal_final,
            "confianca": conf_final,
        }

        return {
            "id": item_id or f"PORTAL_{uuid.uuid4().hex[:12].upper()}",
            "name": target_filename,
            "type": "file",
            "extension": "pdf",
            "mime_type": "application/pdf",
            "size": file_size,
            "lastModifiedDateTime": now_iso,
            "lastModifiedBy": modified_by,
            "webUrl": relative_web_url,
            "childCount": None,
            "fields": fields_data,
            "meta": fields_data,
        }

    @classmethod
    def _upsert_item_in_list(cls, items: List[Dict[str, Any]], new_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        target_name_lower = (new_item.get("name") or "").strip().lower()
        updated = False
        for idx, it in enumerate(items):
            if (it.get("name") or "").strip().lower() == target_name_lower:
                preserved_id = it.get("id") or new_item["id"]
                merged = dict(new_item)
                merged["id"] = preserved_id
                items[idx] = merged
                updated = True
                break
        if not updated:
            items.insert(0, new_item)
        items.sort(key=_parse_item_sort_ts, reverse=True)
        return items

    @classmethod
    def _fetch_remote_index(cls, category: str, token: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Lê docs/reports/index_<category>.json diretamente do GitHub para preservar itens de outras máquinas."""
        api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/docs/reports/index_{category}.json"
        try:
            r = requests.get(api_url, headers=cls._gh_headers(token), params={"ref": GITHUB_BRANCH}, timeout=20)
            if r.status_code == 200:
                payload = r.json()
                raw_b64 = payload.get("content") or ""
                if raw_b64:
                    data = json.loads(base64.b64decode(raw_b64).decode("utf-8"))
                    return list(data.get("items") or []), payload.get("sha")
                # Se arquivo > 1MB, baixa pelo download_url
                dl_url = payload.get("download_url")
                if dl_url:
                    r_dl = requests.get(dl_url, timeout=20)
                    if r_dl.status_code == 200:
                        data = r_dl.json()
                        return list(data.get("items") or []), payload.get("sha")
        except Exception as e:
            logger.debug(f"[PortalSync] Índice remoto index_{category}.json ainda não disponível ou erro de leitura: {e}")
        return [], None

    @classmethod
    def _get_remote_file_sha(cls, repo_path: str, token: str) -> Optional[str]:
        api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{repo_path}"
        try:
            r = requests.get(api_url, headers=cls._gh_headers(token), params={"ref": GITHUB_BRANCH}, timeout=15)
            if r.status_code == 200:
                return r.json().get("sha")
        except Exception:
            pass
        return None

    @classmethod
    def _publish_entries_to_github_atomic(
        cls,
        category: str,
        drive_name: str,
        entries: List[Dict[str, Any]],
        local_fallback_items: Optional[List[Dict[str, Any]]] = None,
        commit_message: Optional[str] = None,
    ) -> bool:
        """
        Publica em UM ÚNICO COMMIT ATÔMICO na branch main do GitHub:
          - Todos os PDFs novos/atualizados em docs/reports/<category>/<filename>
          - O índice ao vivo docs/reports/index_<category>.json mesclado com o estado remoto
        Funciona 100% via GitHub REST API (zero dependência de git CLI no PC do operador).
        """
        token = cls._get_github_token()
        if not token:
            logger.warning("[PortalSync] Token GitHub ausente — publicação remota no Google Site ignorada.")
            return False

        if not entries:
            return True

        headers = cls._gh_headers(token)
        base_api = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

        with _GITHUB_PUBLISH_LOCK:
            for attempt in range(4):
                try:
                    # 1. Obter HEAD atual da branch main
                    r_ref = requests.get(f"{base_api}/git/ref/heads/{GITHUB_BRANCH}", headers=headers, timeout=20)
                    if r_ref.status_code != 200:
                        logger.warning(f"[PortalSync] Falha ao obter ref main (HTTP {r_ref.status_code}): {r_ref.text[:160]}")
                        return False
                    head_sha = r_ref.json()["object"]["sha"]

                    r_commit = requests.get(f"{base_api}/git/commits/{head_sha}", headers=headers, timeout=20)
                    if r_commit.status_code != 200:
                        logger.warning(f"[PortalSync] Falha ao obter commit {head_sha}: HTTP {r_commit.status_code}")
                        return False
                    base_tree_sha = r_commit.json()["tree"]["sha"]

                    # 2. Ler índice remoto atual (para nunca sobrescrever envios de outras máquinas)
                    remote_items, _ = cls._fetch_remote_index(category, token)
                    if not remote_items and local_fallback_items:
                        remote_items = [dict(x) for x in local_fallback_items]

                    # 3. Preparar blobs dos PDFs novos/atualizados e mesclar itens no índice
                    tree_entries = []
                    uploaded_pdfs = 0

                    for ent in entries:
                        item_obj = ent["item"]
                        pdf_path = ent.get("pdf_path")
                        fname = item_obj["name"]

                        cls._upsert_item_in_list(remote_items, item_obj)

                        if pdf_path and os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as f_pdf:
                                pdf_bytes = f_pdf.read()
                            if len(pdf_bytes) < 100:
                                logger.warning(f"[PortalSync] PDF suspeito (<100 bytes) ignorado no upload: {fname}")
                                continue

                            repo_pdf_path = f"docs/reports/{category}/{fname}"
                            local_blob_sha = _git_blob_sha(pdf_bytes)

                            # Checar se o arquivo já existe idêntico no remoto (apenas em envios pequenos <= 5)
                            remote_sha = cls._get_remote_file_sha(repo_pdf_path, token) if len(entries) <= 5 else None
                            if remote_sha and remote_sha == local_blob_sha:
                                logger.debug(f"[PortalSync] PDF '{fname}' já idêntico no GitHub (SHA {local_blob_sha[:8]}).")
                            else:
                                r_blob = requests.post(
                                    f"{base_api}/git/blobs",
                                    headers=headers,
                                    json={
                                        "content": base64.b64encode(pdf_bytes).decode("ascii"),
                                        "encoding": "base64",
                                    },
                                    timeout=90,
                                )
                                if r_blob.status_code not in (200, 201):
                                    logger.error(f"[PortalSync] Falha ao criar blob PDF '{fname}': HTTP {r_blob.status_code} {r_blob.text[:160]}")
                                    return False
                                blob_sha = r_blob.json()["sha"]
                                tree_entries.append({
                                    "path": repo_pdf_path,
                                    "mode": "100644",
                                    "type": "blob",
                                    "sha": blob_sha,
                                })
                                uploaded_pdfs += 1

                    # 4. Criar blob do índice JSON atualizado
                    index_payload = {
                        "drive_name": drive_name,
                        "category": category,
                        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "items_count": len(remote_items),
                        "items": remote_items,
                    }
                    index_bytes = json.dumps(index_payload, ensure_ascii=False, indent=2).encode("utf-8")
                    r_idx_blob = requests.post(
                        f"{base_api}/git/blobs",
                        headers=headers,
                        json={
                            "content": base64.b64encode(index_bytes).decode("ascii"),
                            "encoding": "base64",
                        },
                        timeout=45,
                    )
                    if r_idx_blob.status_code not in (200, 201):
                        logger.error(f"[PortalSync] Falha ao criar blob do índice '{category}': HTTP {r_idx_blob.status_code}")
                        return False

                    tree_entries.append({
                        "path": f"docs/reports/index_{category}.json",
                        "mode": "100644",
                        "type": "blob",
                        "sha": r_idx_blob.json()["sha"],
                    })

                    # 5. Criar nova Git Tree
                    r_tree = requests.post(
                        f"{base_api}/git/trees",
                        headers=headers,
                        json={"base_tree": base_tree_sha, "tree": tree_entries},
                        timeout=45,
                    )
                    if r_tree.status_code not in (200, 201):
                        logger.error(f"[PortalSync] Falha ao criar git tree: HTTP {r_tree.status_code} {r_tree.text[:160]}")
                        return False
                    new_tree_sha = r_tree.json()["sha"]

                    # 6. Criar novo Commit
                    if not commit_message:
                        if len(entries) == 1:
                            commit_message = f"chore(portal): publica relatorio {category} - {entries[0]['item']['name']}"
                        else:
                            commit_message = f"chore(portal): publica lote de {len(entries)} relatorios ({category})"

                    r_new_commit = requests.post(
                        f"{base_api}/git/commits",
                        headers=headers,
                        json={
                            "message": commit_message,
                            "tree": new_tree_sha,
                            "parents": [head_sha],
                        },
                        timeout=30,
                    )
                    if r_new_commit.status_code not in (200, 201):
                        logger.error(f"[PortalSync] Falha ao criar commit: HTTP {r_new_commit.status_code} {r_new_commit.text[:160]}")
                        return False
                    new_commit_sha = r_new_commit.json()["sha"]

                    # 7. Atualizar referência heads/main (non-fast-forward retorna 422 -> retry automático!)
                    r_patch = requests.patch(
                        f"{base_api}/git/refs/heads/{GITHUB_BRANCH}",
                        headers=headers,
                        json={"sha": new_commit_sha, "force": False},
                        timeout=30,
                    )
                    if r_patch.status_code == 200:
                        logger.info(
                            f"🌐 [PortalSync GitHub] Commit {new_commit_sha[:7]} publicado no Google Sites! "
                            f"Categoria: {category} | PDFs enviados: {uploaded_pdfs} | Total no índice: {len(remote_items)}"
                        )
                        return True
                    elif r_patch.status_code in (409, 422):
                        logger.warning(f"[PortalSync] Conflito de concorrência no branch main (tentativa {attempt+1}/4). Recarregando HEAD e mesclando...")
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    else:
                        logger.error(f"[PortalSync] Falha ao atualizar ref main: HTTP {r_patch.status_code} {r_patch.text[:180]}")
                        return False

                except Exception as e_gh:
                    logger.warning(f"[PortalSync] Exceção na publicação GitHub (tentativa {attempt+1}/4): {e_gh}")
                    time.sleep(1.5 * (attempt + 1))

        return False

    @classmethod
    def _save_local_index(cls, project_root: str, category: str, drive_name: str, items: List[Dict[str, Any]]) -> None:
        payload = {
            "drive_name": drive_name,
            "category": category,
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items_count": len(items),
            "items": items,
        }
        for root_sub in ("docs", "portal_web"):
            idx_dir = os.path.join(project_root, root_sub, "reports")
            os.makedirs(idx_dir, exist_ok=True)
            idx_path = os.path.join(idx_dir, f"index_{category}.json")
            with open(idx_path, "w", encoding="utf-8") as f_idx:
                json.dump(payload, f_idx, ensure_ascii=False, indent=2)

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
        canal: Optional[str] = None,
        publish_github: bool = True,
        defer_github_push: bool = False,
    ) -> bool:
        """
        Publica o PDF no repositório local (docs/reports/ e portal_web/reports/),
        atualiza o índice ao vivo docs/reports/index_<category>.json e o master data local,
        e envia automaticamente para o GitHub (que alimenta o Google Sites em tempo real).
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

            if os.path.abspath(pdf_path) != os.path.abspath(docs_file_path):
                shutil.copy2(pdf_path, docs_file_path)
            if os.path.abspath(pdf_path) != os.path.abspath(portal_file_path):
                shutil.copy2(pdf_path, portal_file_path)

            file_size = os.path.getsize(pdf_path)
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            new_item = cls._build_drive_item(
                target_filename=target_filename,
                category=category,
                file_size=file_size,
                now_iso=now_iso,
                partida=partida,
                campeonato=campeonato,
                plataforma=plataforma,
                confianca=confianca,
                data_hora=data_hora or "",
                auditado=auditado,
                placar=placar,
                canal=canal,
            )

            # 2. Atualizar config/sharepoint_portal_master_data.json local
            config_dir = os.path.join(project_root, "config")
            os.makedirs(config_dir, exist_ok=True)
            master_data_path = os.path.join(config_dir, "sharepoint_portal_master_data.json")

            if not os.path.exists(master_data_path):
                meipass = getattr(sys, "_MEIPASS", None)
                if meipass:
                    bundled_master = os.path.join(meipass, "config", "sharepoint_portal_master_data.json")
                    if os.path.exists(bundled_master):
                        try:
                            shutil.copy2(bundled_master, master_data_path)
                        except Exception as e_copy:
                            logger.warning(f"[PortalSync] Falha ao copiar master data do _MEIPASS: {e_copy}")

            if not os.path.exists(master_data_path):
                initial_data = {
                    "last_sync": datetime.now(timezone.utc).isoformat(),
                    "drives": {},
                    "lists": {},
                }
                with open(master_data_path, "w", encoding="utf-8") as f_init:
                    json.dump(initial_data, f_init, ensure_ascii=False, indent=2)

            with _GITHUB_PUBLISH_LOCK:
                with open(master_data_path, "r", encoding="utf-8") as f:
                    master_data = json.load(f)

                drives = master_data.setdefault("drives", {})
                drive = drives.setdefault(drive_name, {
                    "name": drive_name,
                    "drive_id": f"DRIVE_{category.upper()}",
                    "webUrl": f"https://sites.google.com/ibope.com/suportecaptacao/{drive_name}",
                    "items_count": 0,
                    "items": [],
                })

                items = drive.setdefault("items", [])
                cls._upsert_item_in_list(items, new_item)
                drive["items_count"] = len(items)

                # Atualizar também master_data["lists"][drive_name]
                lists_data = master_data.setdefault("lists", {})
                target_list_name = drive_name
                if target_list_name not in lists_data:
                    for k in lists_data.keys():
                        if k.replace(" ", "_").lower() == drive_name.replace(" ", "_").lower():
                            target_list_name = k
                            break

                list_entry = lists_data.setdefault(target_list_name, {
                    "name": target_list_name,
                    "displayName": target_list_name,
                    "columns": [],
                    "items": [],
                })
                list_items = list_entry.setdefault("items", [])
                f_obj = new_item["fields"]
                list_item_data = {
                    "Data_Hora": f_obj["Data_Hora"],
                    "Data_Partida": f_obj["Data_Hora"],
                    "Data_Jogo": f_obj["Data_Jogo"],
                    "Campeonato": f_obj["Campeonato"],
                    "Partida": f_obj["Partida"],
                    "Plataforma": f_obj["Plataforma"],
                    "Canal": f_obj["Canal"],
                    "Confianca": f_obj["Confiança"],
                    "Confiança": f_obj["Confiança"],
                    "Placar": f_obj["Placar"],
                    "Auditado": f_obj["Auditado"],
                    "Modified": now_iso,
                    "Created": now_iso,
                    "CriadoPor": "svc.captacao",
                    "ModificadoPor": "Monitor_Esportes Auto-Audit",
                    "Title": target_filename,
                    "FileLeafRef": target_filename,
                    "pdfUrl": new_item["webUrl"],
                    "webUrl": new_item["webUrl"],
                }

                found_list_item = False
                for idx, li in enumerate(list_items):
                    if li.get("Title") == target_filename or li.get("FileLeafRef") == target_filename:
                        list_items[idx].update(list_item_data)
                        found_list_item = True
                        break
                if not found_list_item:
                    list_items.insert(0, list_item_data)

                master_data["last_sync"] = now_iso
                with open(master_data_path, "w", encoding="utf-8") as f:
                    json.dump(master_data, f, ensure_ascii=False, indent=2)

                # Salvar índice JSON leve localmente
                cls._save_local_index(project_root, category, drive_name, items)
                local_items_snapshot = list(items)

            # 3. Publicar no GitHub (Google Sites Live) — imediato ou enfileirado para batch
            # Proteção contra testes unitários com arquivos dummy (< 500 bytes) poluindo produção
            is_dummy_test_file = (file_size < 500 and target_filename.lower().startswith("test_"))
            gh_ok = True
            if publish_github and not is_dummy_test_file:
                entry = {
                    "drive_name": drive_name,
                    "category": category,
                    "pdf_path": docs_file_path,
                    "item": new_item,
                }
                if defer_github_push:
                    with _GITHUB_PUBLISH_LOCK:
                        _PENDING_BATCHES.setdefault(category, []).append(entry)
                    logger.info(f"📦 [PortalSync] '{target_filename}' enfileirado para publicação em lote ({category}).")
                else:
                    gh_ok = cls._publish_entries_to_github_atomic(
                        category=category,
                        drive_name=drive_name,
                        entries=[entry],
                        local_fallback_items=local_items_snapshot,
                    )

            logger.info(
                f"🚀 [PortalSync] Relatório '{target_filename}' sincronizado no Portal Web ({drive_name}) | "
                f"Google Sites Live Push: {'OK' if gh_ok else 'PENDENTE/LOCAL'}"
            )
            return gh_ok if (publish_github and not defer_github_push) else True

        except Exception as e:
            logger.error(f"[PortalSync] Erro ao sincronizar relatório com portal web: {e}")
            return False

    @classmethod
    def flush_github_batch(cls, category: str) -> bool:
        """Publica todos os relatórios enfileirados (defer_github_push=True) em UM único commit atômico no GitHub."""
        with _GITHUB_PUBLISH_LOCK:
            entries = list(_PENDING_BATCHES.pop(category, []))
        if not entries:
            return True

        drive_name = entries[0]["drive_name"]
        project_root = get_project_root()
        local_items = []
        idx_local = os.path.join(project_root, "docs", "reports", f"index_{category}.json")
        if os.path.exists(idx_local):
            try:
                with open(idx_local, "r", encoding="utf-8") as f:
                    local_items = json.load(f).get("items") or []
            except Exception:
                pass

        return cls._publish_entries_to_github_atomic(
            category=category,
            drive_name=drive_name,
            entries=entries,
            local_fallback_items=local_items,
        )
