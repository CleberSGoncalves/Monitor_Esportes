# scripts/reprocess_nba_brt.py
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService
from modules.nba_report_generator import NBAReportGenerator
from modules.sharepoint_nba_reporter import SharePointNBAReporter

def reprocess_all():
    start_date = datetime(2026, 10, 20)
    end_date = datetime(2026, 11, 3)
    
    cur = start_date
    total_processed = 0
    total_synced = 0

    print(f"Iniciando reprocessamento dos relatorios da NBA de {start_date.strftime('%d/%m/%Y')} ate {end_date.strftime('%d/%m/%Y')} com fuso horario BRT...")

    while cur <= end_date:
        d_str = cur.strftime("%Y-%m-%d")
        print(f"\nProcessando data: {d_str}...")
        try:
            games = NBAService.fetch_games_for_date(d_str)
        except Exception as e:
            print(f"Erro ao buscar jogos de {d_str}: {e}")
            games = []

        for game in games:
            if not game.get("is_finished"):
                continue

            match_disp = game.get("match_display", "")
            print(f"  Jogo: {match_disp}...")
            try:
                gb_path = NBAService.download_gamebook(game)
                parsed = NBAService.parse_gamebook(gb_path) if gb_path else {}
                pdf_path = NBAReportGenerator.generate_report(game, parsed)
                total_processed += 1
                print(f"     Relatorio PDF BRT gerado: {os.path.basename(pdf_path)}")
                
                # Sincronizar com SharePoint
                try:
                    ok = SharePointNBAReporter.sync_nba_report(pdf_path, game)
                    if ok:
                        total_synced += 1
                        print(f"     Sincronizado no SharePoint: {match_disp}")
                    else:
                        print(f"     SharePoint retorno False para {match_disp}")
                except Exception as sp_err:
                    print(f"     Erro SharePoint: {sp_err}")
            except Exception as g_err:
                print(f"     Erro no jogo {match_disp}: {g_err}")

        cur += timedelta(days=1)

    print(f"\nConcluido! Total de relatorios NBA BRT processados: {total_processed} | Sincronizados: {total_synced}")

if __name__ == "__main__":
    reprocess_all()
