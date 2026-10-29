import sys
from datetime import datetime, timedelta

sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.nba_service import NBAService

start_dt = datetime(2026, 10, 20)
end_dt = datetime(2026, 10, 29)
curr = start_dt
all_games = {}
duplicates = []

while curr <= end_dt:
    d_str = curr.strftime("%Y-%m-%d")
    games = NBAService.fetch_games_for_date(d_str)
    fin_count = sum(1 for g in games if g["is_finished"])
    print(f"Date {d_str}: {len(games)} games ({fin_count} finalizados)")
    for g in games:
        gid = g["id"]
        match = g["match_display"]
        date_clean = g.get("date_clean")
        sp_filename = f"Relatorio_NBA_{g.get('away_tri')}_at_{g.get('home_tri')}_{date_clean}.pdf"
        if gid in all_games:
            prev = all_games[gid]
            duplicates.append((gid, match, prev["date"], d_str))
            print(f"   ⚠️ DUPLICATA DETECTADA: {gid} - {match} em {prev['date']} E {d_str}")
        all_games[gid] = {
            "date": d_str,
            "match": match,
            "finished": g["is_finished"],
            "score": g["score_display"],
            "status": g["status"],
            "sp_filename": sp_filename
        }
    curr += timedelta(days=1)

print("\n" + "="*60)
print(f"Total de jogos únicos (20/10 a 29/10): {len(all_games)}")
finished = [g for g in all_games.values() if g["finished"]]
print(f"Jogos finalizados que já aconteceram: {len(finished)}")
print(f"Duplicatas encontradas na busca por data: {len(duplicates)}")
for d in duplicates:
    print(f"  • ID {d[0]}: {d[1]} (Datas: {d[2]} e {d[3]})")
