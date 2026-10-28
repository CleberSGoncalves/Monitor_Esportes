import os
import json

state_file = os.path.join(os.environ.get("APPDATA", ""), "Monitor_Esportes", "live_channels", "state.json")
with open(state_file, "r", encoding="utf-8") as f:
    st = json.load(f)

events = st.get("events", {})
print(f"Total eventos: {len(events)}")
for k, v in list(events.items()):
    t = v.get("title", "")
    ch = v.get("channel_name", "")
    p = v.get("pipeline")
    err = v.get("error")
    s = f"[{ch}] {k}: {t[:50]} | pipe={p} | err={err[:50] if err else None}"
    print(s.encode('ascii', 'ignore').decode())
