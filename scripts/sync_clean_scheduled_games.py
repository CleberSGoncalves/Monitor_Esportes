import json
import os
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_PATH = os.path.join(PROJECT_ROOT, "config", "scheduled_games.json")
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", ""), "Monitor_Esportes", "config")
APPDATA_PATH = os.path.join(APPDATA_DIR, "scheduled_games.json")

clean_schedule = [
  {
    "id": "game_1_29102026_2000",
    "team1": "Vasco da Gama",
    "team2": "Flamengo",
    "comp": "Brasileirão Série A",
    "date": "29/10/2026",
    "time": "20:00",
    "platform": "Amazon Prime",
    "status": "pending",
    "last_run": None,
    "report_file": None
  },
  {
    "id": "game_2_01112026_1500",
    "team1": "Palmeiras",
    "team2": "Vasco da Gama",
    "comp": "Copa do Brasil",
    "date": "01/11/2026",
    "time": "15:00",
    "platform": "Amazon Prime",
    "status": "pending",
    "last_run": None,
    "report_file": None
  },
  {
    "id": "game_3_01112026_1730",
    "team1": "Grêmio",
    "team2": "Atlético-MG",
    "comp": "Copa do Brasil",
    "date": "01/11/2026",
    "time": "17:30",
    "platform": "Amazon Prime",
    "status": "pending",
    "last_run": None,
    "report_file": None
  },
  {
    "id": "game_4_04112026_1930",
    "team1": "Athletico-PR",
    "team2": "Vasco da Gama",
    "comp": "Brasileirão Série A",
    "date": "04/11/2026",
    "time": "19:30",
    "platform": "CazéTV",
    "status": "pending",
    "last_run": None,
    "report_file": None
  },
  {
    "id": "game_5_05112026_2130",
    "team1": "Cruzeiro",
    "team2": "Bahia",
    "comp": "Brasileirão Série A",
    "date": "05/11/2026",
    "time": "21:30",
    "platform": "Amazon Prime",
    "status": "pending",
    "last_run": None,
    "report_file": None
  }
]

os.makedirs(os.path.dirname(LOCAL_PATH), exist_ok=True)
with open(LOCAL_PATH, "w", encoding="utf-8") as f:
    json.dump(clean_schedule, f, indent=2, ensure_ascii=False)
print(f"Updated local config: {LOCAL_PATH}")

if os.path.exists(APPDATA_DIR):
    with open(APPDATA_PATH, "w", encoding="utf-8") as f:
        json.dump(clean_schedule, f, indent=2, ensure_ascii=False)
    print(f"Updated appdata config: {APPDATA_PATH}")
