from datetime import datetime, timezone, timedelta
import zoneinfo

brt = timezone(timedelta(hours=-3))

timestamps = {
    'Gaucha': 1793545036,
    'Gaucha Esportes': 1793545045,
    'Bage TV': 1793545529,
    'Band RS': 1793559527
}

for name, ts in timestamps.items():
    dt_utc = datetime.fromtimestamp(ts, timezone.utc)
    dt_brt = dt_utc.astimezone(brt)
    print(f"{name}: Início Live = {dt_brt.strftime('%Y-%m-%d %H:%M:%S')} BRT (ts: {ts})")
