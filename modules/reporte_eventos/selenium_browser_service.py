# -*- coding: utf-8 -*-
"""
Serviço de gerenciamento do Google Chrome DevTools (portas 9222 e 9224)
e automação de scrapers Selenium para plataformas de streaming (Prime, Dazn, Max, Disney).

REGRAS DE SEGURANÇA:
- NUNCA executa taskkill /f /im chrome.exe indiscriminadamente.
- Filtra estritamente os processos Chrome pela porta de depuração ou diretório de profile.
"""

import os
import sys
import time
import socket
import logging
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
import requests
import psutil

from .crypto_utils import get_base_dir, get_config_value
from .cbf_pdf_service import prettify_match_name

logger = logging.getLogger(__name__)

def verificar_chrome_debug(porta_debug: str = "9222") -> bool:
    """Verifica se o Chrome está aberto e respondendo na porta de depuração remota."""
    url = f"http://127.0.0.1:{porta_debug}/json/version"
    try:
        resp = requests.get(url, timeout=2.5)
        return resp.status_code == 200
    except Exception:
        return False

def obter_profile_dir(porta_debug: str) -> Path:
    """Retorna o diretório isolado de perfil do Chrome para a porta especificada."""
    base = get_base_dir() / "profiles_chrome"
    base.mkdir(parents=True, exist_ok=True)
    if porta_debug == "9222":
        p = base / "Esquerda_9222"
    else:
        p = base / "Direita_9224"
    p.mkdir(parents=True, exist_ok=True)
    return p

def abrir_chrome(porta_debug: str = "9222") -> bool:
    """Abre o Chrome com depuração remota ativada na porta correspondente."""
    if verificar_chrome_debug(porta_debug):
        logger.info(f"[Chrome] Porta {porta_debug} já ativa.")
        return True

    profile_dir = obter_profile_dir(porta_debug)
    
    # Procura executável do Chrome padrão no Windows
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    chrome_exe = None
    for cp in chrome_paths:
        if os.path.exists(cp):
            chrome_exe = cp
            break

    if not chrome_exe:
        logger.error("[Chrome] Executável chrome.exe não encontrado no sistema.")
        return False

    cmd = [
        chrome_exe,
        f"--remote-debugging-port={porta_debug}",
        f"--user-data-dir={str(profile_dir)}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
    ]

    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Aguarda subida da porta
        for _ in range(12):
            time.sleep(0.5)
            if verificar_chrome_debug(porta_debug):
                logger.info(f"[Chrome] Conectado com sucesso na porta {porta_debug}!")
                return True
    except Exception as e:
        logger.error(f"[Chrome] Erro ao iniciar Chrome porta {porta_debug}: {e}")
    return False

def fechar_chrome_seguro(porta_debug: str) -> None:
    """
    Encerra estritamente a instância do Chrome rodando na porta especificada.
    JAMAIS afeta outros processos de navegadores no sistema.
    """
    logger.info(f"[Chrome] Encerrando com segurança processos na porta {porta_debug}...")
    try:
        porta_int = int(porta_debug)
        pids_alvo = set()

        # 1. Filtra por conexões locais na porta de debug
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == porta_int:
                if conn.pid:
                    pids_alvo.add(conn.pid)

        # 2. Filtra por linha de comando do Chrome
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if f"--remote-debugging-port={porta_debug}" in cmdline:
                    pids_alvo.add(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Encerra os processos estritamente identificados
        for pid in pids_alvo:
            try:
                p = psutil.Process(pid)
                p.terminate()
                p.wait(timeout=2.0)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"[Chrome] Erro no encerramento seguro da porta {porta_debug}: {e}")

def obter_driver_conectado(porta_debug: str = "9222"):
    """Cria e retorna uma instância do WebDriver conectado à porta remota."""
    if not verificar_chrome_debug(porta_debug):
        abrir_chrome(porta_debug)

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    chrome_options = Options()
    chrome_options.add_argument("--js-flags=--max_old_space_size=4096")
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{porta_debug}")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)
