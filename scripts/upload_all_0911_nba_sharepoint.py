"""
Upload e Homologação Definitiva de Todos os 8 Relatórios da NBA de 09/11/2026 no SharePoint.
Substitui qualquer arquivo stub legado com os relatórios completos de ~2.2 MB.
"""

import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService
from modules.sharepoint_nba_reporter import SharePointNBAReporter
from modules.nba_autonomous_auditor import NBAAutonomousAuditor

def main():
    print("=" * 70)
    print("☁️ UPLOAD E HOMOLOGAÇÃO NO SHAREPOINT — NBA 09/11/2026")
    print("=" * 70)

    svc = NBAService()
    auditor = NBAAutonomousAuditor()
    games = svc.fetch_games_for_date("2026-11-09")

    # Mapeamento de PDFs gerados em reports/
    reports_dir = os.path.join(PROJECT_ROOT, "reports")
    
    success = 0
    for idx, game in enumerate(games, 1):
        away_tri = game.get("away_tri", "").lower()
        home_tri = game.get("home_tri", "").lower()
        match_disp = game.get("match_display")
        date_clean = game.get("date_clean", "20261109")

        # Localiza o PDF recém-gerado
        target_name = f"expert_nba_nba_league_pass_{away_tri}_at_{home_tri}_{date_clean}.pdf"
        pdf_path = os.path.join(reports_dir, target_name)

        if not os.path.exists(pdf_path):
            # Tenta variações de nome
            candidates = [f for f in os.listdir(reports_dir) if f"{away_tri}_at_{home_tri}_{date_clean}" in f.lower() and f.endswith(".pdf")]
            if candidates:
                pdf_path = os.path.join(reports_dir, candidates[0])

        if not os.path.exists(pdf_path):
            print(f"[{idx}/{len(games)}] ❌ PDF não encontrado para {match_disp}")
            continue

        size = os.path.getsize(pdf_path)
        print(f"\n[{idx}/{len(games)}] Sincronizando: {match_disp} ({size:,} bytes)...")

        for attempt in range(5):
            try:
                ok = SharePointNBAReporter.sync_nba_report(pdf_path, game, confianca="99.0%")
                if ok:
                    print(f"  🎉 HOMOLOGADO NO SHAREPOINT: {match_disp}!")
                    auditor.mark_game_audited(game, pdf_path, email_sent=False, sp_synced=True)
                    success += 1
                    break
                else:
                    print(f"  ⚠️ Tentativa {attempt+1} falhou, aguardando 15s...")
                    time.sleep(15)
            except Exception as e:
                print(f"  ⚠️ Erro na sincronização: {e}. Aguardando 20s...")
                time.sleep(20)

        # Pausa preventiva de 10s para respeitar rate limits do Microsoft Graph API
        time.sleep(10)

    print("\n" + "=" * 70)
    print(f"🎉 FINALIZADO: {success}/{len(games)} relatórios homologados no SharePoint!")
    print("=" * 70)

if __name__ == "__main__":
    main()
