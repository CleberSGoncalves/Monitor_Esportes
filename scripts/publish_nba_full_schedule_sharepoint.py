"""
Script para sincronizar e publicar imediatamente todos os eventos da NBA
(passados, ao vivo e previstos para os próximos 6 dias) na lista e biblioteca
'Relatorios_de_Jogos_NBA' do SharePoint.
"""

import os
import sys
import time
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService
from modules.nba_report_generator import NBAReportGenerator
from modules.sharepoint_nba_reporter import SharePointNBAReporter

def main():
    service = NBAService()
    reporter = NBAReportGenerator()

    # Datas: ontem (-1), hoje (0), e os próximos 6 dias (+1 a +6)
    base_dt = datetime.now()
    dates = [(base_dt + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 7)]

    print(f"================================================================")
    print(f"🏀 Sincronizador de Agenda e Auditoria NBA -> SharePoint")
    print(f"Período: {dates[0]} até {dates[-1]}")
    print(f"================================================================")

    all_games = []
    for d_str in dates:
        games = service.fetch_games_for_date(d_str)
        print(f"📅 Data {d_str}: {len(games)} jogos encontrados.")
        all_games.extend(games)

    total = len(all_games)
    print(f"\nTotal consolidado: {total} partidas na grade oficial da NBA.")
    print("Iniciando publicação/sincronização na biblioteca 'Relatorios_de_Jogos_NBA'...\n")

    success = 0
    errors = 0

    for idx, g in enumerate(all_games, 1):
        match_disp = g.get("match_display")
        date_disp = g.get("date_display")
        time_brt = g.get("time_brt")
        plat = g.get("platform")
        is_fin = g.get("is_finished")
        score = g.get("score_display")

        status_tag = f"FINALIZADO ({score})" if is_fin else f"AGENDADO ({time_brt} BRT)"
        print(f"[{idx}/{total}] Sincronizando: {match_disp} ({date_disp}) | {plat} | {status_tag}...")

        try:
            gb_path = service.download_gamebook(g) if is_fin else None
            parsed = service.parse_gamebook(gb_path) if gb_path else {}
            pdf = reporter.generate_report(g, parsed)

            ok = SharePointNBAReporter.sync_nba_report(pdf, g)
            if ok:
                success += 1
                print(f"      ✅ Publicado com sucesso no SharePoint!")
            else:
                errors += 1
                print(f"      ⚠️ Falha ao publicar {match_disp}.")
        except Exception as e:
            errors += 1
            print(f"      ❌ Erro: {e}")

        # Pequeno intervalo para respeitar o rate limit do Microsoft Graph
        time.sleep(1.8)

    print(f"\n================================================================")
    print(f"🎯 Concluído! {success} de {total} partidas sincronizadas com sucesso!")
    if errors > 0:
        print(f"⚠️ Houve {errors} falha(s).")
    print(f"================================================================")

if __name__ == "__main__":
    main()
