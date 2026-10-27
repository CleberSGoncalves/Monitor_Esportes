import json
import sys
sys.path.insert(0, ".")
from modules.expert_assistant import ExpertAssistant

k = json.load(open("config/google_ai.json"))["gemini_api_key"]
ea = ExpertAssistant(k)

jogos = [
    ("Coritiba", "Botafogo", "12/10/2026", "Brasileirão Série A", "Amazon Prime"),
    ("Vasco da Gama", "Remo", "10/10/2026", "Brasileirão Série A", "CazéTV"),
]
for t1, t2, d, comp, plat in jogos:
    for i in range(2):
        v = ea.get_grounding_audit_verdict(t1, t2, d, comp, plat)
        print(f"=== {t1} x {t2} (execução {i+1}) ===")
        print(v["verdict_text"])
        print("REFS:", [r["title"] for r in v["references"]])
        print()
