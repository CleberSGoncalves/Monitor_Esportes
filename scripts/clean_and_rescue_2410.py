import os
import sys
import json
import re

sys.path.insert(0, ".")

state_file = os.path.join(os.environ.get("APPDATA", ""), "Monitor_Esportes", "live_channels", "state.json")
if not os.path.exists(state_file):
    print("state.json nao encontrado em AppData!")
    exit(0)

with open(state_file, "r", encoding="utf-8") as f:
    st = json.load(f)

events = st.get("events", {})
active_queue = st.get("active_queue", [])

from modules.narration_chronology import is_likely_match, is_definitely_non_match

print(f"Total eventos antes: {len(events)}")
print(f"Fila ativa antes: {len(active_queue)}")

removed_count = 0
cleaned_queue = []

for vid in active_queue:
    ev = events.get(vid)
    if not ev:
        continue
    title = ev.get("title", "")
    dur = int(ev.get("duration") or 0)
    is_non, _ = is_definitely_non_match(title)
    
    # Se for não-jogo, descarta da fila
    if is_non or not is_likely_match(title, dur):
        ev["selected"] = False
        ev["user_unselected"] = True
        ev["pipeline"] = "not_match"
        removed_count += 1
    else:
        cleaned_queue.append(vid)

# Resgata os jogos de 24/10 (Inter x Botafogo)
for vid, ev in events.items():
    title = ev.get("title", "")
    if "INTER X BOTAFOGO" in title.upper() and ("24/10" in title or "24/10" in str(ev.get("scheduled_epoch"))):
        ev["status"] = "ended"
        ev["pipeline"] = "ended"
        ev["selected"] = True
        ev["is_match_narration"] = True
        ev["meta"] = {
            "team1": "Internacional",
            "team2": "Botafogo",
            "competition": "Brasileirão Série A",
            "date": "24/10/2026"
        }
        if vid not in cleaned_queue:
            cleaned_queue.append(vid)

st["active_queue"] = cleaned_queue

with open(state_file, "w", encoding="utf-8") as f:
    json.dump(st, f, indent=2, ensure_ascii=False)

print(f"Removidos da fila: {removed_count}")
print(f"Fila ativa agora: {len(cleaned_queue)}")
for vid in cleaned_queue:
    ev = events.get(vid, {})
    print(f"-> NA FILA: [{ev.get('status')}] {ev.get('title')[:60]}")
