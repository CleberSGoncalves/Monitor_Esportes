import os, sys, tempfile, urllib.parse
from playwright.sync_api import sync_playwright

q = "horário de inicio e termino do jogo Coritiba x Botafogo dia 12 de outubro de 2026, traga também os sites de referencia para confirmação correta dos horarios"
modes = {
    "aimode": "https://www.google.com/search?udm=50&hl=pt-BR&q=" + urllib.parse.quote(q),
    "search": "https://www.google.com/search?hl=pt-BR&q=" + urllib.parse.quote(q),
}
profile = os.path.join(os.environ["APPDATA"], "Monitor_Esportes", "browser_profile_test")
os.makedirs(profile, exist_ok=True)
with sync_playwright() as pw:
    ctx = pw.chromium.launch_persistent_context(
        profile, channel="chrome", headless=True, locale="pt-BR",
        timezone_id="America/Sao_Paulo", viewport={"width": 1280, "height": 1100},
        args=["--disable-blink-features=AutomationControlled"])
    for name, url in modes.items():
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(15000)
        shot = os.path.join(tempfile.gettempdir(), f"google_{name}.png")
        page.screenshot(path=shot, full_page=False)
        body = page.inner_text("body")
        print(f"===== {name} | url final: {page.url[:80]} =====")
        print(body[:1800])
        print("screenshot:", shot)
        page.close()
    ctx.close()
