import os
import re

gui_path = r"e:\desenvolvimento\Monitor_Esportes\gui\main_gui.py"
with open(gui_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Clean _load_cbf_streaming_events
target_load = '''def _load_cbf_streaming_events() -> list:

    """Lê os eventos oficiais de transmissão do projeto Streaming_Scheduler (E:\desenvolvimento\Streaming_Scheduler\data.csv)."""

    scheduler_csv = r"E:\desenvolvimento\Streaming_Scheduler\data.csv"

    fallback_csv = os.path.join(PROJECT_ROOT, "config", "streaming_data.csv")

    

    csv_path = scheduler_csv if os.path.exists(scheduler_csv) else fallback_csv'''

replacement_load = '''def _load_cbf_streaming_events() -> list:

    """Lê os eventos oficiais de transmissão configurados no projeto."""

    csv_path = os.path.join(PROJECT_ROOT, "config", "streaming_data.csv")'''

# 2. Clean block 1 (~13890)
target_b1 = '''        csv_evts = _load_cbf_streaming_events()

        combined_evts = list(cbf_evts) if cbf_evts else []

        seen_s = {f"{e.get('team1')}_{e.get('team2')}_{e.get('date')}".lower() for e in combined_evts}

        for ce in csv_evts:

            cs = f"{ce.get('team1')}_{ce.get('team2')}_{ce.get('date')}".lower()

            if cs not in seen_s:

                combined_evts.append(ce)

                seen_s.add(cs)

        cbf_evts = combined_evts'''

# 3. Clean block 2 (~15115)
target_b2 = '''                csv_events = _load_cbf_streaming_events()

                combined_events = list(cbf_events) if cbf_events else []

                seen_sigs = {f"{e.get('team1')}_{e.get('team2')}_{e.get('date')}".lower() for e in combined_events}

                for ce in csv_events:

                    csig = f"{ce.get('team1')}_{ce.get('team2')}_{ce.get('date')}".lower()

                    if csig not in seen_sigs:

                        combined_events.append(ce)

                        seen_sigs.add(csig)

                cbf_events = combined_events'''

if '\r\n' in text:
    target_load = target_load.replace('\n', '\r\n')
    replacement_load = replacement_load.replace('\n', '\r\n')
    target_b1 = target_b1.replace('\n', '\r\n')
    target_b2 = target_b2.replace('\n', '\r\n')

if target_load in text:
    text = text.replace(target_load, replacement_load, 1)
    print("Cleaned _load_cbf_streaming_events!")
else:
    print("target_load not found")

if target_b1 in text:
    text = text.replace(target_b1, "", 1)
    print("Cleaned target_b1!")
else:
    print("target_b1 not found")

if target_b2 in text:
    text = text.replace(target_b2, "", 1)
    print("Cleaned target_b2!")
else:
    print("target_b2 not found")

with open(gui_path, "w", encoding="utf-8") as f:
    f.write(text)
print("main_gui.py cleaned!")
