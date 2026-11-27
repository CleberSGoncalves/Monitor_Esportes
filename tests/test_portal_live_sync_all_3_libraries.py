"""
Testes automatizados reais (Unitários + Integração + Integridade dos 3 Drives)
garantindo que TODOS os 3 tipos de relatórios (Futebol, YouTube e NBA):
  1. Enviam simultaneamente para SharePoint e Google Sites (PortalSyncManager);
  2. Mantêm metadados 100% fidedignos (data/hora real BRT, placar, partida completa, plataforma/canal);
  3. Publicam no Google Sites mesmo se o SharePoint falhar (Regra 6 - Autonomia);
  4. Suportam publicação em lote atômica para jogos agendados da NBA;
  5. Possuem 100% dos PDFs reais (> 1 KB) presentes em docs/reports/ e índices ao vivo ordenados;
  6. Possuem credencial criptografada funcional com permissão push na GitHub API.
"""

import os
import sys
import json
import tempfile
from unittest.mock import patch
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.portal_sync import PortalSyncManager, iso_utc_to_brt_str, _parse_item_sort_ts
from modules.sharepoint_reporter import SharePointReporter
from modules.sharepoint_youtube_reporter import SharePointYouTubeReporter
from modules.sharepoint_nba_reporter import SharePointNBAReporter


def _make_dummy_pdf(tmpdir: str, name: str) -> str:
    p = os.path.join(tmpdir, name)
    # PDF válido > 1.5 KB
    content = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n" + (b"%TESTDATA" * 200) + b"\n%%EOF\n"
    with open(p, "wb") as f:
        f.write(content)
    return p


def test_iso_utc_to_brt_conversion():
    assert iso_utc_to_brt_str("2026-12-01T00:30:00Z") == "30/11/2026 21:30"
    assert iso_utc_to_brt_str("2026-11-23T23:00:00Z") == "23/11/2026 20:00"
    assert iso_utc_to_brt_str("27/11/2026 17:00") == "27/11/2026 17:00"


def test_futebol_reporter_publishes_to_google_site_even_if_sharepoint_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = _make_dummy_pdf(tmpdir, "test_futebol.pdf")
        captured = {}

        def fake_sync(**kwargs):
            captured.update(kwargs)
            return True

        with patch.object(SharePointReporter, "obter_token_graph", side_effect=RuntimeError("SharePoint Offline")), \
             patch.object(PortalSyncManager, "sync_report_to_portal", side_effect=fake_sync):
            ok = SharePointReporter.sync_pdf_to_sharepoint(
                pdf_path=pdf_path,
                partida="Botafogo x São Paulo",
                campeonato="Brasileirão Série A",
                plataforma="Amazon Prime Video",
                data_hora_iso="2026-11-23T23:00:00Z",
                confianca="99.0%",
            )

        assert ok is True
        assert captured["drive_name"] == "Relatorios_de_Jogos"
        assert captured["category"] == "futebol"
        assert captured["partida"] == "Botafogo x São Paulo"
        assert captured["campeonato"] == "Brasileiro Serie A"
        assert captured["plataforma"] == "Amazon Prime"
        assert captured["data_hora"] == "23/11/2026 20:00"
        assert captured["auditado"] is True


def test_youtube_reporter_publishes_to_google_site_even_if_sharepoint_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = _make_dummy_pdf(tmpdir, "test_yt.pdf")
        captured = {}

        def fake_sync(**kwargs):
            captured.update(kwargs)
            return True

        ev = {
            "program_name": "Bom Dia Grêmio",
            "coverage_theme": "Análise Pós-Jogo",
            "is_coverage_debate": True,
            "channel_name": "Bagé TV",
            "date": "27/11/2026",
            "start_time": "17:00",
            "date_clean": "20261127",
        }

        with patch.object(SharePointReporter, "obter_token_graph", side_effect=RuntimeError("SharePoint Offline")), \
             patch.object(PortalSyncManager, "sync_report_to_portal", side_effect=fake_sync):
            ok = SharePointYouTubeReporter.sync_youtube_report(pdf_path=pdf_path, event_info=ev, confianca="99.0%")

        assert ok is True
        assert captured["drive_name"] == "Relatorio Jogos Youtube"
        assert captured["category"] == "youtube"
        assert captured["canal"] == "Bagé TV"
        assert captured["plataforma"] == "Bagé TV"
        assert captured["data_hora"] == "27/11/2026 17:00"
        assert captured["placar"] == "99.0%"
        assert captured["auditado"] is True


def test_nba_reporter_metadata_fidelity_and_batch_flush():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = _make_dummy_pdf(tmpdir, "test_nba.pdf")
        captured_calls = []

        def fake_sync(**kwargs):
            captured_calls.append(kwargs)
            return True

        game_sched = {
            "away_tri": "LAL",
            "home_tri": "HOU",
            "match_display": "Los Angeles Lakers @ Houston Rockets",
            "date_clean": "20261130",
            "date_display": "30/11/2026",
            "time_brt": "21:30",
            "iso_utc": "2026-12-01T00:30:00Z",
            "platform": "Amazon Prime Video",
            "is_finished": False,
        }

        with patch.object(SharePointReporter, "obter_token_graph", side_effect=RuntimeError("SharePoint Offline")), \
             patch.object(PortalSyncManager, "sync_report_to_portal", side_effect=fake_sync), \
             patch.object(PortalSyncManager, "flush_github_batch", return_value=True) as mock_flush, \
             patch("modules.nba_report_generator.NBAReportGenerator.generate_schedule_sheet", return_value=pdf_path):
            count = SharePointNBAReporter.sync_all_scheduled_games([game_sched], max_future_games=5)

        assert count == 1
        assert len(captured_calls) == 1
        c = captured_calls[0]
        assert c["drive_name"] == "Relatorios_de_Jogos_NBA"
        assert c["category"] == "nba"
        assert c["partida"] == "Los Angeles Lakers @ Houston Rockets"
        assert c["plataforma"] == "Amazon Prime"
        assert c["data_hora"] == "30/11/2026 21:30"
        assert c["placar"] == "Agendado (21:30 BRT)"
        assert c["auditado"] is False
        assert c["defer_github_push"] is True
        mock_flush.assert_called_once_with("nba")


def test_all_three_live_indexes_and_pdfs_integrity():
    expected = [
        ("futebol", "Relatorios_de_Jogos", 35),
        ("youtube", "Relatorio Jogos Youtube", 100),
        ("nba", "Relatorios_de_Jogos_NBA", 200),
    ]
    for cat, drive_name, min_count in expected:
        idx_path = os.path.join(PROJECT_ROOT, "docs", "reports", f"index_{cat}.json")
        assert os.path.exists(idx_path), f"Índice ausente: {idx_path}"
        with open(idx_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("items") or []
        assert data.get("drive_name") == drive_name
        assert len(items) >= min_count, f"{cat} tem apenas {len(items)} itens (esperado >= {min_count})"

        # Verificar ordenação decrescente (mais recente no topo)
        timestamps = [_parse_item_sort_ts(it) for it in items]
        assert timestamps == sorted(timestamps, reverse=True), f"Índice {cat} não está ordenado por data decrescente!"

        # Verificar que 100% dos PDFs referenciados existem em docs/reports/<cat>/ com tamanho >= 1KB
        missing = []
        corrupt = []
        for it in items:
            pdf_file = os.path.join(PROJECT_ROOT, "docs", "reports", cat, it["name"])
            if not os.path.exists(pdf_file):
                missing.append(it["name"])
            elif os.path.getsize(pdf_file) < 1000:
                corrupt.append((it["name"], os.path.getsize(pdf_file)))
        assert not missing, f"PDFs faltando em docs/reports/{cat}/: {missing[:5]}"
        assert not corrupt, f"PDFs corrompidos (<1KB) em docs/reports/{cat}/: {corrupt[:5]}"


def test_github_publisher_token_and_push_permission():
    tok = PortalSyncManager._get_github_token()
    assert tok and len(tok) > 20, "Token GitHub de publicação do portal não pôde ser resolvido!"
    r = requests.get(
        "https://api.github.com/repos/CleberSGoncalves/Monitor_Esportes",
        headers=PortalSyncManager._gh_headers(tok),
        timeout=15,
    )
    assert r.status_code == 200, f"Falha na autenticação GitHub API: HTTP {r.status_code}"
    perms = r.json().get("permissions") or {}
    assert perms.get("push") is True, f"Token sem permissão push: {perms}"


def test_portal_js_syntax_and_playwright_e2e_all_3_drives():
    import re
    import subprocess
    from pathlib import Path
    from playwright.sync_api import sync_playwright

    # 1. Validacao node -c em docs/index.html e portal_web/index.html (Regra 7)
    for html_rel in ("docs/index.html", "portal_web/index.html"):
        html_abs = os.path.join(PROJECT_ROOT, html_rel)
        with open(html_abs, "r", encoding="utf-8") as f:
            txt = f.read()
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", txt, re.S | re.I)
        assert len(scripts) > 0, f"Nenhum bloco <script> em {html_rel}"
        for i, sc in enumerate(scripts):
            if not sc.strip():
                continue
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
                tf.write(sc)
                tpath = tf.name
            try:
                res = subprocess.run(["node", "-c", tpath], capture_output=True, text=True)
                assert res.returncode == 0, f"Erro de sintaxe JS em {html_rel} bloco #{i}: {res.stderr}"
            finally:
                if os.path.exists(tpath):
                    os.unlink(tpath)

    # 2. Playwright E2E real nos dois arquivos HTML
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for html_rel in ("docs/index.html", "portal_web/index.html"):
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page_errors = []
                console_errors = []
                page.on("pageerror", lambda err: page_errors.append(str(err)))
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

                uri = Path(os.path.join(PROJECT_ROOT, html_rel)).as_uri()
                page.goto(uri, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(700)

                # Home -> Acesso Remoto RDP -> Streaming (Excluir Selecionados + modal in-DOM)
                assert page.locator("#pane-home.active").count() == 1
                page.evaluate("handleMenuClick('remoto', 'Acesso Remoto')")
                page.wait_for_timeout(250)
                assert page.locator("#pane-remoto.active").count() == 1

                page.evaluate("handleMenuClick('streaming', 'Streaming')")
                page.wait_for_timeout(300)
                assert page.locator("#pane-streaming.active").count() == 1
                first_cb = page.locator("#pane-streaming input[type='checkbox'].row-check-streaming, #pane-streaming input[type='checkbox'].check-item-streaming").first
                if first_cb.count() > 0:
                    first_cb.check()
                    page.wait_for_timeout(150)
                    del_btn = page.locator("#btn-delete-streaming-selected, #pane-streaming button:has-text('Excluir Selecionados')").first
                    if del_btn.count() > 0 and del_btn.is_visible():
                        del_btn.click()
                        page.wait_for_timeout(200)
                        assert page.locator("#modal-generic-confirm-delete").is_visible()
                        page.locator("#modal-generic-confirm-delete button:has-text('Cancelar')").click()
                        page.wait_for_timeout(150)

                # Validar todas as 3 bibliotecas de relatórios (Futebol, YouTube, NBA)
                for dkey, expected_min, expected_top_date in (
                    ("Relatorios_de_Jogos", 40, "24/11/2026"),
                    ("Relatorio Jogos Youtube", 132, "27/11/2026"),
                    ("Relatorios_de_Jogos_NBA", 228, "30/11/2026"),
                ):
                    page.evaluate(f"openDrive({json.dumps(dkey)}, {json.dumps(dkey)})")
                    page.wait_for_timeout(350)
                    rows = page.locator("#drive-viewer-tbody tr")
                    cnt = rows.count()
                    assert cnt >= expected_min, f"{html_rel} {dkey}: esperava >= {expected_min}, obteve {cnt}"
                    first_txt = rows.first.inner_text()
                    assert expected_top_date in first_txt, f"{html_rel} {dkey}: topo esperado {expected_top_date}, veio: {first_txt[:140]}"
                    assert page.locator("#btn-refresh-drive-live").is_visible()

                    # Abrir PDF no modal in-DOM
                    rows.first.locator("button.btn-doc-download").click()
                    page.wait_for_timeout(250)
                    assert page.locator("#modal-pdf-viewer").is_visible(), f"Modal PDF não abriu em {dkey}"
                    src = page.locator("#pdf-viewer-frame").get_attribute("src") or ""
                    assert ".pdf" in src.lower(), f"Iframe PDF src inválido: {src}"
                    page.evaluate("closePdfModal()")
                    page.wait_for_timeout(150)

                assert not page_errors, f"pageerror em {html_rel}: {page_errors}"
                real_console_errs = [
                    e for e in console_errors
                    if "Failed to load resource" not in e and "ERR_FILE_NOT_FOUND" not in e and "CORS" not in e
                ]
                assert not real_console_errs, f"console.error em {html_rel}: {real_console_errs}"
                page.close()
        finally:
            browser.close()
