import os
import json
import glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_files = [
    os.path.join(PROJECT_ROOT, "config", "scheduled_games.json"),
    os.path.join(os.getenv("APPDATA", ""), "Monitor_Esportes", "config", "scheduled_games.json")
]

p_vasco_pdf = glob.glob(os.path.join(PROJECT_ROOT, "reports", "*palmeiras*vasco*01112026*.pdf"))
g_atletico_pdf = glob.glob(os.path.join(PROJECT_ROOT, "reports", "*grêmio*atlético*01112026*.pdf"))

p_vasco_path = p_vasco_pdf[-1] if p_vasco_pdf else None
g_atletico_path = g_atletico_pdf[-1] if g_atletico_pdf else None

for c_path in config_files:
    if os.path.exists(c_path):
        with open(c_path, "r", encoding="utf-8") as f:
            games = json.load(f)
        for g in games:
            if "Palmeiras" in g.get("team1", "") and "Vasco" in g.get("team2", "") and g.get("date") == "01/11/2026":
                g["status"] = "completed"
                g["time"] = "16:00"
                g["report_file"] = p_vasco_path
                g["last_run"] = "03/11/2026 15:56:43"
            elif "Grêmio" in g.get("team1", "") and "Atlético" in g.get("team2", "") and g.get("date") == "01/11/2026":
                g["status"] = "completed"
                g["time"] = "17:30"
                g["report_file"] = g_atletico_path
                g["last_run"] = "03/11/2026 15:57:30"
            elif "Vasco" in g.get("team1", "") and "Flamengo" in g.get("team2", "") and g.get("date") == "29/10/2026":
                # Finalizado
                g["status"] = "completed"
        with open(c_path, "w", encoding="utf-8") as f:
            json.dump(games, f, indent=2, ensure_ascii=False)
        print(f"Updated {c_path}")
