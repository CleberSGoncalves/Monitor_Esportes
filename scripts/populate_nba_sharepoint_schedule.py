import os
import sys
import time
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService
from modules.nba_report_generator import NBAReportGenerator
from modules.sharepoint_nba_reporter import SharePointNBAReporter

def main():
    svc = NBAService()
    gen = NBAReportGenerator()

    dates = ["2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30", "2026-10-31"]
    all_games = []
    for d in dates:
        games = svc.fetch_games_for_date(d)
        print(f"Data {d}: {len(games)} jogos encontrados.")
        all_games.extend(games)

    print(f"Total de jogos coletados: {len(all_games)}")
    success = 0
    for idx, g in enumerate(all_games, 1):
        match_disp = g.get("match_display")
        dt_disp = g.get("date_display")
        plat = g.get("platform")
        is_fin = g.get("is_finished")
        print(f"[{idx}/{len(all_games)}] Processando {match_disp} ({dt_disp}) | Plat: {plat} | Fin: {is_fin}...", flush=True)

        gb_path = svc.download_gamebook(g) if is_fin else None
        parsed = svc.parse_gamebook(gb_path) if gb_path else {}
        pdf = gen.generate_report(g, parsed)

        ok = SharePointNBAReporter.sync_nba_report(pdf, g)
        if ok:
            success += 1
            print(f"  -> OK sincronizado no SharePoint!", flush=True)
        else:
            print(f"  -> Falha ao sincronizar.", flush=True)
        time.sleep(2.0)

    print(f"\nConcluido! {success}/{len(all_games)} jogos sincronizados no SharePoint Relatorios_de_Jogos_NBA!")

if __name__ == "__main__":
    main()
