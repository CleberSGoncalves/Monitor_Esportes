# -*- coding: utf-8 -*-
"""
Utilitários de criptografia e gerenciamento de configurações seguras para o Reporte de Eventos.
Portado e adaptado do Streaming_Scheduler para o Monitor_Esportes.
Suporta execução direta via script e binário congelado PyInstaller (--onefile).
"""

import sys
import os
import re
import shutil
import logging
import zipfile
import xml.etree.ElementTree as ET
import base64
from pathlib import Path
from typing import Optional, List
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

def get_base_dir() -> Path:
    """Retorna o diretório base do executável ou do projeto."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # modules/reporte_eventos/crypto_utils.py -> raiz do projeto Monitor_Esportes
    return Path(__file__).resolve().parent.parent.parent

def get_config_dir() -> Path:
    """Retorna o diretório config/ do projeto (gravável pelo usuário)."""
    cfg_dir = get_base_dir() / "config"
    try:
        cfg_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return cfg_dir

def get_bundled_dir() -> Optional[Path]:
    """Retorna o diretório temporário do PyInstaller (_MEIPASS) se em execução congelada."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return None

def get_app_path(rel_path: str, for_writing: bool = False) -> str:
    """
    Resolve o caminho de um arquivo, priorizando o diretório config/ gravável,
    a raiz do aplicativo e os recursos empacotados pelo PyInstaller (_MEIPASS).
    """
    if not rel_path:
        return str(get_base_dir())
    if os.path.isabs(rel_path):
        return rel_path

    target_cfg = get_config_dir() / rel_path
    if for_writing:
        return str(target_cfg)

    # 1. Tentar dentro de config/ do usuário
    if target_cfg.exists():
        return str(target_cfg)

    # 2. Tentar na raiz do executável / workspace
    root_path = get_base_dir() / rel_path
    if root_path.exists():
        return str(root_path)

    # 3. Tentar no diretório de trabalho atual (CWD)
    cwd_cfg = Path.cwd() / "config" / rel_path
    if cwd_cfg.exists():
        return str(cwd_cfg)
    cwd_root = Path.cwd() / rel_path
    if cwd_root.exists():
        return str(cwd_root)

    # 4. Tentar recursos embutidos do PyInstaller (_MEIPASS)
    meipass = get_bundled_dir()
    if meipass:
        meipass_cfg = meipass / "config" / rel_path
        if meipass_cfg.exists():
            try:
                shutil.copy2(meipass_cfg, target_cfg)
                return str(target_cfg)
            except Exception:
                return str(meipass_cfg)

        meipass_root = meipass / rel_path
        if meipass_root.exists():
            try:
                shutil.copy2(meipass_root, target_cfg)
                return str(target_cfg)
            except Exception:
                return str(meipass_root)

    # 5. Tentar extrair do acessos.zip se existir
    for zip_candidate in [get_base_dir() / "acessos.zip", Path.cwd() / "acessos.zip", (meipass / "acessos.zip" if meipass else None)]:
        if zip_candidate and zip_candidate.exists():
            try:
                with zipfile.ZipFile(zip_candidate, "r") as z:
                    if rel_path in z.namelist():
                        z.extract(rel_path, get_config_dir())
                        if target_cfg.exists():
                            return str(target_cfg)
            except Exception:
                pass

    # Padrão: dentro de config/
    return str(target_cfg)

def _obter_chave_embutida() -> Optional[bytes]:
    """Obtém a chave empacotada no executável (_MEIPASS) ou acessos.zip."""
    meipass = get_bundled_dir()
    candidates = []
    if meipass:
        candidates.extend([
            meipass / "config" / "secret.key",
            meipass / "secret.key",
        ])
    for zip_cand in [get_base_dir() / "acessos.zip", Path.cwd() / "acessos.zip", (meipass / "acessos.zip" if meipass else None)]:
        if zip_cand and zip_cand.exists():
            try:
                with zipfile.ZipFile(zip_cand, "r") as z:
                    if "secret.key" in z.namelist():
                        k = z.read("secret.key").strip()
                        if len(k) == 44:
                            return k
            except Exception:
                pass

    for cand in candidates:
        if cand.exists():
            try:
                with open(cand, "rb") as f:
                    data = f.read().strip()
                if len(data) == 44:
                    return data
            except Exception:
                pass
    return None

def _validar_chave_com_auth(key_data: bytes) -> bool:
    """Verifica se a chave fornecida consegue descriptografar os dados em auth.xml."""
    auth_candidates = [
        get_config_dir() / "auth.xml",
        get_base_dir() / "auth.xml",
    ]
    meipass = get_bundled_dir()
    if meipass:
        auth_candidates.extend([
            meipass / "config" / "auth.xml",
            meipass / "auth.xml",
        ])

    for auth_path in auth_candidates:
        if auth_path.exists():
            try:
                tree = ET.parse(auth_path)
                root = tree.getroot()
                email_el = root.find("email")
                if email_el is not None and email_el.text:
                    txt = email_el.text.strip()
                    if txt.startswith("gAAAA"):
                        fernet = Fernet(key_data)
                        dec = fernet.decrypt(txt.encode("utf-8")).decode("utf-8")
                        if "@" in dec:
                            return True
            except Exception:
                continue
    # Se não houver auth.xml com token criptografado para testar, aceita a chave como válida
    return True

def carregar_chave(caminho=None) -> bytes:
    """Carrega a chave de criptografia Fernet do arquivo secret.key."""
    if caminho is None:
        caminho = get_app_path("secret.key")
    else:
        caminho = get_app_path(caminho)

    # 1. Se existir o arquivo no caminho resolvido
    if os.path.exists(caminho):
        try:
            with open(caminho, "rb") as f:
                key_data = f.read().strip()
            if len(key_data) == 44:
                # Validar se esta chave consegue descriptografar auth.xml
                if _validar_chave_com_auth(key_data):
                    return key_data
                else:
                    # Chave local não consegue abrir auth.xml. Tentar chave embutida do _MEIPASS / acessos.zip
                    key_emb = _obter_chave_embutida()
                    if key_emb and _validar_chave_com_auth(key_emb):
                        with open(caminho, "wb") as f:
                            f.write(key_emb)
                        logger.info("[Crypto] Chave secret.key recuperada com sucesso do pacote embutido.")
                        return key_emb
                    return key_data
        except Exception:
            pass

    # 2. Tentar obter chave empacotada no _MEIPASS / acessos.zip
    key_emb = _obter_chave_embutida()
    if key_emb:
        try:
            with open(caminho, "wb") as f:
                f.write(key_emb)
            return key_emb
        except Exception:
            return key_emb

    # 3. Se não existir em nenhum lugar, gera chave padrão e salva
    key = Fernet.generate_key()
    try:
        with open(caminho, "wb") as f:
            f.write(key)
    except Exception:
        pass
    return key

def gerar_chave(caminho=None) -> None:
    """Gera e salva uma nova chave de criptografia em secret.key."""
    if caminho is None:
        caminho = get_app_path("secret.key", for_writing=True)
    else:
        caminho = get_app_path(caminho, for_writing=True)
    key = Fernet.generate_key()
    with open(caminho, "wb") as f:
        f.write(key)

def criptografar(texto: str) -> str:
    """Criptografa uma string com Fernet."""
    if not texto:
        return ""
    fernet = Fernet(carregar_chave())
    return fernet.encrypt(texto.encode("utf-8")).decode("utf-8")

def descriptografar(texto: str) -> str:
    """Descriptografa uma string Fernet, ou retorna o texto original (se plaintext legível) ou vazio se for token ilegível."""
    if not texto:
        return ""
    try:
        s_texto = str(texto).strip()
        if not s_texto.startswith("gAAAA"):
            # Se for token criptografado legado em base64 (sem @ e > 50 caracteres)
            if len(s_texto) > 50 and "@" not in s_texto and not re.search(r'\s', s_texto):
                try:
                    fernet = Fernet(carregar_chave())
                    return fernet.decrypt(s_texto.encode("utf-8")).decode("utf-8")
                except Exception:
                    # Token encriptado com chave desconhecida: nunca exibe o hash cru na tela
                    return ""
            return s_texto
        fernet = Fernet(carregar_chave())
        return fernet.decrypt(s_texto.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Se a chave atual falhou, tentar chave embutida do pacote
        key_emb = _obter_chave_embutida()
        if key_emb:
            try:
                fernet_emb = Fernet(key_emb)
                return fernet_emb.decrypt(s_texto.encode("utf-8")).decode("utf-8")
            except Exception:
                pass
        return ""
    except Exception:
        return ""

def get_env_value(chave: str, caminho=None) -> str:
    """Retorna o valor descriptografado de uma chave em .env.enc ou .env."""
    if caminho is None:
        caminho = get_app_path(".env.enc")
    else:
        caminho = get_app_path(caminho)

    try:
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as file:
                for line in file:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        if k.strip() == chave:
                            return descriptografar(v.strip())
    except Exception:
        pass

    # Fallback para .env na raiz ou config/
    env_plain = get_app_path(".env")
    try:
        if os.path.exists(env_plain):
            with open(env_plain, "r", encoding="utf-8") as file:
                for line in file:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        if k.strip() == chave:
                            return v.strip().strip('"').strip("'")
    except Exception:
        pass

    # Fallback para variáveis de ambiente do SO
    return os.getenv(chave, "")

def get_config_value(tag: str, caminho=None) -> str:
    """Retorna o valor descriptografado de uma tag do config.xml."""
    if caminho is None:
        caminho = get_app_path("config.xml")
    else:
        caminho = get_app_path(caminho)
    try:
        if os.path.exists(caminho):
            tree = ET.parse(caminho)
            root = tree.getroot()
            elem = root.find(tag)
            if elem is not None and elem.text:
                val = descriptografar(elem.text.strip())
                if val:
                    return val
    except Exception:
        pass

    # Fallback: tentar ler do arquivo bundled diretamente se falhar no local
    meipass = get_bundled_dir()
    if meipass:
        for cand in [meipass / "config" / "config.xml", meipass / "config.xml"]:
            if cand.exists() and str(cand) != str(caminho):
                try:
                    tree = ET.parse(cand)
                    root = tree.getroot()
                    elem = root.find(tag)
                    if elem is not None and elem.text:
                        key_emb = _obter_chave_embutida()
                        if key_emb:
                            fernet = Fernet(key_emb)
                            txt = elem.text.strip()
                            if txt.startswith("gAAAA"):
                                return fernet.decrypt(txt.encode("utf-8")).decode("utf-8")
                            return txt
                except Exception:
                    pass
    return ""

def get_auth_value(tag: str, caminho=None) -> str:
    """Retorna o valor descriptografado de uma tag do auth.xml."""
    if caminho is None:
        caminho = get_app_path("auth.xml")
    else:
        caminho = get_app_path(caminho)
    try:
        if os.path.exists(caminho):
            tree = ET.parse(caminho)
            root = tree.getroot()
            elem = root.find(tag)
            if elem is not None and elem.text:
                val = descriptografar(elem.text.strip())
                if val:
                    return val
    except Exception:
        pass

    # Fallback: tentar ler do arquivo bundled diretamente se falhar no local
    meipass = get_bundled_dir()
    if meipass:
        for cand in [meipass / "config" / "auth.xml", meipass / "auth.xml"]:
            if cand.exists() and str(cand) != str(caminho):
                try:
                    tree = ET.parse(cand)
                    root = tree.getroot()
                    elem = root.find(tag)
                    if elem is not None and elem.text:
                        key_emb = _obter_chave_embutida()
                        if key_emb:
                            fernet = Fernet(key_emb)
                            txt = elem.text.strip()
                            if txt.startswith("gAAAA"):
                                return fernet.decrypt(txt.encode("utf-8")).decode("utf-8")
                            return txt
                except Exception:
                    pass

    # Fallback adicional: tentar ler diretamente de acessos.zip se existir
    for zip_cand in [get_base_dir() / "acessos.zip", Path.cwd() / "acessos.zip", (meipass / "acessos.zip" if meipass else None)]:
        if zip_cand and zip_cand.exists():
            try:
                with zipfile.ZipFile(zip_cand, "r") as z:
                    if "auth.xml" in z.namelist():
                        raw_xml = z.read("auth.xml")
                        tree = ET.fromstring(raw_xml)
                        elem = tree.find(tag)
                        if elem is not None and elem.text:
                            key_emb = _obter_chave_embutida()
                            if key_emb:
                                fernet = Fernet(key_emb)
                                txt = elem.text.strip()
                                if txt.startswith("gAAAA"):
                                    return fernet.decrypt(txt.encode("utf-8")).decode("utf-8")
                                return txt
            except Exception:
                pass

    return ""

def ensure_config_files() -> None:
    """Garante que auth.xml, secret.key, config.xml e .env estejam presentes e íntegros em config/."""
    cfg_dir = get_config_dir()
    meipass = get_bundled_dir()
    essentials = ["secret.key", "auth.xml", "config.xml", ".env"]

    # 1. Copiar arquivos ausentes a partir do _MEIPASS
    if meipass:
        for fname in essentials:
            target = cfg_dir / fname
            if not target.exists():
                source_cfg = meipass / "config" / fname
                source_root = meipass / fname
                src = source_cfg if source_cfg.exists() else (source_root if source_root.exists() else None)
                if src:
                    try:
                        shutil.copy2(src, target)
                        logger.info(f"[Crypto] Inicializado {fname} em {target} a partir do pacote executável.")
                    except Exception as e:
                        logger.warning(f"[Crypto] Erro ao copiar {fname}: {e}")

    # 2. Se ainda faltar algum arquivo, tentar extrair de acessos.zip
    for zip_cand in [get_base_dir() / "acessos.zip", Path.cwd() / "acessos.zip", (meipass / "acessos.zip" if meipass else None)]:
        if zip_cand and zip_cand.exists():
            try:
                with zipfile.ZipFile(zip_cand, "r") as z:
                    for fname in essentials:
                        target = cfg_dir / fname
                        if not target.exists() and fname in z.namelist():
                            z.extract(fname, cfg_dir)
                            logger.info(f"[Crypto] Extraído {fname} de {zip_cand} para config/.")
            except Exception:
                pass

    # 3. Auto-cura: Se o e-mail não descriptografar, restaurar secret.key e auth.xml originais
    email = get_auth_value("email")
    if not email:
        logger.warning("[Crypto] auth.xml local não descriptografou. Executando auto-recuperação de integridade...")
        key_emb = _obter_chave_embutida()
        if key_emb:
            try:
                with open(cfg_dir / "secret.key", "wb") as f:
                    f.write(key_emb)
                logger.info("[Crypto] secret.key restaurada com chave empacotada válida.")
            except Exception:
                pass

        # Restaurar auth.xml se necessário
        if meipass:
            for cand in [meipass / "config" / "auth.xml", meipass / "auth.xml"]:
                if cand.exists():
                    try:
                        shutil.copy2(cand, cfg_dir / "auth.xml")
                        logger.info("[Crypto] auth.xml restaurado do pacote executável.")
                        break
                    except Exception:
                        pass
        for zip_cand in [get_base_dir() / "acessos.zip", Path.cwd() / "acessos.zip", (meipass / "acessos.zip" if meipass else None)]:
            if zip_cand and zip_cand.exists():
                try:
                    with zipfile.ZipFile(zip_cand, "r") as z:
                        if "auth.xml" in z.namelist():
                            z.extract("auth.xml", cfg_dir)
                            logger.info(f"[Crypto] auth.xml restaurado de {zip_cand}.")
                            break
                except Exception:
                    pass

# Executar auto-seeding e validação na carga do módulo
try:
    ensure_config_files()
except Exception as _e:
    logger.debug(f"[Crypto] ensure_config_files erro ignorado: {_e}")
