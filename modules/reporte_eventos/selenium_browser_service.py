# -*- coding: utf-8 -*-
"""
Serviço de gerenciamento do Google Chrome DevTools (portas 9222 e 9224)
e automação de scrapers Selenium para plataformas de streaming (Prime Video, DAZN, Max, Disney+).

REGRAS DE SEGURANÇA E FIDELIDADE:
- NUNCA executa taskkill /f /im chrome.exe indiscriminadamente.
- Filtra estritamente os processos Chrome pela porta de depuração ou diretório de profile.
- 100% fiel e compatível com as rotinas de raspagem e autenticação do Streaming_Scheduler original.
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
from typing import Optional, List, Dict, Any, Tuple, Callable, Set
from datetime import datetime, timedelta
import requests
import psutil

try:
    from amazoncaptcha import AmazonCaptcha
except Exception:
    AmazonCaptcha = None

from .crypto_utils import get_base_dir, get_config_dir, get_config_value, get_auth_value, get_app_path
from .cbf_pdf_service import prettify_match_name, is_cbf_broadcast_authorized
from .sharepoint_client import _deep_normalize_partida, _obter_titulo_oficial_campeonato

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
    
    clean = re.sub(r'\s+', ' ', str(data_str)).replace('BRT', '').strip()
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


def tem_numeros(texto: str) -> bool:
    """Verifica se a string informada possui um ou mais números."""
    return any(char.isdigit() for char in str(texto))

def reduzir_minutos(minutos_a_subtrair: int) -> List[str]:
    """Retorna [data_atual_str, hora_atual_str] com minutos reduzidos."""
    agora = datetime.now()
    resultado = agora - timedelta(minutes=minutos_a_subtrair)
    return [resultado.strftime("%d/%m/%Y"), resultado.strftime("%H:%M")]

def converter_data_pt(data_str: str) -> str:
    """Converte datas abreviadas em português para formato numérico dd/mm/YYYY."""
    agora = datetime.now()
    clean = str(data_str).lower().strip()
    for mes_sigla, mes_num in MONTH_MAP_PT.items():
        if mes_sigla in clean:
            nums = re.findall(r'\d+', clean)
            dia = int(nums[0]) if nums else agora.day
            ano = agora.year
            try:
                dt = datetime(ano, mes_num, dia)
                if dt.date() < (agora.date() - timedelta(days=60)):
                    dt = datetime(ano + 1, mes_num, dia)
                return dt.strftime("%d/%m/%Y")
            except Exception:
                pass
    return agora.strftime("%d/%m/%Y")


# ── GERENCIAMENTO DE PROFILES E INSTÂNCIAS DO CHROME ─────────────────────────

def obter_profile_dir(porta_debug: str) -> Path:
    """
    Retorna o diretório de perfil do Chrome para a porta especificada.
    Garante suporte total para pastas TempProfile / TempProfile2 colocadas tanto
    dentro da pasta config/ quanto na pasta raiz do aplicativo ou de projetos irmãos.
    """
    base_dir = get_base_dir()
    cfg_dir = get_config_dir()
    cwd_dir = Path(os.getcwd())
    porta_str = str(porta_debug).strip()

    if porta_str == "9222":
        candidates = [
            cfg_dir / "TempProfile",
            base_dir / "TempProfile",
            cwd_dir / "TempProfile",
            Path(r"E:\desenvolvimento\Streaming_Scheduler\TempProfile"),
            Path(r"D:\MediaDNA_V2\Applications\Monitor_Esportes\config\TempProfile"),
            Path(r"D:\MediaDNA_V2\Applications\Monitor_Esportes\TempProfile"),
            cfg_dir / "TempProfile1",
            base_dir / "TempProfile1",
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
            cwd_dir / "TempProfile2",
            Path(r"E:\desenvolvimento\Streaming_Scheduler\TempProfile2"),
            Path(r"D:\MediaDNA_V2\Applications\Monitor_Esportes\config\TempProfile2"),
            Path(r"D:\MediaDNA_V2\Applications\Monitor_Esportes\TempProfile2"),
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                logger.info(f"[Chrome] Utilizando perfil existente para 9224: {c}")
                return c
        target = cfg_dir / "TempProfile2"
        target.mkdir(parents=True, exist_ok=True)
        return target


def verificar_chrome_debug(porta_debug: str = "9222") -> bool:
    """
    Verifica se há Chrome DevTools na porta:
      - Checagem socket rápida (< 1ms).
      - Retorna True somente quando /json/version responder HTTP 200 com webSocketDebuggerUrl.
    """
    try:
        porta = int(str(porta_debug).strip())
    except Exception:
        porta = 9222

    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=0.25) as s:
            s.settimeout(0.5)
            s.sendall(
                f"GET /json/version HTTP/1.1\r\nHost: 127.0.0.1:{porta}\r\nConnection: close\r\n\r\n".encode("ascii")
            )
            data = s.recv(8192)
        head, _, body = data.partition(b"\r\n\r\n")
        if b" 200 " in head and b"webSocketDebuggerUrl" in body:
            return True
    except Exception:
        pass

    return False


def abrir_chrome(porta_debug: str = "9222") -> bool:
    """
    Abre o Chrome com depuração remota ativada na porta correspondente.
    Exibe a janela visível no desktop do usuário para permitir acompanhamento.
    """
    if verificar_chrome_debug(porta_debug):
        logger.info(f"[Chrome] Porta {porta_debug} já ativa e pronta.")
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
        f"--user-data-dir={str(profile_dir.resolve())}",
        "--profile-directory=Default",
        "--disable-features=SkipProfilePicker",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    try:
        logger.info(f"[Chrome] Iniciando: {' '.join(cmd)}")
        subprocess.Popen(cmd)
        # Aguarda subida da porta (até 12 segundos)
        for _ in range(24):
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

        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == porta_int:
                if conn.pid:
                    pids_alvo.add(conn.pid)

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if f"--remote-debugging-port={porta_debug}" in cmdline:
                    pids_alvo.add(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

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
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        logger.warning(f"[Chrome] Falha ao conectar WebDriver direto: {e}. Tentando ChromeDriverManager...")
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)


def clicar_com_espera_segura(driver, xpath: str, timeout: int = 10):
    """Clica em um elemento com espera explícita e retry via JavaScript se interceptado."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException

    try:
        elemento = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView();", elemento)
        driver.execute_script("arguments[0].click();", elemento)
        return elemento
    except ElementClickInterceptedException:
        time.sleep(1)
        try:
            elemento = driver.find_element(By.XPATH, xpath)
            driver.execute_script("arguments[0].click();", elemento)
            return elemento
        except Exception:
            return None
    except TimeoutException:
        return None


# ── ROTINAS DE AUTENTICAÇÃO DAS PLATAFORMAS (FIDELIDADE STREAMING_SCHEDULER) ──

def loginprime(url: str, us: str, passw: str, driver, tempo: int = 10, evento: str = "Novos") -> None:
    """Realiza verificação de autenticação e login no Amazon Prime Video."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException

    try:
        if len(driver.find_elements(By.XPATH, '//*[@id="ap_email"]')) > 0:
            logger.info("[Prime] Tela de login detectada. Preenchendo credenciais...")
            user_el = driver.find_element(By.XPATH, '//*[@id="ap_email"]')
            t = user_el.get_attribute("value") or ""
            tuser = "+55" + str(us)
            tuser2 = "55" + str(us)
            if t == tuser or t == tuser2:
                user_el.send_keys(Keys.ENTER)
            else:
                time.sleep(3)
                user_el.clear()
                time.sleep(1)
                user_el.send_keys(tuser)
                time.sleep(2)
                t_atual = user_el.get_attribute("value") or ""
                if tem_numeros(t_atual):
                    user_el.clear()
                    novo_valor = t_atual.replace("+55", "", 1)
                    user_el.send_keys(novo_valor)
                user_el.send_keys(Keys.ENTER)
                time.sleep(3)

            # Desafio Captcha
            try:
                clicar_com_espera_segura(driver, '//*[@id="aa-challenge-whole-page-iframe"]', timeout=3)
            except Exception:
                pass

            if len(driver.find_elements(By.XPATH, '//*[@id="aa_amazon_image_captcha"]')) > 0 and AmazonCaptcha:
                try:
                    link = driver.find_element(By.XPATH, '//*[@id="aa_amazon_image_captcha"]').get_attribute('src')
                    catcha = AmazonCaptcha.fromlink(link)
                    captcha_val = AmazonCaptcha.solve(catcha)
                    driver.find_element(By.ID, "aa_captcha_input").send_keys(captcha_val)
                    driver.find_element(By.CLASS_NAME, "a-button-input").click()
                    time.sleep(2)
                except Exception as e_cap:
                    logger.warning(f"[Prime] Erro ao resolver Captcha: {e_cap}")
            else:
                driver.switch_to.default_content()
                lembrar = driver.find_elements(By.XPATH, '//*[@id="authportal-main-section"]//input[@type="checkbox"]')
                if lembrar:
                    try:
                        lembrar[0].click()
                    except Exception:
                        pass

            pas_el = driver.find_elements(By.XPATH, '//*[@id="ap_password"]')
            if pas_el:
                pas_el[0].clear()
                pas_el[0].send_keys(passw)
                pas_el[0].send_keys(Keys.ENTER)
                time.sleep(3)

        # Navega para a URL da competição
        driver.get(url)
        time.sleep(3)

        # Checa necessidade de reautenticação
        if len(driver.find_elements(By.XPATH, '//*[@id="pv-nav-container"]/div/div[2]/ul/li[5]/a')) > 0:
            time.sleep(2)
            try:
                driver.find_element(By.XPATH, '//*[@id="pv-nav-container"]/div/div[2]/ul/li[5]/a').click()
                time.sleep(2)
                loginprime(url, us, passw, driver, tempo, evento)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[Prime] Aviso no fluxo de login Prime Video: {e}")


def resolve_banners_Dazn(driver) -> None:
    """Fecha modais e banners promocionais na página do DAZN."""
    from selenium.webdriver.common.by import By
    try:
        banner = driver.find_elements(By.CLASS_NAME, 'content-promotion__modal-close___2MB1S')
        if banner:
            banner[0].click()
        banner2 = driver.find_elements(By.XPATH, '//*[@id="notification-layer"]/div/div/div[1]/div/div[5]/div[2]/button')
        if banner2:
            banner2[0].click()
    except Exception:
        pass


def logindazn(url: str, email: str, senha: str, driver, timeantes: int, evento: str) -> None:
    """Efetua login no DAZN se necessário."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        driver.get("https://www.dazn.com/pt-BR/account/content/dazn/signup?signin=true&page=emailDetails")
        time.sleep(4)
        resolve_banners_Dazn(driver)

        btn_cookie = driver.find_elements(By.XPATH, '//*[@id="onetrust-accept-btn-handler"]')
        if btn_cookie:
            try:
                btn_cookie[0].click()
            except Exception:
                pass

        inp_email = driver.find_elements(By.ID, "email")
        if inp_email and email:
            inp_email[0].clear()
            inp_email[0].send_keys(email)
            inp_email[0].send_keys(Keys.ENTER)
            time.sleep(3)

        inp_pass = driver.find_elements(By.ID, "password")
        if inp_pass and senha:
            inp_pass[0].clear()
            inp_pass[0].send_keys(senha)
            inp_pass[0].send_keys(Keys.ENTER)
            time.sleep(3)

        driver.get(url)
        time.sleep(3)
    except Exception as e:
        logger.warning(f"[DAZN] Aviso no login DAZN: {e}")


def obter_eventos_dazn_completo(driver) -> List[Dict[str, str]]:
    """Percorre os carrosséis da página do DAZN coletando partidas."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains

    eventos = []
    titulos_ja_adicionados = set()

    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.4);")
        time.sleep(2)
        resolve_banners_Dazn(driver)

        for _ in range(20):
            artigos = driver.find_elements(
                By.XPATH,
                '//h2[contains(text(), "A seguir")]/ancestor::div[contains(@class, "rail__rail-title")]/following-sibling::div//article'
            )
            if not artigos:
                artigos = driver.find_elements(By.CSS_SELECTOR, "article, div[data-testid*='event']")

            for artigo in artigos:
                try:
                    titulo = ""
                    for tag in ("h4", "h3", "span"):
                        elems = artigo.find_elements(By.TAG_NAME, tag)
                        if elems and elems[0].text.strip():
                            titulo = elems[0].text.strip()
                            break

                    link_tag = artigo.find_elements(By.CSS_SELECTOR, 'a')
                    url_evento = link_tag[0].get_attribute('href') if link_tag else ""
                    horario = artigo.text.strip()

                    if titulo and (" x " in titulo.lower() or " vs " in titulo.lower()):
                        if titulo not in titulos_ja_adicionados:
                            dt_dict = format_datetime(horario)
                            eventos.append({
                                "Campeonato": "Mundial de Clubes FIFA",
                                "Jogo": titulo,
                                "Data/hora": f"{dt_dict['data']} {dt_dict['hora']}",
                                "URL": url_evento
                            })
                            titulos_ja_adicionados.add(titulo)
                except Exception:
                    continue

            seta = driver.find_elements(By.XPATH, "//button[contains(@class, 'slick-next')]")
            if not seta:
                break
            try:
                ActionChains(driver).move_to_element(seta[0]).click().perform()
                time.sleep(2.5)
            except Exception:
                break
    except Exception as e:
        logger.warning(f"[DAZN] Erro ao obter eventos DAZN: {e}")

    return eventos


def rolar_cards_proximos_eventos(driver, max_clicks: int = 40, wait_time: float = 0.8) -> None:
    """Força o carregamento TOTAL do rail do Max clicando na seta e forçando repaint."""
    from selenium.webdriver.common.by import By

    for _ in range(max_clicks):
        try:
            btn = driver.find_element(By.CSS_SELECTOR, 'button[data-position="forward"]')
            if not btn.is_displayed():
                break
            driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", btn)
            time.sleep(0.2)
            driver.execute_script("arguments[0].click();", btn)
            driver.execute_script("window.dispatchEvent(new Event('resize'));")
            time.sleep(wait_time)
        except Exception:
            break


def ler_tile_max_com_retry(a_tag, tentativas: int = 5, delay: float = 0.3) -> Optional[Dict[str, str]]:
    """Lê um tile esportivo do Max lidando com virtualização do rail."""
    from selenium.webdriver.common.by import By

    for _ in range(tentativas):
        try:
            url = a_tag.get_attribute("href")
            badge = a_tag.find_elements(By.CSS_SELECTOR, 'span[class*="StyledBadgeText"]')
            if not badge:
                continue
            data_hora = badge[0].text.strip()
            titulo_el = a_tag.find_elements(By.CSS_SELECTOR, 'span[class*="StyledPrimaryTitle"]')
            if not titulo_el:
                continue
            titulo = titulo_el[0].text.strip()
            return {"url": url, "data_hora": data_hora, "titulo": titulo}
        except Exception:
            time.sleep(delay)
    return None


def loginmax(url_plataform: str, url: str, us: str, passw: str, driver, tempo: int, evento: str) -> None:
    """Autenticação no Max com suporte a Shadow DOM."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    try:
        driver.get(url_plataform)
        time.sleep(5)
        user = driver.execute_script("""
            const giLogin = document.querySelector('gi-login');
            if (!giLogin || !giLogin.shadowRoot) return null;
            const emailComp = giLogin.shadowRoot.querySelector('gi-sign-in-email');
            if (!emailComp || !emailComp.shadowRoot) return null;
            return emailComp.shadowRoot.querySelector('#sign-in-email-input');
        """)
        if user and us:
            driver.execute_script("arguments[0].value = '';", user)
            user.send_keys(us)
            user.send_keys(Keys.ENTER)
            time.sleep(5)

        pwd = driver.execute_script("""
            const giLogin = document.querySelector("gi-login");
            if (!giLogin || !giLogin.shadowRoot) return null;
            const passStep = giLogin.shadowRoot.querySelector("gi-sign-in-password");
            if (!passStep || !passStep.shadowRoot) return null;
            const pwdComp = passStep.shadowRoot.querySelector("gi-password-input");
            if (!pwdComp || !pwdComp.shadowRoot) return null;
            return pwdComp.shadowRoot.querySelector('input[type="password"]');
        """)
        if pwd and passw:
            driver.execute_script("arguments[0].value = '';", pwd)
            pwd.send_keys(passw)
            pwd.send_keys(Keys.ENTER)
            time.sleep(5)
        driver.get(url)
    except Exception as e:
        logger.warning(f"[Max] Aviso no login Max: {e}")


def logindisney(url: str, us: str, passw: str, driver, tempo: int, evento: str) -> None:
    """Autenticação no Disney+."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    try:
        time.sleep(3)
        if len(driver.find_elements(By.XPATH, '//*[@id="email"]')) > 0 and us:
            user_el = driver.find_element(By.XPATH, '//*[@id="email"]')
            user_el.clear()
            user_el.send_keys(us)
            user_el.send_keys(Keys.ENTER)
            time.sleep(4)

        if len(driver.find_elements(By.XPATH, '//*[@id="password"]')) > 0 and passw:
            pas_el = driver.find_element(By.XPATH, '//*[@id="password"]')
            pas_el.clear()
            pas_el.send_keys(passw)
            pas_el.send_keys(Keys.ENTER)
            time.sleep(4)

        driver.get(url)
        time.sleep(4)
    except Exception as e:
        logger.warning(f"[Disney] Aviso no login Disney+: {e}")


# ── SCRAPERS COMPLETOS DAS PLATAFORMAS (STREAMING_SCHEDULER ORIGINAL) ────────

def run_eventos_prime(url_camp: str, expected_camp: str = "Brasileirão serie A") -> List[Tuple[Any, ...]]:
    """
    Extrai eventos esportivos do Amazon Prime Video via navegador Chrome 9222 conectado.
    Implementação 100% fiel à função run_eventos_prime do Streaming_Scheduler.
    """
    eventos: List[Tuple[Any, ...]] = []
    if not verificar_chrome_debug("9222"):
        if not abrir_chrome("9222"):
            logger.warning("[Prime] Não foi possível iniciar Chrome 9222.")
            return eventos

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        driver = obter_driver_conectado("9222")
        us = get_config_value("usuario_prime") or ""
        pas = get_config_value("senha_prime") or ""
        url_plataform = "https://www.primevideo.com/offers/nonprimehomepage/ref=atv_auth_signout"

        driver.get(url_plataform)
        loginprime(url_camp, us, pas, driver, 10, "Novos")

        wait = WebDriverWait(driver, 15)
        try:
            uls = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul[data-testid='card-container-list']"))
            )
        except Exception:
            uls = driver.find_elements(By.TAG_NAME, "ul")

        if not uls:
            logger.warning("[Prime] Nenhuma lista de cards encontrada na página.")
            return eventos

        valid_uls = []
        for u_idx, ul in enumerate(uls):
            title_text = ""
            try:
                parent_shelf = ul.find_element(By.XPATH, "./ancestor::section[1] | ./ancestor::div[contains(@class, 'carousel') or contains(@class, 'shelf')][1]")
                for tag in ("h2", "h3", "span"):
                    headers = parent_shelf.find_elements(By.TAG_NAME, tag)
                    for h in headers:
                        if h.text.strip():
                            title_text = h.text.strip()
                            break
                    if title_text:
                        break
            except Exception:
                pass

            title_lower = title_text.lower()
            blacklist = ["repetições", "repetição", "replays", "replay", "equipes", "equipas", "destaques", "melhores", "momento", "highlights", "excluir", "ligas", "liga", "teams", "times", "terminadas", "encerrados", "recentemente", "concluídos", "concluidos", "premiere", "combo", "upgrade"]
            if any(w in title_lower for w in blacklist):
                continue
            valid_uls.append((ul, title_text))

        # Restringe busca à lista principal superior ("Seus eventos ao vivo e próximos eventos")
        if valid_uls:
            valid_uls = valid_uls[:1]

        for ul, title in valid_uls:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ul)
                time.sleep(0.5)
            except Exception:
                pass

        cards = []
        for ul, title in valid_uls:
            try:
                ul_cards = ul.find_elements(By.CSS_SELECTOR, "article[data-testid='card'], article[data-testid='super-carousel-card']")
                cards.extend(ul_cards)
            except Exception:
                pass

        logger.info(f"[Prime] Total de cards encontrados: {len(cards)}")

        var_navegador = "Esquerda"
        for idx, card in enumerate(cards):
            card_text_raw = ""
            try:
                card_text_raw = card.text.strip().lower()
            except Exception:
                pass

            # Ignora canais extras/Premiere
            if any(ch in card_text_raw for ch in ["premiere", "subscreva", "assine", "store filled", "combate", "paramount", "telecine"]):
                continue

            nome_evento = card.get_attribute("data-card-title") or ""
            if not nome_evento.strip():
                try:
                    nome_evento = card.find_element(By.CSS_SELECTOR, "a[aria-label]").get_attribute("aria-label") or ""
                except Exception:
                    pass
            if not nome_evento.strip():
                try:
                    nome_evento = card.find_element(By.CSS_SELECTOR, "img[alt]").get_attribute("alt") or ""
                except Exception:
                    pass
            if not nome_evento.strip():
                try:
                    nome_evento = card.find_element(By.CSS_SELECTOR, "a._3HZFFn").text.strip()
                except Exception:
                    pass

            if "premiere" in nome_evento.lower():
                continue

            data_hora = ""
            for selector in ("p.qKxeGx", "p.GNymT4"):
                try:
                    data_hora_el = card.find_element(By.CSS_SELECTOR, selector)
                    data_hora = data_hora_el.text.strip()
                    break
                except Exception:
                    pass

            if not data_hora:
                try:
                    data_hora = card.text.strip()
                except Exception:
                    pass

            extracted = extract_prime_datetime(data_hora)
            if not extracted:
                continue

            data_hora_formatada = format_datetime(extracted)
            dt = data_hora_formatada.get('data', '')
            hr = data_hora_formatada.get('hora', '19:00')

            url = ""
            try:
                a_tags = card.find_elements(By.CSS_SELECTOR, "a[href]")
                if a_tags:
                    url = a_tags[0].get_attribute("href") or ""
            except Exception:
                pass

            if not url:
                try:
                    url = card.get_attribute("href") or ""
                except Exception:
                    pass

            if url.startswith("/"):
                url = "https://www.primevideo.com" + url

            if nome_evento.strip() and dt:
                jogo_limpo = prettify_match_name(nome_evento)
                if not is_cbf_broadcast_authorized(expected_camp, jogo_limpo, "Amazon Prime"):
                    logger.info(f"[Prime] Jogo '{jogo_limpo}' descartado: sem direitos na tabela CBF para Amazon Prime.")
                    continue

                csv_row = (expected_camp, jogo_limpo, dt, hr, var_navegador, "10", "Amazon Prime", url)
                eventos.append(csv_row)
                var_navegador = "Direita" if var_navegador == "Esquerda" else "Esquerda"

        # Paginação: avança mais títulos se disponível
        try:
            for _ in range(3):
                btns = driver.find_elements(By.XPATH, '//button[@aria-label="next 3 titles"]')
                if btns:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btns[0])
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", btns[0])
                    time.sleep(1.2)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"[Prime] Falha na busca Prime Video: {e}")

    return eventos


def run_eventos_dazn(url_camp: str, expected_camp: str = "Mundial de Clubes FIFA") -> List[Tuple[Any, ...]]:
    """Extrai eventos do DAZN conectando ao Chrome 9222."""
    eventos: List[Tuple[Any, ...]] = []
    if not verificar_chrome_debug("9222"):
        if not abrir_chrome("9222"):
            return eventos

    try:
        driver = obter_driver_conectado("9222")
        us = get_config_value("usuario_dazn") or ""
        pas = get_config_value("senha_dazn") or ""

        logindazn(url_camp, us, pas, driver, 10, "Novos")
        evs = obter_eventos_dazn_completo(driver)

        var_nav = "Esquerda"
        for ev in evs:
            jogo = re.sub(r'\s+[vVxX]\s+', ' x ', ev["Jogo"]).upper()
            dt_dict = format_datetime(ev["Data/hora"])
            tup = (expected_camp, prettify_match_name(jogo), dt_dict["data"], dt_dict["hora"], var_nav, "15", "Dazn", ev["URL"])
            eventos.append(tup)
            var_nav = "Direita" if var_nav == "Esquerda" else "Esquerda"
    except Exception as e:
        logger.error(f"[DAZN] Erro na busca DAZN: {e}")

    return eventos


def run_eventos_max(url_camp: str, expected_camp: str = "Campeonato Paulista") -> List[Tuple[Any, ...]]:
    """Extrai eventos do Campeonato Paulista no Max (HBO) via Chrome 9222."""
    eventos: List[Tuple[Any, ...]] = []
    if not verificar_chrome_debug("9222"):
        if not abrir_chrome("9222"):
            return eventos

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        driver = obter_driver_conectado("9222")
        driver.get(url_camp)
        time.sleep(4)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a[data-testid$="_tile"]'))
            )
        except Exception:
            pass

        rolar_cards_proximos_eventos(driver, max_clicks=30)
        time.sleep(1.5)

        tiles = driver.find_elements(By.CSS_SELECTOR, 'a[data-testid$="_tile"]')
        logger.info(f"[Max] Tiles encontrados: {len(tiles)}")

        urls_proc = set()
        var_nav = "Esquerda"
        for a_tag in tiles:
            info = ler_tile_max_com_retry(a_tag)
            if not info:
                continue

            url = info["url"]
            if url.startswith("/"):
                url = "https://play.hbomax.com" + url

            if url in urls_proc:
                continue
            urls_proc.add(url)

            data_fmt = format_datetime(info["data_hora"])
            dt = data_fmt.get("data", "")
            hr = data_fmt.get("hora", "19:00")
            if not dt:
                continue

            titulo = re.sub(r"\s+Rodada\s+\d+.*$", "", info["titulo"], flags=re.IGNORECASE).strip()
            titulo = re.sub(r'\s+[vVxX]\s+', ' x ', titulo)

            row = (expected_camp, prettify_match_name(titulo), dt, hr, var_nav, "10", "TNT_SPORTS", url)
            eventos.append(row)
            var_nav = "Direita" if var_nav == "Esquerda" else "Esquerda"

    except Exception as e:
        logger.error(f"[Max] Erro na busca Max: {e}")

    return eventos


def run_eventos_disney(url_camp: str, expected_camp: Optional[str] = "CONMEBOL Libertadores") -> List[Tuple[Any, ...]]:
    """Extrai eventos esportivos do Disney+ via Chrome 9222."""
    eventos: List[Tuple[Any, ...]] = []
    if not verificar_chrome_debug("9222"):
        if not abrir_chrome("9222"):
            return eventos

    from selenium.webdriver.common.by import By

    try:
        driver = obter_driver_conectado("9222")
        us = get_config_value("usuario_disney") or ""
        pas = get_config_value("senha_disney") or ""

        logindisney(url_camp, us, pas, driver, 10, "Novos")
        time.sleep(4)

        c1 = driver.find_elements(By.XPATH, '//*[@class="_192jb2w9 xgfbc11x2 ordv7e0"]')
        var_nav = "Esquerda"

        if c1:
            for rail in c1:
                try:
                    c2 = rail.find_elements(By.CSS_SELECTOR, 'div')
                    for j in range(len(c2)):
                        btn_fwd = driver.find_elements(By.XPATH, '//*[@id="explore-ui-main-content-container"]//button[2]')
                        if btn_fwd:
                            try:
                                driver.execute_script("arguments[0].click();", btn_fwd[0])
                            except Exception:
                                pass

                        cards = c2[j].find_elements(By.XPATH, '//*[@class="_192jb2wb _2b0dm73"]')
                        for cd in cards:
                            items = cd.find_elements(By.XPATH, '//*[@class="_1o25tbf1 xgfbc1w2"]')
                            for it in items:
                                lines = [l.strip() for l in it.text.split("\n") if l.strip()]
                                if len(lines) >= 2:
                                    dt_dict = format_datetime(lines[0])
                                    evento_nome = lines[1]
                                    a_tags = it.find_elements(By.TAG_NAME, "a")
                                    url_d = a_tags[0].get_attribute("href") if a_tags else ""

                                    camp_d = expected_camp or "Disney"
                                    row = (camp_d, prettify_match_name(evento_nome), dt_dict["data"], dt_dict["hora"], var_nav, "0", "Disney", url_d)
                                    eventos.append(row)
                                    var_nav = "Direita" if var_nav == "Esquerda" else "Esquerda"
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"[Disney] Erro na busca Disney: {e}")

    return eventos


def executar_varredura_plataformas(
    plataformas_ativas: Dict[str, bool],
    campeonatos_ativos: Dict[str, bool],
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> List[Tuple[Any, ...]]:
    """
    Executa varredura automatizada no Chrome 9222 para todas as plataformas de streaming selecionadas.
    """
    todos_eventos = []

    # 1. DAZN
    if plataformas_ativas.get("Dazn"):
        if progress_callback:
            progress_callback("Coletando eventos do DAZN...", 0.15)
        if campeonatos_ativos.get("Mundial de Clubes FIFA"):
            url = "https://www.dazn.com/pt-BR/competition/Competition:dc4k1xh2984zbypbnunk7ncic"
            todos_eventos.extend(run_eventos_dazn(url, "Mundial de Clubes FIFA"))

    # 2. Amazon Prime Video
    if plataformas_ativas.get("Amazon Prime"):
        if progress_callback:
            progress_callback("Buscando Amazon Prime Video (Brasileirão Série A)...", 0.30)
        if campeonatos_ativos.get("Brasileirão serie A") or campeonatos_ativos.get("Brasileirão Série A"):
            url = "https://www.primevideo.com/tournament/amzn1.dv.icid.5a28c628-0310-42c0-8966-2f1f748488d3/ref=atv_hm_spo_c_NPzfck_2_1?jic=8%7CEgNhbGw%3D"
            todos_eventos.extend(run_eventos_prime(url, "Brasileirão serie A"))
        if progress_callback:
            progress_callback("Buscando Amazon Prime Video (Copa do Brasil)...", 0.45)
        if campeonatos_ativos.get("Copa do Brasil"):
            url = "https://www.primevideo.com/tournament/amzn1.dv.icid.6e097abf-f4c9-4638-ba1e-7ff95367e1c8/ref=atv_hm_spo_c_NPzfck_2_2?jic=8%7CEgNhbGw%3D"
            todos_eventos.extend(run_eventos_prime(url, "Copa do Brasil"))

    # 3. Max
    if plataformas_ativas.get("Max"):
        if progress_callback:
            progress_callback("Coletando eventos do Max (Campeonato Paulista)...", 0.60)
        if campeonatos_ativos.get("Campeonato Paulista"):
            url = "https://play.hbomax.com/sport/event/paulistao"
            todos_eventos.extend(run_eventos_max(url, "Campeonato Paulista"))

    # 4. Disney+
    if plataformas_ativas.get("Disney"):
        if progress_callback:
            progress_callback("Coletando eventos do Disney+...", 0.70)
        if campeonatos_ativos.get("CONMEBOL Libertadores"):
            url = "https://www.disneyplus.com/pt-br/browse/entity-1229387e-c683-4ef3-9f32-68824a7be427"
            todos_eventos.extend(run_eventos_disney(url, "CONMEBOL Libertadores"))
        if campeonatos_ativos.get("CONMEBOL Sudamericana"):
            url = "https://www.disneyplus.com/pt-br/browse/entity-7bf8f49c-cc47-4d42-9a85-587631faee03"
            todos_eventos.extend(run_eventos_disney(url, "CONMEBOL Sudamericana"))

    return todos_eventos


# ── ROTINAS DE PADRONIZAÇÃO, DEDUPLICAÇÃO E ORDENAÇÃO DE GRADE ───────────────

def padronizar_nomes_grid(tree) -> None:
    """Varre todo o grid e substitui nomes de partidas e campeonatos pelos nomes canônicos e oficiais."""
    try:
        for item in tree.get_children():
            values = list(tree.item(item, 'values'))
            changed = False
            if len(values) > 0 and _obter_titulo_oficial_campeonato:
                camp_orig = str(values[0])
                camp_oficial = _obter_titulo_oficial_campeonato(camp_orig)
                if camp_orig != camp_oficial:
                    values[0] = camp_oficial
                    changed = True
            if len(values) > 1:
                nome_original = str(values[1])
                nome_bonito = prettify_match_name(nome_original)
                if nome_original != nome_bonito:
                    values[1] = nome_bonito
                    changed = True
            if changed:
                tree.item(item, values=values)
    except Exception as e:
        logger.error(f"[Grid] Erro em padronizar_nomes_grid: {e}")


def remover_duplicatas(tree) -> int:
    """
    Remove itens duplicados do Treeview de forma segura com regra estrita de prioridade:
    Plataforma de Streaming Oficial > CBF (PDF).
    """
    duplicatas = 0
    itens_unicos = {}
    itens_para_remover = set()

    for item in tree.get_children():
        values = tree.item(item, 'values')
        try:
            jogo_fuzzy = _deep_normalize_partida(str(values[1]))
            data_val = str(values[2]).strip()
            plat_val = str(values[6]).strip().lower() if len(values) > 6 else ""
            chave = (jogo_fuzzy, data_val)
        except Exception:
            continue

        if chave in itens_unicos:
            item_existente = itens_unicos[chave]
            values_exist = tree.item(item_existente, 'values')
            camp_exist = str(values_exist[0]).upper() if len(values_exist) > 0 else ""
            url_exist = str(values_exist[7]).lower() if len(values_exist) > 7 else ""
            is_cbf_exist = "CBF" in camp_exist or url_exist.endswith(".pdf")

            camp_novo = str(values[0]).upper() if len(values) > 0 else ""
            url_novo = str(values[7]).lower() if len(values) > 7 else ""
            is_cbf_novo = "CBF" in camp_novo or url_novo.endswith(".pdf")

            if is_cbf_exist and not is_cbf_novo:
                itens_para_remover.add(item_existente)
                itens_unicos[chave] = item
            else:
                itens_para_remover.add(item)
            duplicatas += 1
        else:
            itens_unicos[chave] = item

    for item in itens_para_remover:
        try:
            if tree.exists(item):
                tree.delete(item)
        except Exception:
            pass

    return duplicatas


def ajustartodootree(tree) -> None:
    """Ordena itens do grid por data e hora crescente e alterna colunas de navegador (Esquerda/Direita)."""
    items = list(tree.get_children())
    if len(items) <= 1:
        return

    def _sort_key(item_id):
        v = tree.item(item_id, 'values')
        dt_str = str(v[2]).strip() if len(v) > 2 else "01/01/2000"
        hr_str = str(v[3]).strip() if len(v) > 3 else "00:00"
        try:
            dt_obj = datetime.strptime(f"{dt_str} {hr_str}", "%d/%m/%Y %H:%M")
        except Exception:
            try:
                dt_obj = datetime.strptime(dt_str, "%d/%m/%Y")
            except Exception:
                dt_obj = datetime.min
        return dt_obj

    sorted_items = sorted(items, key=_sort_key)
    var_nav = "Esquerda"
    for index, item_id in enumerate(sorted_items):
        tree.move(item_id, '', index)
        vals = list(tree.item(item_id, 'values'))
        if len(vals) > 4:
            vals[4] = var_nav
            tree.item(item_id, values=tuple(vals))
            var_nav = "Direita" if var_nav == "Esquerda" else "Esquerda"
