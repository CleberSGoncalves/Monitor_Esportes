import json
import os
from modules.expert_assistant import ExpertAssistant

def run_test():
    config_path = os.path.join("config", "google_ai.json")
    if not os.path.exists(config_path):
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
        api_key = config_data.get("gemini_api_key") or config_data.get("api_key")

    assistant = ExpertAssistant(api_key=api_key, model_id="gemini-2.5-flash")

    print("[TESTE] Consultando partida REAL: Palmeiras x Flamengo (28/01/2023)")
    try:
        result = assistant.get_match_chronology(
            team1="Palmeiras",
            team2="Flamengo",
            competition="Supercopa do Brasil",
            platform="YouTube",
            date="28/01/2023"
        )
        print("\n=== RESULTADO (JSON PARSEADO COM SUCESSO) ===")
        print(json.dumps(result, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"\n[ERRO FATAL] {e}")

if __name__ == "__main__":
    run_test()
