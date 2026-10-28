import json
import os
from modules.cbf_schedule_fetcher import CBFScheduleFetcher

events = CBFScheduleFetcher.get_upcoming_matches(force_refresh=True)
initial = []
for i, e in enumerate(events, 1):
    d_clean = e.get("date", "").replace("/", "")
    t_clean = e.get("time", "").replace(":", "")
    initial.append({
        "id": f"game_{i}_{d_clean}_{t_clean}",
        "team1": e.get("team1"),
        "team2": e.get("team2"),
        "comp": e.get("comp"),
        "date": e.get("date"),
        "time": e.get("time"),
        "platform": e.get("platform"),
        "status": "pending",
        "last_run": None,
        "report_file": None
    })

cfg_dir = os.path.join(os.path.dirname(__file__), "config")
os.makedirs(cfg_dir, exist_ok=True)
path_local = os.path.join(cfg_dir, "scheduled_games.json")
with open(path_local, "w", encoding="utf-8") as f:
    json.dump(initial, f, indent=2, ensure_ascii=False)

appdata = os.environ.get("APPDATA", "")
if appdata:
    app_cfg = os.path.join(appdata, "Monitor_Esportes", "config")
    os.makedirs(app_cfg, exist_ok=True)
    with open(os.path.join(app_cfg, "scheduled_games.json"), "w", encoding="utf-8") as f2:
        json.dump(initial, f2, indent=2, ensure_ascii=False)

print(f"Sucesso: {len(initial)} jogos futuros oficiais gravados na fila.")
