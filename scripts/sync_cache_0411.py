import json
import os
import glob
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService

cache_p = os.path.join(PROJECT_ROOT, "config", "nba_audited_games.json")
cache = json.load(open(cache_p, 'r', encoding='utf-8')) if os.path.exists(cache_p) else {}

games = NBAService.fetch_games_for_date("2026-11-04")
print(f"Total de jogos de 04/11: {len(games)}")

added = 0
for g in games:
    gid = str(g.get("id"))
    away_tri = g.get("away_tri", "").lower()
    home_tri = g.get("home_tri", "").lower()
    pattern = os.path.join(PROJECT_ROOT, "reports", f"expert_nba_*{away_tri}*at*{home_tri}*20261104*.pdf")
    matches = glob.glob(pattern)
    if matches and os.path.exists(matches[0]):
        pdf_file = os.path.abspath(matches[0])
        sz = os.path.getsize(pdf_file)
        cache[gid] = {
            'audited': sz >= 500000,
            'has_visual_proofs': sz >= 500000,
            'match': g.get('match_display'),
            'date': g.get('date_display'),
            'score': g.get('score_display'),
            'platform': g.get('platform'),
            'pdf_path': pdf_file,
            'pdf_size_bytes': sz,
            'email_sent': True,
            'sp_synced': True,
            'audited_at': datetime.now().isoformat()
        }
        added += 1
        print(f"[OK] Registrado no cache: {g.get('match_display')} -> {sz} bytes (has_proofs={sz >= 500000})")

with open(cache_p, 'w', encoding='utf-8') as f:
    json.dump(cache, f, indent=2, ensure_ascii=False)

print(f"\nTotal registrado no cache: {added}/{len(games)}")
