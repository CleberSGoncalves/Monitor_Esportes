"""
Script para sincronizar todos os 50 relatórios da NBA em cache com o fuso BRT
diretamente na biblioteca 'Relatorios_de_Jogos_NBA' do SharePoint.
"""

import os
import sys
import re
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService, NBA_TEAMS
from modules.nba_report_generator import NBAReportGenerator
from modules.sharepoint_nba_reporter import SharePointNBAReporter

TRI_TO_NAME = {v: k for k, v in NBA_TEAMS.items()}

def sync_all_cached_gamebooks():
    cache_dir = os.path.join(PROJECT_ROOT, "config", "nba_cache")
    pdf_files = sorted([f for f in os.listdir(cache_dir) if f.endswith("_book.pdf")])
    
    print(f"==================================================================")
    print(f"Atualizando {len(pdf_files)} Game Books da NBA com Fuso BRT no SharePoint")
    print(f"==================================================================")

    success = 0
    errors = 0

    for idx, f in enumerate(pdf_files, 1):
        pdf_path = os.path.join(cache_dir, f)
        m = re.match(r"(\d{8})_([A-Z]{3})([A-Z]{3})_book\.pdf", f)
        if not m:
            continue
        d_clean, away_tri, home_tri = m.groups()
        d_disp = f"{d_clean[6:8]}/{d_clean[4:6]}/{d_clean[:4]}"

        away_name = TRI_TO_NAME.get(away_tri, away_tri)
        home_name = TRI_TO_NAME.get(home_tri, home_tri)

        try:
            parsed = NBAService.parse_gamebook(pdf_path, home_tri=home_tri, date_clean=d_clean)
            first_m = parsed.get("milestones", [{}])[0].get("time_brt", "19:00:00")
            time_brt_short = ":".join(first_m.split(":")[:2])

            game = {
                "away_team": away_name,
                "home_team": home_name,
                "away_tri": away_tri,
                "home_tri": home_tri,
                "match_display": f"{away_name} @ {home_name}",
                "date_clean": d_clean,
                "date_display": d_disp,
                "time_brt": time_brt_short,
                "platform": "NBA League Pass",
                "score_display": "Finalizado",
                "is_finished": True
            }

            out_pdf = NBAReportGenerator.generate_report(game, parsed)
            ok = SharePointNBAReporter.sync_nba_report(out_pdf, game)
            if ok:
                success += 1
                print(f"[{idx:2d}/{len(pdf_files)}] [OK] {away_tri} @ {home_tri} ({d_disp}) -> BRT {time_brt_short}")
            else:
                errors += 1
                print(f"[{idx:2d}/{len(pdf_files)}] [ERRO] {away_tri} @ {home_tri} ({d_disp}) -> Falha sync")

        except Exception as e:
            errors += 1
            print(f"[{idx:2d}/{len(pdf_files)}] [EXCECAO] {away_tri} @ {home_tri}: {e}")

        # Intervalo defensivo para evitar 429 Rate Limit
        time.sleep(2.0)

    print(f"\n==================================================================")
    print(f"Concluído: {success} enviados com sucesso, {errors} falhas.")
    print(f"==================================================================")

if __name__ == "__main__":
    sync_all_cached_gamebooks()
