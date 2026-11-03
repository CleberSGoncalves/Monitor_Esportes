# scripts/generate_all_nba_brt.py
import os
import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService, NBA_TEAMS
from modules.nba_report_generator import NBAReportGenerator

TRI_TO_NAME = {v: k for k, v in NBA_TEAMS.items()}

def generate_all():
    cache_dir = os.path.join(PROJECT_ROOT, "config", "nba_cache")
    pdf_files = [f for f in os.listdir(cache_dir) if f.endswith("_book.pdf")]
    
    print(f"Encontrados {len(pdf_files)} Game Books em cache para processamento com fuso BRT...")
    success_count = 0

    for f in sorted(pdf_files):
        pdf_path = os.path.join(cache_dir, f)
        # 20261027_BKNBOS_book.pdf
        m = re.match(r"(\d{8})_([A-Z]{3})([A-Z]{3})_book\.pdf", f)
        if not m:
            continue
        d_clean, away_tri, home_tri = m.groups()
        d_disp = f"{d_clean[6:8]}/{d_clean[4:6]}/{d_clean[:4]}"

        away_name = TRI_TO_NAME.get(away_tri, away_tri)
        home_name = TRI_TO_NAME.get(home_tri, home_tri)

        parsed = NBAService.parse_gamebook(pdf_path, home_tri=home_tri, date_clean=d_clean)
        
        # Obter primeiro marco para horário oficial BRT
        first_m = parsed.get("milestones", [{}])[0].get("time_brt", "19:00:00")
        time_brt_short = ":".join(first_m.split(":")[:2])

        game = {
            "away_team": away_name,
            "home_team": home_name,
            "away_tri": away_tri,
            "home_tri": home_tri,
            "match_display": f"{away_name} x {home_name}",
            "date_clean": d_clean,
            "date_display": d_disp,
            "time_brt": time_brt_short,
            "platform": "NBA League Pass",
            "score_display": "—",
            "is_finished": True
        }

        try:
            out_pdf = NBAReportGenerator.generate_report(game, parsed)
            if out_pdf and os.path.exists(out_pdf):
                success_count += 1
        except Exception as e:
            print(f"Erro em {f}: {e}")

    print(f"\nSucesso total! {success_count} relatórios oficiais da NBA foram gerados/atualizados com fuso BRT!")

if __name__ == "__main__":
    generate_all()
