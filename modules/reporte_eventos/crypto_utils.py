# -*- coding: utf-8 -*-
"""
Utilitários de criptografia e gerenciamento de configurações seguras para o Reporte de Eventos.
Portado e adaptado do Streaming_Scheduler para o Monitor_Esportes.
"""

import sys
import os
import xml.etree.ElementTree as ET
import base64
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

def get_base_dir() -> Path:
    """Retorna o diretório base do executável ou do projeto."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # modules/reporte_eventos/crypto_utils.py -> raiz do projeto Monitor_Esportes
    return Path(__file__).resolve().parent.parent.parent

def get_config_dir() -> Path:
    """Retorna o diretório config/ do projeto."""
    cfg_dir = get_base_dir() / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir

def get_app_path(rel_path: str) -> str:
    """Resolve o caminho de um arquivo, priorizando o diretório config/ e depois a raiz."""
    if not rel_path:
        return str(get_base_dir())
    if os.path.isabs(rel_path):
        return rel_path
    
    # 1. Tentar dentro de config/
    cfg_path = get_config_dir() / rel_path
    if cfg_path.exists():
        return str(cfg_path)
    
    # 2. Tentar na raiz
    root_path = get_base_dir() / rel_path
    if root_path.exists():
        return str(root_path)
    
    # Padrão: dentro de config/
    return str(cfg_path)

def carregar_chave(caminho=None) -> bytes:
    """Carrega a chave de criptografia Fernet do arquivo secret.key."""
    if caminho is None:
        caminho = get_app_path("secret.key")
    else:
        caminho = get_app_path(caminho)
    
    if os.path.exists(caminho):
        with open(caminho, "rb") as f:
            return f.read().strip()
    
    # Se não existir, gera chave padrão e salva
    key = Fernet.generate_key()
    with open(caminho, "wb") as f:
        f.write(key)
    return key

def gerar_chave(caminho=None) -> None:
    """Gera e salva uma nova chave de criptografia em secret.key."""
    if caminho is None:
        caminho = get_app_path("secret.key")
    else:
        caminho = get_app_path(caminho)
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
        return ""
    except Exception as e:
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
    
    # Fallback para .env na raiz
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
                return descriptografar(elem.text.strip())
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
                return descriptografar(elem.text.strip())
    except Exception:
        pass
    return ""
