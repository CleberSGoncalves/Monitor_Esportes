# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.live_channel_monitor import LiveNarrationService
from modules.report_generator import ReportGenerator

def test_audit():
    print("[*] Instanciando LiveNarrationService...")
    reports_dir = os.path.join(Path(__file__).resolve().parents[1], "reports")
    os.makedirs(reports_dir, exist_ok=True)
    reporter = ReportGenerator(reports_dir=reports_dir)
    svc = LiveNarrationService(
        reporter=reporter,
        config_provider=lambda: {"api_key": "dummy"},
        log=print,
        on_change=lambda: None
    )
    print(f"[*] Total de eventos na base: {len(svc.list_events())}")
    print("[*] Gerando Relatório Geral de Auditoria de Lives...")
    res = svc.generate_all_cases_audit_report()
    print("[*] Resultado:", res)
    if res.get("ok"):
        pdf = res.get("pdf_path")
        print(f"[SUCCESS] PDF gerado em: {pdf} (Existe: {os.path.exists(pdf)})")

if __name__ == "__main__":
    test_audit()
