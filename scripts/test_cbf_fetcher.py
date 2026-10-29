import sys
sys.path.insert(0, ".")
from modules.cbf_schedule_fetcher import CBFScheduleFetcher

matches = CBFScheduleFetcher.get_recent_finished_matches()
print(f"Total recent finished matches: {len(matches)}")
for m in matches:
    d = m.get('date')
    t = m.get('time')
    comp = m.get('comp')
    t1 = m.get('team1')
    t2 = m.get('team2')
    p = m.get('platform')
    print(f"{d} {t} | {comp} | {t1} x {t2} | {p}")

upcoming = CBFScheduleFetcher.get_upcoming_matches()
print(f"\nTotal upcoming matches: {len(upcoming)}")
for m in upcoming:
    d = m.get('date')
    t = m.get('time')
    comp = m.get('comp')
    t1 = m.get('team1')
    t2 = m.get('team2')
    p = m.get('platform')
    print(f"{d} {t} | {comp} | {t1} x {t2} | {p}")
