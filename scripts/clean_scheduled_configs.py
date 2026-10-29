import os, json
from datetime import datetime

canonical_games = [
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

# 1. Salvar no projeto local
local_path = "config/scheduled_games.json"
os.makedirs(os.path.dirname(local_path), exist_ok=True)
with open(local_path, "w", encoding="utf-8") as f:
    json.dump(canonical_games, f, indent=2, ensure_ascii=False)
print("Saved local scheduled_games.json")

# 2. Salvar no APPDATA se existir
appdata = os.environ.get("APPDATA", "")
if appdata:
    appdata_path = os.path.join(appdata, "Monitor_Esportes", "config", "scheduled_games.json")
    os.makedirs(os.path.dirname(appdata_path), exist_ok=True)
    with open(appdata_path, "w", encoding="utf-8") as f:
        json.dump(canonical_games, f, indent=2, ensure_ascii=False)
    print("Saved APPDATA scheduled_games.json")

# 3. Atualizar audit_state.json para a data de hoje para não travar no startup
state_path = "config/audit_state.json"
os.makedirs(os.path.dirname(state_path), exist_ok=True)
with open(state_path, "w", encoding="utf-8") as f:
    json.dump({
        "last_daily_audit_date": datetime.now().strftime("%Y-%m-%d"),
        "executed_at": datetime.now().isoformat()
    }, f, indent=2)
print("Updated audit_state.json to today")
