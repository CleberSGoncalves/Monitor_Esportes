import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.web_verdict_collector import build_query, get_web_verdict

print("Testing get_web_verdict...")
gv = get_web_verdict("Fluminense", "Internacional", "28/10/2026", "Brasileirão Série A")
print("Result:")
print(json.dumps(gv, indent=2, ensure_ascii=False))
