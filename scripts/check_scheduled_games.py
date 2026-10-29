import json
import os

path = "config/scheduled_games.json"
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        games = json.load(f)
    print(f"Total scheduled games: {len(games)}")
    for g in games:
        d = g.get("date", "")
        t = g.get("time", "")
        t1 = g.get("team1", "")
        t2 = g.get("team2", "")
        plat = g.get("platform", "")
        st = g.get("status", "")
        print(f"{d} {t} | {t1} x {t2} | {plat} | {st}")
else:
    print("config/scheduled_games.json not found")
