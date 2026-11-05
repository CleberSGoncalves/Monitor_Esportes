import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService
from modules.nba_report_generator import NBAReportGenerator
from modules.sharepoint_nba_reporter import SharePointNBAReporter

def regenerate_0411():
    games = NBAService.fetch_games_for_date("2026-11-04")
    print(f"Regenerando {len(games)} relatorios de 04/11 com sincronia estrita de horarios...")

    generated = []
    for g in games:
        away_tri, home_tri = g["away_tri"], g["home_tri"]
        gb_path = NBAService.download_gamebook(g)
        if gb_path and os.path.exists(gb_path):
            parsed = NBAService.parse_gamebook(gb_path, home_tri=home_tri, date_clean="20261104")
            pdf = NBAReportGenerator.generate_report(g, parsed, auto_generate_proofs=True)
            sz = os.path.getsize(pdf) if os.path.exists(pdf) else 0
            print(f"[OK] {g['match_display']} -> {os.path.basename(pdf)} ({sz} bytes)")
            generated.append((g, pdf))

    print(f"\nSincronizando {len(generated)} relatorios atualizados no SharePoint...")
    for g, pdf in generated:
        try:
            ok = SharePointNBAReporter.sync_nba_report(pdf, g)
            print(f"  SharePoint {g['match_display']}: {ok}")
        except Exception as e:
            print(f"  Erro no SharePoint {g['match_display']}: {e}")
        time.sleep(2.0)

if __name__ == "__main__":
    regenerate_0411()
