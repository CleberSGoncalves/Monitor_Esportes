import os
import sys
import json
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService

def populate_cache():
    s = NBAService()
    now_dt = datetime.now()
    season_start = datetime(2026, 10, 20)
    days_span = max(1, (now_dt - season_start).days + 1)
    dates = [(season_start + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(days_span + 1)]

    cache_path = os.path.join(PROJECT_ROOT, "config", "nba_audited_games.json")
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    total_added = 0
    for d_str in dates:
        games = s.fetch_games_for_date(d_str)
        for g in games:
            gid = str(g.get("id"))
            if g.get("is_finished"):
                if gid not in cache:
                    cache[gid] = {
                        "audited": True,
                        "match": g.get("match_display"),
                        "date": g.get("date_display"),
                        "score": g.get("score_display"),
                        "platform": g.get("platform"),
                        "pdf_path": "",
                        "email_sent": True,
                        "sp_synced": True,
                        "audited_at": datetime.now().isoformat()
                    }
                    total_added += 1

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    print(f"Sucesso! {len(cache)} partidas da NBA registradas no cache. {total_added} novas marcadas como auditadas.")

if __name__ == "__main__":
    populate_cache()
