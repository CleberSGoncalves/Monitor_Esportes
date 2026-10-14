"""
Coletor de horários via navegador (Playwright).

Reproduz no Gemini web (com a conta Google do usuário, login feito uma única vez num perfil
dedicado) a mesma pergunta feita manualmente e devolve a resposta exibida, SEM cálculos ou deduções.

Uso:
    python modules/web_verdict_collector.py --login     # abre o navegador para login único
    python modules/web_verdict_collector.py             # teste headless (Coritiba x Botafogo)
"""
import os
import re
import sys
import tempfile
import time
from typing import Dict, Any, List
from urllib.parse import urlparse

GEMINI_URL = "https://gemini.google.com/app"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def human_date(date_str: str) -> str:
    """'12/10/2026' -> '12 de outubro de 2026' (apenas formatação)."""
    m = re.match(r'^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$', str(date_str or ""))
    if not m:
        return str(date_str or "").strip()
    d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
    return f"{d} de {MESES[mo - 1]} de {y}"


def build_query(team1: str, team2: str, date_str: str, competition: str = "") -> str:
    comp_txt = f"pelo {competition} " if competition and competition not in ("—", "-", "None") else ""
    return (
        f"Consulte a súmula oficial da CBF e a cobertura em tempo real / minuto a minuto dos portais esportivos (ge.globo.com, Lance!, UOL Esporte, Flashscore) "
        f"e informe o horário de início (apito inicial) e término (apito final) do jogo {team1} x {team2} {comp_txt}no dia {human_date(date_str)} "
        f"(horário de Brasília). Traga também os sites de referência para confirmação correta dos horários."
    )


def _profile_dir() -> str:
    base = os.path.join(os.environ.get("APPDATA", tempfile.gettempdir()), "Monitor_Esportes", "browser_profile")
    os.makedirs(base, exist_ok=True)
    return base


def _launch(pw, headless: bool):
    last_err = ""
    for channel in ("chrome", "msedge"):
        try:
            return pw.chromium.launch_persistent_context(
                _profile_dir(), channel=channel, headless=headless, locale="pt-BR",
                timezone_id="America/Sao_Paulo", viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            ), ""
        except Exception as e:
            last_err = f"{channel}: {e}"
    return None, last_err


def _is_logged_in(page) -> bool:
    try:
        url = page.url or ""
        # Se estiver na tela de login da Conta Google, obviamente o usuário ainda está preenchendo
        if "accounts.google.com" in url or "signin" in url.lower():
            return False

        # Se houver botão explícito de "Fazer login", não está logado
        has_login_btn = False
        try:
            if page.get_by_role("link", name=re.compile("Fazer login|Sign in", re.I)).count() > 0:
                has_login_btn = True
            elif page.get_by_role("button", name=re.compile("^Fazer login$|^Sign in$", re.I)).count() > 0:
                has_login_btn = True
        except Exception:
            pass

        if has_login_btn:
            return False

        # Verifica se a caixa interativa de prompt do Gemini já está pronta e visível
        has_chat = False
        try:
            box = page.locator("rich-textarea div[contenteditable='true'], div[contenteditable='true'][role='textbox']")
            if box.count() > 0 and box.first.is_visible():
                has_chat = True
        except Exception:
            pass

        # Verifica se o avatar de conta do Google está visível no topo
        has_avatar = False
        try:
            avatar = page.locator("a[href*='SignOutOptions'], a[aria-label*='Conta do Google'], button[aria-label*='Conta do Google'], a[aria-label*='Google Account']")
            if avatar.count() > 0:
                has_avatar = True
        except Exception:
            pass

        return has_chat or has_avatar
    except Exception:
        return False


def login_interactive(wait_s: int = 600) -> bool:
    """Abre o navegador VISÍVEL para o usuário entrar na conta Google com tempo amplo (até 10 min)."""
    from playwright.sync_api import sync_playwright
    print("\n" + "="*60)
    print("  ABRINDO O NAVEGADOR PARA LOGIN NO GEMINI WEB")
    print("="*60)
    print("Por favor, faça login na sua Conta Google na janela que abrir.")
    print("O navegador permanecerá aberto até você concluir o login.")
    print("="*60 + "\n")

    with sync_playwright() as pw:
        ctx, err = _launch(pw, headless=False)
        if ctx is None:
            print("Falha ao abrir navegador:", err)
            return False
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            pass

        t0 = time.time()
        ok = False
        consecutive_logged_in = 0

        while time.time() - t0 < wait_s:
            try:
                # Se o usuário fechou o navegador manualmente pelo X
                if page.is_closed() or not ctx.pages:
                    print("\nJanela do navegador foi fechada pelo usuário.")
                    break
            except Exception:
                break

            time.sleep(2)

            try:
                if _is_logged_in(page):
                    consecutive_logged_in += 1
                    # Exige 3 checagens consecutivas (6s estável logado) para evitar falso positivo no loading
                    if consecutive_logged_in >= 3:
                        print("\n✅ Login detectado com sucesso na Conta Google!")
                        ok = True
                        time.sleep(3)
                        break
                else:
                    consecutive_logged_in = 0
            except Exception:
                pass

        try:
            ctx.close()
        except Exception:
            pass

        if ok:
            print("🎉 Sessão salva com sucesso no perfil do navegador!")
        else:
            print("ℹ️ Janela encerrada. Se você fez login antes de fechar, a sessão foi gravada.")
            ok = True
        return ok


def ask_gemini_web(query: str, headless: bool = True, timeout_s: int = 120,
                   screenshot_path: str = "") -> Dict[str, Any]:
    from playwright.sync_api import sync_playwright

    result = {"ok": False, "text": "", "links": [], "logged_in": False, "error": ""}
    with sync_playwright() as pw:
        ctx, err = _launch(pw, headless)
        if ctx is None:
            result["error"] = err
            return result
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
            result["logged_in"] = _is_logged_in(page)
            if not result["logged_in"]:
                result["error"] = "sessao_google_nao_logada"
                return result

            box = page.locator("rich-textarea div[contenteditable='true'], div[contenteditable='true'][role='textbox']").first
            box.wait_for(state="visible", timeout=25000)
            box.click()
            box.fill(query)
            page.keyboard.press("Enter")

            resp_sel = "message-content, .model-response-text"
            last, stable = "", 0
            t0 = time.time()
            while time.time() - t0 < timeout_s:
                page.wait_for_timeout(2500)
                try:
                    items = page.locator(resp_sel)
                    txt = items.last.inner_text(timeout=3000) if items.count() else ""
                except Exception:
                    txt = ""
                if txt and txt == last:
                    stable += 1
                    if stable >= 3:
                        break
                else:
                    stable, last = 0, txt

            raw_text = last.strip()
            # Limpeza de chips/badges visuais da interface web do Google (+ 1, badges de fontes isoladas)
            clean_lines = []
            for r_line in raw_text.splitlines():
                s_l = r_line.strip()
                if re.match(r'^\+\s*\d+$', s_l):
                    continue
                if s_l.lower() in {"lance!", "lance", "gzh", "uol", "uol esporte", "ge", "globo esporte", "cbf", "espn", "band", "terra", "agência brasil - ebc", "agencia brasil - ebc"}:
                    continue
                if len(s_l) < 35 and " - Site Oficial" in s_l:
                    continue
                clean_lines.append(r_line)
            result["text"] = "\n".join(clean_lines).strip()
            try:
                hrefs = page.locator("message-content a[href^='http'], .model-response-text a[href^='http']") \
                            .evaluate_all("els => els.map(e => e.href)")
                seen, links = set(), []
                for h in hrefs:
                    host = urlparse(h).netloc.replace("www.", "")
                    if host and "google." not in host and host not in seen:
                        seen.add(host)
                        links.append({"title": host, "url": h})
                result["links"] = links
            except Exception:
                pass
            result["ok"] = bool(result["text"])
            if screenshot_path:
                page.screenshot(path=screenshot_path, full_page=True)
        except Exception as e:
            result["error"] = str(e)
        finally:
            ctx.close()
    return result


def extract_times(text: str) -> Dict[str, str]:
    """Apenas lê (sem calcular) os horários exibidos na resposta."""
    out = {"inicio": "", "termino": ""}
    for ln in text.split("\n"):
        low = ln.lower()
        m = re.search(r'\b(\d{1,2})\s*[h:]\s*(\d{2})?', ln)
        if not m:
            continue
        val = f"{int(m.group(1)):02d}h{m.group(2) or '00'}"
        if "início" in low or "inicio" in low:
            out["inicio"] = out["inicio"] or val
        elif "término" in low or "termino" in low or "encerramento" in low:
            out["termino"] = out["termino"] or val
    return out


def get_web_verdict(team1: str, team2: str, date_str: str, competition: str = "") -> Dict[str, Any]:
    """Retorna {'verdict_text', 'references', 'times': {'inicio', 'termino'}, 'source': 'gemini_web'} ou {} se indisponível."""
    q = build_query(team1, team2, date_str, competition)
    r = ask_gemini_web(q, headless=True)
    if not r.get("ok"):
        print(f"[WEB VERDICT] indisponível: {r.get('error') or 'sem resposta'}")
        return {}
    txt_clean = re.sub(r'\*\*', '', r["text"])
    parsed_times = extract_times(txt_clean)
    return {
        "verdict_text": txt_clean,
        "references": r["links"][:8],
        "times": parsed_times,
        "source": "gemini_web"
    }


if __name__ == "__main__":
    if "--login" in sys.argv:
        sys.exit(0 if login_interactive() else 1)
    q = build_query("Coritiba", "Botafogo", "12/10/2026")
    r = ask_gemini_web(q, headless=("--show" not in sys.argv),
                       screenshot_path=os.path.join(tempfile.gettempdir(), "gemini_web_test.png"))
    print("OK:", r["ok"], "| LOGADO:", r["logged_in"], "| ERRO:", r["error"])
    print(r["text"])
    print(r["links"])
    print(extract_times(r["text"]))
