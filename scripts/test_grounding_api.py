import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

with open("config/google_ai.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

api_key = cfg.get("gemini_api_keys") or cfg.get("gemini_api_key") or cfg.get("api_key")
model_id = cfg.get("model", "gemini-2.5-flash")

from modules.expert_assistant import ExpertAssistant
ea = ExpertAssistant(api_key=api_key, model_id=model_id)

print(f"Calling get_grounding_audit_verdict with model {model_id}...")
gv = ea.get_grounding_audit_verdict("Fluminense", "Internacional", "28/10/2026", "Brasileirão Série A", "CazéTV")
print("GV Result:")
print("verdict_text:", gv.get("verdict_text"))
print("references count:", len(gv.get("references", [])))
print(json.dumps(gv, indent=2, ensure_ascii=False))
