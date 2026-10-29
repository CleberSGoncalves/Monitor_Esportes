import os

gui_path = r"e:\desenvolvimento\Monitor_Esportes\gui\main_gui.py"
with open(gui_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. First block at lines ~13890
target1 = '''        try:

            from modules.cbf_schedule_fetcher import CBFScheduleFetcher

            cbf_evts = CBFScheduleFetcher.get_upcoming_matches()

        except:

            cbf_evts = _load_cbf_streaming_events()'''

replacement1 = '''        try:

            from modules.cbf_schedule_fetcher import CBFScheduleFetcher

            cbf_evts = CBFScheduleFetcher.get_upcoming_matches()

        except:

            cbf_evts = []

        csv_evts = _load_cbf_streaming_events()

        combined_evts = list(cbf_evts) if cbf_evts else []

        seen_s = {f"{e.get('team1')}_{e.get('team2')}_{e.get('date')}".lower() for e in combined_evts}

        for ce in csv_evts:

            cs = f"{ce.get('team1')}_{ce.get('team2')}_{ce.get('date')}".lower()

            if cs not in seen_s:

                combined_evts.append(ce)

                seen_s.add(cs)

        cbf_evts = combined_evts'''

# 2. Second block at lines ~15090
target2 = '''                try:

                    cbf_events = CBFScheduleFetcher.get_upcoming_matches()

                except Exception as ex_fetch:

                    self._log(f"⏰ [AGENDAMENTO AUTOMÁTICO] Falha ao raspar CBF, usando fallback local: {ex_fetch}")

                    cbf_events = _load_cbf_streaming_events()'''

replacement2 = '''                try:

                    cbf_events = CBFScheduleFetcher.get_upcoming_matches()

                except Exception as ex_fetch:

                    self._log(f"⏰ [AGENDAMENTO AUTOMÁTICO] Falha ao raspar CBF: {ex_fetch}")

                    cbf_events = []

                csv_events = _load_cbf_streaming_events()

                combined_events = list(cbf_events) if cbf_events else []

                seen_sigs = {f"{e.get('team1')}_{e.get('team2')}_{e.get('date')}".lower() for e in combined_events}

                for ce in csv_events:

                    csig = f"{ce.get('team1')}_{ce.get('team2')}_{ce.get('date')}".lower()

                    if csig not in seen_sigs:

                        combined_events.append(ce)

                        seen_sigs.add(csig)

                cbf_events = combined_events'''

# Handle CRLF vs LF
if '\r\n' in text:
    target1 = target1.replace('\n', '\r\n')
    replacement1 = replacement1.replace('\n', '\r\n')
    target2 = target2.replace('\n', '\r\n')
    replacement2 = replacement2.replace('\n', '\r\n')

ok1 = target1 in text
ok2 = target2 in text

if ok1:
    text = text.replace(target1, replacement1, 1)
    print("Block 1 patched!")
else:
    print("Block 1 target NOT found!")

if ok2:
    text = text.replace(target2, replacement2, 1)
    print("Block 2 patched!")
else:
    print("Block 2 target NOT found!")

if ok1 or ok2:
    with open(gui_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("main_gui.py saved successfully!")
