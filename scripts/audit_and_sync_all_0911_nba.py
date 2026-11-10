"""
Script para Auditar, Gerar Relatórios Completos com Comprovação Visual (8 etapas)
e Sincronizar Todos os 8 Jogos da NBA de 09/11/2026 no SharePoint (Relatorios_de_Jogos_NBA).
Substitui qualquer stub ou arquivo corrompido/agendado anterior.
"""

import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService
from modules.nba_report_generator import NBAReportGenerator
from modules.sharepoint_nba_reporter import SharePointNBAReporter
from modules.nba_autonomous_auditor import NBAAutonomousAuditor

def main():
    print("=" * 70)
    print("🏀 AUDITORIA E SINCRONIZAÇÃO COMPLETA DA NBA — 09/11/2026")
    print("=" * 70)

    svc = NBAService()
    reporter = NBAReportGenerator()
    auditor = NBAAutonomousAuditor()

    games = svc.fetch_games_for_date("2026-11-09")
    print(f"Total de partidas localizadas em 09/11/2026: {len(games)}")

    success_count = 0
    for idx, game in enumerate(games, 1):
        match_disp = game.get("match_display")
        away_tri = game.get("away_tri")
        home_tri = game.get("home_tri")
        score = game.get("score_display")
        print(f"\n[{idx}/{len(games)}] Processando: {match_disp} (Placar: {score})")

        # 1. Download do Game Book oficial
        gb_path = svc.download_gamebook(game, force=False)
        if not gb_path or not os.path.exists(gb_path):
            print(f"  ❌ Falha no download do Game Book para {match_disp}")
            continue

        # 2. Parseamento canônico do Game Book
        parsed = svc.parse_gamebook(gb_path, home_tri=home_tri, date_clean=game.get("date_clean"))
        milestones = parsed.get("milestones", [])
        if not milestones:
            print(f"  ❌ Nenhum marco oficial extraído para {match_disp}")
            continue

        print(f"  ✅ Game Book oficial: {len(milestones)} marcos temporais extraídos.")

        # 3. Geração do Relatório PDF completo com Comprovação Visual
        try:
            pdf = reporter.generate_report(game, parsed)
            pdf_size = os.path.getsize(pdf) if os.path.exists(pdf) else 0
            print(f"  ✅ PDF gerado: {os.path.basename(pdf)} ({pdf_size:,} bytes)")
        except Exception as ex_rep:
            print(f"  ❌ Erro ao gerar PDF: {ex_rep}")
            continue

        if pdf_size < 500_000:
            print(f"  ⚠️ PDF menor que 500 KB ({pdf_size} bytes). Comprovação visual incompleta!")
            continue

        # 4. Upload e Homologação definitiva no SharePoint
        for attempt in range(3):
            try:
                print(f"  ☁️ Enviando ao SharePoint (Relatorios_de_Jogos_NBA)... [Tentativa {attempt+1}]")
                sp_ok = SharePointNBAReporter.sync_nba_report(pdf, game)
                if sp_ok:
                    print(f"  🎉 HOMOLOGADO NO SHAREPOINT: {match_disp}!")
                    auditor.mark_game_audited(game, pdf, email_sent=False, sp_synced=True)
                    success_count += 1
                    break
                else:
                    print(f"  ⚠️ Tentativa {attempt+1} falhou. Aguardando...")
                    time.sleep(5)
            except Exception as ex_sp:
                print(f"  ⚠️ Erro no SharePoint: {ex_sp}")
                time.sleep(10)

        time.sleep(3)

    print("\n" + "=" * 70)
    print(f"🎉 FINALIZADO: {success_count}/{len(games)} partidas de 09/11 homologadas com 100% de conformidade!")
    print("=" * 70)

if __name__ == "__main__":
    main()
