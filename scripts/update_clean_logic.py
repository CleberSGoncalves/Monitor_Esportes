# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("modules/live_channel_monitor.py")
content = p.read_text(encoding="utf-8")

old_code = '''                    is_active = ev.get("pipeline") in ("live", "transcribing", "analyzing", "generating") or ev.get("status") in ("live", "upcoming")'''

new_code = '''                    now = time.time()
                    is_live = ev.get("pipeline") in ("live", "transcribing", "analyzing", "generating") or ev.get("status") == "live"
                    sched = float(ev.get("scheduled_epoch") or 0)
                    is_future = ev.get("status") == "upcoming" and sched > now
                    is_active = is_live or is_future'''

if old_code in content:
    content = content.replace(old_code, new_code)
    p.write_text(content, encoding="utf-8")
    print("SUCCESS: clean_queue_keep_active updated!")
else:
    print("WARNING: old_code not found")
