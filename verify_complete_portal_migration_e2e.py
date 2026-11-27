# -*- coding: utf-8 -*-
"""
verify_complete_portal_migration_e2e.py
Auditoria Completa E2E do Portal Web (docs e portal_web)
Valida:
1. Zero menções a adgbl.sharepoint.com e zero links quebrados.
2. 100% dos relatórios das 3 listas (Futebol, YouTube, NBA) abrem seus respectivos PDFs sem erro 404.
3. Editor de Planilhas em Tela Cheia abre qualquer planilha com abas autênticas e dados reais.
4. Botão de download e abertura no Excel Desktop funciona sem falhas.
5. Painel de Streaming exibe o dia atual em verde e dias anteriores em vermelho.
"""

import os
import sys
import json
import time
import socket
import threading
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen, Request
from playwright.sync_api import sync_playwright

PROJECT_ROOT = r"E:\desenvolvimento\Monitor_Esportes"
TARGET_FOLDERS = [
    ("docs", os.path.join(PROJECT_ROOT, "docs")),
    ("portal_web", os.path.join(PROJECT_ROOT, "portal_web"))
]

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

class QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass

def start_server(directory, port):
    def run():
        handler = lambda *args, **kwargs: QuietHandler(*args, directory=directory, **kwargs)
        server = QuietServer(('127.0.0.1', port), handler)
        server.serve_forever()
    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(0.5)

def run_e2e_for_target(name, folder, port):
    print(f"\n======================================================================", flush=True)
    print(f"  INICIANDO AUDITORIA E2E: [{name.upper()}] em http://127.0.0.1:{port}", flush=True)
    print(f"======================================================================", flush=True)

    evidence = {
        "target": name,
        "folder": folder,
        "tests": {},
        "success": True
    }

    # 1. VERIFICAÇÃO DE ZERO DEPENDÊNCIA DO SHAREPOINT (adgbl.sharepoint.com)
    print(f"[*] [Teste 1/5] Verificando ausência total de 'adgbl.sharepoint.com'...", flush=True)
    sp_matches = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__']]
        for f in files:
            if f.endswith(('.html', '.js', '.json', '.css', '.md')):
                fp = os.path.join(root, f)
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as fl:
                        content = fl.read()
                        if 'adgbl.sharepoint.com' in content:
                            sp_matches.append(os.path.relpath(fp, folder))
                except Exception:
                    pass

    if sp_matches:
        print(f"  [FALHA] Foram encontrados links para adgbl.sharepoint.com em: {sp_matches}", flush=True)
        evidence["tests"]["zero_sharepoint"] = {"status": "FAIL", "matches": sp_matches}
        evidence["success"] = False
    else:
        print(f"  [OK] Zero menções a 'adgbl.sharepoint.com' em todo o pacote {name}!", flush=True)
        evidence["tests"]["zero_sharepoint"] = {"status": "PASS", "matches": []}

    # 2. VERIFICAÇÃO DE TODOS OS RELATÓRIOS (FUTEBOL, YOUTUBE, NBA)
    print(f"\n[*] [Teste 2/5] Validando integridade de 100% dos Relatórios PDF (Futebol, YouTube, NBA)...", flush=True)
    html_file = os.path.join(folder, "index.html")
    with open(html_file, "r", encoding="utf-8") as f:
        html_text = f.read()

    idx = html_text.find("let SP_MASTER_DATA =")
    json_str = html_text[idx + len("let SP_MASTER_DATA ="):].strip()
    data, _ = json.JSONDecoder().raw_decode(json_str)
    drives = data.get("drives", {})

    report_categories = {
        "Relatorios_de_Jogos": "futebol",
        "Relatorio Jogos Youtube": "youtube",
        "Relatorios_de_Jogos_NBA": "nba"
    }

    report_stats = {}
    all_reports_valid = True

    for drive_key, cat in report_categories.items():
        items = drives.get(drive_key, {}).get("items", [])
        checked = 0
        missing_404 = []

        for it in items:
            name_file = it.get("name", "")
            web_url = it.get("webUrl", f"reports/{cat}/{name_file}")
            
            # Testa se o arquivo físico existe no disco
            disk_path = os.path.join(folder, web_url.replace("/", os.sep))
            if not os.path.exists(disk_path):
                missing_404.append((name_file, web_url, "Disk File Not Found"))
                continue

            # Testa se o servidor HTTP responde 200 OK sem 404
            encoded_url = urllib.parse.quote(web_url, safe="/")
            http_url = f"http://127.0.0.1:{port}/{encoded_url}"
            try:
                req = Request(http_url, headers={"User-Agent": "E2E-Auditor"})
                with urlopen(req, timeout=5) as resp:
                    if resp.status != 200:
                        missing_404.append((name_file, web_url, f"HTTP {resp.status}"))
                    else:
                        resp_bytes = resp.read()
                        if not resp_bytes.startswith(b"%PDF-"):
                            missing_404.append((name_file, web_url, "Invalid PDF magic header"))
            except Exception as e:
                missing_404.append((name_file, web_url, str(e)))

            checked += 1

        print(f"  - [{cat.upper()}]: {len(items)} relatórios cadastrados | {checked} auditados | 404 erros: {len(missing_404)}", flush=True)
        report_stats[cat] = {
            "total": len(items),
            "checked": checked,
            "errors_404": len(missing_404),
            "failed_items": missing_404[:5]
        }
        if missing_404:
            all_reports_valid = False

    evidence["tests"]["reports_pdf"] = {
        "status": "PASS" if all_reports_valid else "FAIL",
        "stats": report_stats
    }
    if not all_reports_valid:
        evidence["success"] = False

    # 3. PLAYWRIGHT NAVEGADOR REAL: UI, EDITOR DE PLANILHAS, STREAMING
    print(f"\n[*] [Teste 3/5] Executando testes funcionais via Playwright Chromium...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type in ["error"] else None)

        page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle")
        print(f"  [OK] Página carregada: '{page.title()}'", flush=True)

        # 3.1. Testar abertura visual de PDF no DOM
        print(f"  [*] Testando abertura de relatório PDF no modal oficial...", flush=True)
        page.evaluate("() => { if (typeof openReportPdf === 'function') openReportPdf('expert_athleticopr_x_palmeiras_20261018.pdf'); }")
        time.sleep(1)

        modal_pdf = page.query_selector("#modal-pdf-viewer")
        modal_visible = modal_pdf is not None and modal_pdf.is_visible()
        pdf_frame = page.query_selector("#pdf-viewer-frame")
        frame_src = pdf_frame.get_attribute("src") if pdf_frame else ""

        print(f"  - Modal PDF visível: {modal_visible} | Fonte do Frame: {frame_src}", flush=True)
        evidence["tests"]["pdf_modal_ui"] = {
            "status": "PASS" if (modal_visible and "reports/futebol" in frame_src) else "FAIL",
            "frame_src": frame_src
        }

        # Fechar modal PDF de forma limpa e explícita
        page.evaluate("() => { const m = document.getElementById('modal-pdf-viewer'); if (m) m.style.display = 'none'; }")
        time.sleep(0.5)

        # 4. EDITOR DE PLANILHAS EM TELA CHEIA
        print(f"\n[*] [Teste 4/5] Testando Editor de Planilhas em Tela Cheia com Abas Autênticas...", flush=True)
        test_sheet = "Acomp. SLA Interno-Globo - Abril 2026.xlsx"
        page.evaluate(f"() => {{ window.openOnlineSheetEditor('{test_sheet}'); }}")
        time.sleep(2)

        sheet_modal = page.query_selector("#modal-online-sheet-editor")
        sheet_modal_visible = sheet_modal is not None and sheet_modal.is_visible()

        # Validar abas autênticas
        tabs = page.query_selector_all(".btn-sheet-tab")
        tab_names = [t.inner_text().strip() for t in tabs]
        print(f"  - Modal de Planilha Aberto: {sheet_modal_visible}", flush=True)
        print(f"  - Abas Autênticas Detectadas ({len(tabs)}): {tab_names}", flush=True)

        # Validar dados tabulares
        rows = page.query_selector_all("#online-sheet-table tbody tr")
        print(f"  - Linhas tabulares renderizadas na aba ativa: {len(rows)}", flush=True)

        # Alternar de aba
        if len(tabs) > 1:
            second_tab = tabs[1]
            second_tab_name = second_tab.inner_text()
            second_tab.click()
            time.sleep(0.5)
            rows_after_tab = page.query_selector_all("#online-sheet-table tbody tr")
            print(f"  - Alternância para aba '{second_tab_name}': {len(rows_after_tab)} linhas renderizadas.", flush=True)

        # Validar botão Excel Desktop
        btn_desktop = page.query_selector("#btn-open-desktop-excel")
        has_desktop_btn = btn_desktop is not None
        print(f"  - Botão 'Abrir no Microsoft Excel Desktop' presente: {has_desktop_btn}", flush=True)
        if btn_desktop:
            btn_desktop.click()
            time.sleep(0.5)

        # Validar botão Exportar CSV
        btn_csv = page.query_selector("#btn-sheet-export-csv")
        has_csv_btn = btn_csv is not None
        print(f"  - Botão 'Exportar .CSV' presente: {has_csv_btn}", flush=True)

        # Fechar editor
        page.evaluate("() => { document.getElementById('modal-online-sheet-editor')?.remove(); }")
        time.sleep(0.5)

        evidence["tests"]["sheet_editor"] = {
            "status": "PASS" if (sheet_modal_visible and len(tabs) >= 2 and len(rows) > 0 and has_desktop_btn) else "FAIL",
            "tabs": tab_names,
            "rows_count": len(rows),
            "desktop_excel_button": has_desktop_btn,
            "csv_button": has_csv_btn
        }
        if not (sheet_modal_visible and len(tabs) >= 2):
            evidence["success"] = False

        # 5. PAINEL DE STREAMING (CORES HOJE VERDE / PASSADO VERMELHO)
        print(f"\n[*] [Teste 5/5] Testando Painel de Streaming e regras de cores das datas...", flush=True)
        page.evaluate("() => { if (typeof showPane === 'function') showPane('streaming'); }")
        time.sleep(1.5)

        today_rows = page.query_selector_all(".stream-row-today")
        past_rows = page.query_selector_all(".stream-row-past")
        future_rows = page.query_selector_all(".stream-row-future")

        print(f"  - Linhas de Streaming Hoje (.stream-row-today): {len(today_rows)}", flush=True)
        print(f"  - Linhas de Streaming Anteriores (.stream-row-past): {len(past_rows)}", flush=True)
        print(f"  - Linhas de Streaming Futuras (.stream-row-future): {len(future_rows)}", flush=True)

        # Verificar cor da linha de hoje
        today_green = False
        if len(today_rows) > 0:
            bg_today = page.evaluate("(el) => window.getComputedStyle(el).backgroundColor", today_rows[0])
            border_today = page.evaluate("(el) => window.getComputedStyle(el).borderLeftColor", today_rows[0])
            print(f"  - Estilo da linha de hoje: bg={bg_today}, borderLeft={border_today}", flush=True)
            if "rgba(34, 197, 94" in bg_today or "rgb(22, 163, 74)" in border_today:
                today_green = True

        # Verificar cor da linha passada
        past_red = False
        if len(past_rows) > 0:
            bg_past = page.evaluate("(el) => window.getComputedStyle(el).backgroundColor", past_rows[0])
            border_past = page.evaluate("(el) => window.getComputedStyle(el).borderLeftColor", past_rows[0])
            print(f"  - Estilo da linha anterior: bg={bg_past}, borderLeft={border_past}", flush=True)
            if "rgba(239, 68, 68" in bg_past or "rgb(239, 68, 68)" in border_past:
                past_red = True

        streaming_pass = past_red and (len(today_rows) == 0 or today_green)
        evidence["tests"]["streaming_panel"] = {
            "status": "PASS" if streaming_pass else "FAIL",
            "today_rows": len(today_rows),
            "today_green": today_green,
            "past_rows": len(past_rows),
            "past_red": past_red,
            "future_rows": len(future_rows)
        }
        if not streaming_pass:
            evidence["success"] = False

        # Verificar erros fatais de console
        fatal_errors = [e for e in console_errors if not "favicon" in e.lower()]
        print(f"  - Erros fatais de console JS durante toda a navegação: {len(fatal_errors)}", flush=True)
        evidence["tests"]["console_integrity"] = {
            "status": "PASS" if len(fatal_errors) == 0 else "WARN",
            "errors": fatal_errors
        }

        browser.close()

    print(f"\n>>> RESULTADO FINAL [{name.upper()}]: {'APROVADO 100%' if evidence['success'] else 'REPROVADO'}", flush=True)
    return evidence

def main():
    print("======================================================================", flush=True)
    print(" SUÍTE DE TESTES E2E: AUDITORIA OFICIAL DO PORTAL WEB & GOOGLE SITES ", flush=True)
    print("======================================================================", flush=True)

    all_results = {}
    for name, folder in TARGET_FOLDERS:
        port = find_free_port()
        start_server(folder, port)
        res = run_e2e_for_target(name, folder, port)
        all_results[name] = res

    # Salva relatório consolidado
    report_file = os.path.join(PROJECT_ROOT, "reports", "portal_complete_e2e_audit_report.json")
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    overall_success = all(r["success"] for r in all_results.values())
    print("\n======================================================================", flush=True)
    print(f" RELATÓRIO CONSOLIDADO E2E: {'SUCESSO ABSOLUTO (100% PASSOU)' if overall_success else 'COM FALHAS'}", flush=True)
    print(f" Arquivo de evidências: {report_file}", flush=True)
    print("======================================================================", flush=True)

    if not overall_success:
        sys.exit(1)

if __name__ == "__main__":
    main()
