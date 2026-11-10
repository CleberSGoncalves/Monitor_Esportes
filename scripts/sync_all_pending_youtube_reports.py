"""
Script para sincronizar todos os relatórios pendentes de canais do YouTube
na biblioteca dedicada 'Relatorio Jogos Youtube'.
"""

import os
import sys
import json
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_youtube_reporter import SharePointYouTubeReporter
from modules.live_channel_monitor import LiveNarrationService

def main():
    print("=" * 70)
    print("📺 SINCRONIZAÇÃO DE RELATÓRIOS DO YOUTUBE (Canais Live)")
    print("=" * 70)

    # 1. Carrega eventos de state.json
    state_file = os.path.join(os.environ.get("APPDATA", ""), "Monitor_Esportes", "live_channels", "state.json")
    events = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                events = data.get("events", {})
        except Exception as e:
            print(f"Erro ao ler state.json: {e}")

    print(f"Eventos cadastrados no monitor: {len(events)}")

    # 2. Varre relatórios em reports/ que correspondem a canais do YouTube
    reports_dir = os.path.join(PROJECT_ROOT, "reports")
    pdf_candidates = []
    if os.path.exists(reports_dir):
        for f in os.listdir(reports_dir):
            if f.endswith(".pdf") and any(k in f.lower() for k in ["youtube", "narracao", "band", "gaucha", "bage", "baldasso"]):
                pdf_candidates.append(os.path.join(reports_dir, f))

    print(f"PDFs candidatos encontrados em reports/: {len(pdf_candidates)}")
    for p in pdf_candidates:
        print(f"  • {os.path.basename(p)} ({os.path.getsize(p):,} bytes)")

if __name__ == "__main__":
    main()
