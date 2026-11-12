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
import re
import time
import socket
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable
from datetime import datetime, timedelta
import requests
import psutil

from .crypto_utils import get_base_dir, get_config_dir, get_config_value, get_app_path
from .cbf_pdf_service import prettify_match_name, is_cbf_broadcast_authorized

logger = logging.getLogger(__name__)

PORTUGUESE_NUMERIC_DT_RE = re.compile(
    r'(?:[A-Za-zçãéíóúâêô]+[-–]feira|[A-Za-zçãéíóúâêô]+),\s*(\d{1,2}/\d{1,2})\s+(\d{1,2}:\d{2})\s*(?:BRT)?',
    re.IGNORECASE
)
PORTUGUESE_LITERAL_DT_RE = re.compile(
    r'(?:[A-Za-zçãéíóúâêô]+[-–]feira|[A-Za-zçãéíóúâêô]+),\s*(\d{1,2})\s+de\s+([A-Za-zçãéíóúâêô.]+)\s+(\d{1,2}:\d{2})\s*(?:BRT)?',
    re.IGNORECASE
)
PRIME_DT_RE = re.compile(
    r'(?:[A-Za-z]+,\s*)?([A-Za-z]+)\s+(\d{1,2})\s+(\d{1,2}(?::\d{2})?\s*(?:AM|PM))',
    re.IGNORECASE
)

MONTH_MAP_PT = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
}

def extract_prime_datetime(text: str) -> str:
    """Extrai data/hora do Prime Video a partir de texto de card."""
    if not text:
        return ""
    m = PORTUGUESE_NUMERIC_DT_RE.search(text)
    if m:
        return m.group(0).strip()
    m = PORTUGUESE_LITERAL_DT_RE.search(text)
    if m:
        return m.group(0).strip()
    m = PRIME_DT_RE.search(text)
    if m:
        return m.group(0).strip()
    return ""

def format_datetime(data_str: str) -> Dict[str, str]:
    """Converte strings de data/hora vindas das plataformas para {'data': 'dd/mm/YYYY', 'hora': 'HH:MM'}."""
    if not data_str:
        return {"data": "", "hora": ""}
    
    clean = re.sub(r'\s+', ' ', data_str).replace('BRT', '').strip()
    agora = datetime.now()
    ano = agora.year

    # 1. Numérico PT: sábado, 1/08 17:00
    m1 = PORTUGUESE_NUMERIC_DT_RE.search(clean)
    if m1:
        dia_mes, hora = m1.group(1), m1.group(2)
        try:
            d, m = dia_mes.split('/')
            dt_obj = datetime(ano, int(m), int(d))
            if dt_obj.date() < (agora.date() - timedelta(days=60)):
                dt_obj = datetime(ano + 1, int(m), int(d))
            return {"data": dt_obj.strftime("%d/%m/%Y"), "hora": hora}
        except Exception:
            pass

    # 2. Literal PT: quarta-feira, 22 de jul. 18:50
    m2 = PORTUGUESE_LITERAL_DT_RE.search(clean)
    if m2:
        dia, mes_str, hora = m2.group(1), m2.group(2).lower()[:3], m2.group(3)
        m_num = MONTH_MAP_PT.get(mes_str, agora.month)
        try:
            dt_obj = datetime(ano, m_num, int(dia))
            if dt_obj.date() < (agora.date() - timedelta(days=60)):
                dt_obj = datetime(ano + 1, m_num, int(dia))
            return {"data": dt_obj.strftime("%d/%m/%Y"), "hora": hora}
        except Exception:
            pass

    # 3. Formato simples dd/mm/YYYY HH:MM
    m3 = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{1,2}:\d{2})', clean)
    if m3:
        d_raw, h_raw = m3.group(1), m3.group(2)
        try:
            parts = d_raw.split('/')
            if len(parts[2]) == 2:
                d_raw = f"{parts[0]}/{parts[1]}/20{parts[2]}"
            return {"data": d_raw, "hora": h_raw}
        except Exception:
            pass

    # 4. Formato Hoje / Amanhã
    if "hoje" in clean.lower():
        m_h = re.search(r'(\d{1,2}:\d{2})', clean)
        h = m_h.group(1) if m_h else "19:00"
        return {"data": agora.strftime("%d/%m/%Y"), "hora": h}
    if "amanhã" in clean.lower() or "amanha" in clean.lower():
        m_h = re.search(r'(\d{1,2}:\d{2})', clean)
        h = m_h.group(1) if m_h else "19:00"
        return {"data": (agora + timedelta(days=1)).strftime("%d/%m/%Y"), "hora": h}

    return {"data": agora.strftime("%d/%m/%Y"), "hora": "19:00"}


def verificar_chrome_debug(porta_debug: str = "9222") -> bool:
    """Verifica se o Chrome está aberto e respondendo na porta de depuração remota."""
    try:
        # Checagem ultrarrápida via socket (< 1ms)
        s = socket.create_connection(("127.0.0.1", int(porta_debug)), timeout=0.15)
        s.close()
    except Exception:
        return False

    url = f"http://127.0.0.1:{porta_debug}/json/version"
    try:
        resp = requests.get(url, timeout=0.8)
        return resp.status_code == 200
    except Exception:
        return False

def obter_profile_dir(porta_debug: str) -> Path:
    """
    Retorna o diretório de perfil do Chrome para a porta especificada.
    Garante suporte total para pastas TempProfile / TempProfile2 colocadas tanto
    dentro da pasta config/ quanto na pasta raiz do aplicativo.
    """
    base_dir = get_base_dir()
    cfg_dir = get_config_dir()
    porta_str = str(porta_debug).strip()

    if porta_str == "9222":
        candidates = [
            cfg_dir / "TempProfile",
            cfg_dir / "TempProfile1",
            base_dir / "TempProfile",
            base_dir / "TempProfile1",
            cfg_dir / "profiles_chrome" / "Esquerda_9222",
            base_dir / "profiles_chrome" / "Esquerda_9222",
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                logger.info(f"[Chrome] Utilizando perfil existente para 9222: {c}")
                return c
        target = cfg_dir / "TempProfile"
        target.mkdir(parents=True, exist_ok=True)
        return target
    else:
        candidates = [
            cfg_dir / "TempProfile2",
            base_dir / "TempProfile2",
            cfg_dir / "profiles_chrome" / "Direita_9224",
            base_dir / "profiles_chrome" / "Direita_9224",
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                logger.info(f"[Chrome] Utilizando perfil existente para 9224: {c}")
                return c
        target = cfg_dir / "TempProfile2"
        target.mkdir(parents=True, exist_ok=True)
        return target

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
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        shutil.which("chrome") or "",
        shutil.which("chrome.exe") or "",
    ]
    chrome_exe = None
    for cp in chrome_paths:
        if cp and os.path.exists(cp):
            chrome_exe = cp
            break

    if not chrome_exe:
        logger.error("[Chrome] Executável chrome.exe não encontrado no sistema.")
        return False

    # Limpa locks residuais se a porta não está ativa para evitar conflito de processo
    for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        try:
            lf = profile_dir / lock_name
            if lf.exists():
                lf.unlink(missing_ok=True)
        except Exception:
            pass

    cmd = [
        chrome_exe,
        "--remote-debugging-address=127.0.0.1",
        f"--remote-debugging-port={porta_debug}",
        f"--user-data-dir={str(profile_dir)}",
        "--profile-directory=Default",
        "--disable-features=SkipProfilePicker",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    try:
        logger.info(f"[Chrome] Iniciando: {' '.join(cmd)}")
        subprocess.Popen(cmd)
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

    chrome_options = Options()
    chrome_options.add_argument("--js-flags=--max_old_space_size=4096")
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{porta_debug}")
    
    try:
        # Usa Selenium 4 nativo com debuggerAddress
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        logger.warning(f"[Chrome] Falha ao conectar WebDriver direto: {e}. Tentando ChromeDriverManager...")
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)


# ── SCRAPERS DE PLATAFORMAS (AMAZON PRIME, DAZN, MAX, DISNEY) ─────────────────

def run_eventos_prime(url_camp: str, expected_camp: str = "Brasileirão serie A") -> List[Tuple[Any, ...]]:
    """Extrai eventos esportivos do Amazon Prime Video via navegador Chrome 9222 conectado."""
    eventos = []
    if not verificar_chrome_debug("9222"):
        if not abrir_chrome("9222"):
            logger.warning("[Prime] Não foi possível iniciar Chrome 9222.")
            return eventos

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        driver = obter_driver_conectado("9222")
        driver.get(url_camp)
        time.sleep(3.5)

        wait = WebDriverWait(driver, 10)
        uls = driver.find_elements(By.CSS_SELECTOR, "ul[data-testid='card-container-list']")
        if not uls:
            uls = driver.find_elements(By.TAG_NAME, "ul")

        cards = []
        for ul in uls[:2]:
            try:
                c = ul.find_elements(By.CSS_SELECTOR, "article[data-testid='card'], article[data-testid='super-carousel-card'], div[data-testid='card']")
                cards.extend(c)
            except Exception:
                pass

        logger.info(f"[Prime] Cards encontrados: {len(cards)}")
        for card in cards:
            try:
                card_text = card.text.strip()
                if not card_text:
                    continue
                
                # Ignora canais extras/Premiere
                if any(x in card_text.lower() for x in ["premiere", "combate", "telecine", "assine"]):
                    continue

                # Título
                nome_evento = card.get_attribute("data-card-title") or ""
                if not nome_evento:
                    for tag in ["h3", "h2", "span", "a"]:
                        elems = card.find_elements(By.TAG_NAME, tag)
                        for el in elems:
                            t = el.text.strip()
                            if " x " in t.lower() or " vs " in t.lower():
                                nome_evento = t
                                break
                        if nome_evento: break

                if not nome_evento:
                    # Tenta extrair da primeira linha do card_text
                    linhas = [l.strip() for l in card_text.split("\n") if l.strip()]
                    for l in linhas:
                        if " x " in l.lower() or " vs " in l.lower():
                            nome_evento = l
                            break

                if not nome_evento:
                    continue

                nome_limpo = prettify_match_name(nome_evento)
                if not is_cbf_broadcast_authorized(expected_camp, nome_limpo, "Amazon Prime"):
                    continue

                extracted_dt = extract_prime_datetime(card_text)
                dt_dict = format_datetime(extracted_dt)
                data_val = dt_dict.get("data") or datetime.now().strftime("%d/%m/%Y")
                hora_val = dt_dict.get("hora") or "19:00"

                url_card = ""
                try:
                    a_tag = card.find_element(By.CSS_SELECTOR, "a[href]")
                    url_card = a_tag.get_attribute("href") or ""
                except Exception:
                    pass

                tup = (expected_camp, nome_limpo, data_val, hora_val, "Esquerda", "15", "Amazon Prime", url_card)
                eventos.append(tup)
            except Exception as e_card:
                logger.warning(f"[Prime] Erro ao processar card: {e_card}")

    except Exception as e:
        logger.error(f"[Prime] Falha na busca Prime Video: {e}")

    return eventos


def run_eventos_dazn(url_camp: str, expected_camp: str = "Mundial de Clubes FIFA") -> List[Tuple[Any, ...]]:
    """Extrai eventos esportivos do DAZN via Chrome 9222."""
    eventos = []
    if not verificar_chrome_debug("9222"):
        if not abrir_chrome("9222"):
            return eventos

    from selenium.webdriver.common.by import By
    try:
        driver = obter_driver_conectado("9222")
        driver.get(url_camp)
        time.sleep(3.5)

        cards = driver.find_elements(By.CSS_SELECTOR, "article, div[data-testid*='event']")
        for card in cards:
            try:
                t = card.text.strip()
                if " x " in t.lower() or " vs " in t.lower():
                    linhas = [l.strip() for l in t.split("\n") if l.strip()]
                    jogo = prettify_match_name(linhas[0])
                    dt_dict = format_datetime(t)
                    tup = (expected_camp, jogo, dt_dict["data"], dt_dict["hora"], "Esquerda", "15", "Dazn", "")
                    eventos.append(tup)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[DAZN] Erro na raspagem DAZN: {e}")

    return eventos


def run_eventos_max(url_camp: str, expected_camp: str = "Campeonato Paulista") -> List[Tuple[Any, ...]]:
    """Extrai eventos do Max (HBO) via Chrome 9222."""
    eventos = []
    if not verificar_chrome_debug("9222"):
        if not abrir_chrome("9222"):
            return eventos

    from selenium.webdriver.common.by import By
    try:
        driver = obter_driver_conectado("9222")
        driver.get(url_camp)
        time.sleep(3.5)

        elems = driver.find_elements(By.CSS_SELECTOR, "div[data-testid*='tile'], article")
        for el in elems:
            try:
                t = el.text.strip()
                if " x " in t.lower() or " vs " in t.lower():
                    linhas = [l.strip() for l in t.split("\n") if l.strip()]
                    jogo = prettify_match_name(linhas[0])
                    dt_dict = format_datetime(t)
                    tup = (expected_camp, jogo, dt_dict["data"], dt_dict["hora"], "Esquerda", "15", "Max", "")
                    eventos.append(tup)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[Max] Erro na raspagem Max: {e}")

    return eventos


def run_eventos_disney(url_camp: str, expected_camp: str = "CONMEBOL Libertadores") -> List[Tuple[Any, ...]]:
    """Extrai eventos do Disney+ / Star+ via Chrome 9222."""
    eventos = []
    if not verificar_chrome_debug("9222"):
        if not abrir_chrome("9222"):
            return eventos

    from selenium.webdriver.common.by import By
    try:
        driver = obter_driver_conectado("9222")
        driver.get(url_camp)
        time.sleep(3.5)

        elems = driver.find_elements(By.CSS_SELECTOR, "div[data-testid*='card'], article")
        for el in elems:
            try:
                t = el.text.strip()
                if " x " in t.lower() or " vs " in t.lower():
                    linhas = [l.strip() for l in t.split("\n") if l.strip()]
                    jogo = prettify_match_name(linhas[0])
                    dt_dict = format_datetime(t)
                    tup = (expected_camp, jogo, dt_dict["data"], dt_dict["hora"], "Esquerda", "15", "Disney", "")
                    eventos.append(tup)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[Disney] Erro na raspagem Disney: {e}")

    return eventos


def executar_varredura_plataformas(plataformas_ativas: Dict[str, bool], campeonatos_ativos: Dict[str, bool]) -> List[Tuple[Any, ...]]:
    """
    Executa varredura automatizada no Chrome 9222 para todas as plataformas de streaming selecionadas.
    """
    todos_eventos = []
    
    # 1. Amazon Prime Video
    if plataformas_ativas.get("Amazon Prime"):
        logger.info("[Varredura] Coletando eventos do Amazon Prime Video...")
        if campeonatos_ativos.get("Brasileirão serie A"):
            url = "https://www.primevideo.com/tournament/amzn1.dv.icid.5a28c628-0310-42c0-8966-2f1f748488d3/ref=atv_hm_spo_c_NPzfck_2_1?jic=8%7CEgNhbGw%3D"
            todos_eventos.extend(run_eventos_prime(url, "Brasileirão serie A"))
        if campeonatos_ativos.get("Copa do Brasil"):
            url = "https://www.primevideo.com/tournament/amzn1.dv.icid.6e097abf-f4c9-4638-ba1e-7ff95367e1c8/ref=atv_hm_spo_c_NPzfck_2_2?jic=8%7CEgNhbGw%3D"
            todos_eventos.extend(run_eventos_prime(url, "Copa do Brasil"))

    # 2. DAZN
    if plataformas_ativas.get("Dazn"):
        logger.info("[Varredura] Coletando eventos do DAZN...")
        if campeonatos_ativos.get("Mundial de Clubes FIFA"):
            url = "https://www.dazn.com/pt-BR/competition/Competition:dc4k1xh2984zbypbnunk7ncic"
            todos_eventos.extend(run_eventos_dazn(url, "Mundial de Clubes FIFA"))

    # 3. Max
    if plataformas_ativas.get("Max"):
        logger.info("[Varredura] Coletando eventos do Max...")
        if campeonatos_ativos.get("Campeonato Paulista"):
            url = "https://play.hbomax.com/sport/event/paulistao"
            todos_eventos.extend(run_eventos_max(url, "Campeonato Paulista"))

    # 4. Disney+
    if plataformas_ativas.get("Disney"):
        logger.info("[Varredura] Coletando eventos do Disney+...")
        if campeonatos_ativos.get("CONMEBOL Libertadores"):
            url = "https://www.disneyplus.com/pt-br/browse/entity-1229387e-c683-4ef3-9f32-68824a7be427"
            todos_eventos.extend(run_eventos_disney(url, "CONMEBOL Libertadores"))
        if campeonatos_ativos.get("CONMEBOL Sudamericana"):
            url = "https://www.disneyplus.com/pt-br/browse/entity-7bf8f49c-cc47-4d42-9a85-587631faee03"
            todos_eventos.extend(run_eventos_disney(url, "CONMEBOL Sudamericana"))

    return todos_eventos
