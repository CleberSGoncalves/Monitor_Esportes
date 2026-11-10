"""
Gera localmente todos os 8 PDFs oficiais da NBA de 09/11/2026 com:
- Game Book oficial (8 marcos temporais)
- Comprovação visual completa (8/8 frames reais dos vídeos oficiais de Highlights)
- Horários BRT sincronizados
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService
from modules.nba_report_generator import NBAReportGenerator

def main():
    print("=" * 70)
    print("🏀 GERAÇÃO LOCAL DE RELATÓRIOS OFICIAIS DA NBA — 09/11/2026")
    print("=" * 70)

    svc = NBAService()
    reporter = NBAReportGenerator()

    games = svc.fetch_games_for_date("2026-11-09")
    print(f"Total de partidas: {len(games)}")

    generated = []
    for idx, game in enumerate(games, 1):
        match_disp = game.get("match_display")
        away_tri = game.get("away_tri")
        home_tri = game.get("home_tri")
        score = game.get("score_display")
        print(f"\n[{idx}/{len(games)}] Processando: {match_disp} ({score})")

        gb_path = svc.download_gamebook(game, force=False)
        parsed = svc.parse_gamebook(gb_path, home_tri=home_tri, date_clean=game.get("date_clean"))
        milestones = parsed.get("milestones", [])
        if not milestones:
            print(f"  ❌ Sem marcos oficiais para {match_disp}")
            continue

        pdf = reporter.generate_report(game, parsed)
        pdf_size = os.path.getsize(pdf) if os.path.exists(pdf) else 0
        print(f"  ✅ PDF gerado: {os.path.basename(pdf)} ({pdf_size:,} bytes)")
        generated.append((game, pdf, pdf_size))

    print("\n" + "=" * 70)
    print(f"🎉 CONCLUÍDO: {len(generated)}/{len(games)} relatórios oficiais gerados com sucesso!")
    print("=" * 70)

if __name__ == "__main__":
    main()
