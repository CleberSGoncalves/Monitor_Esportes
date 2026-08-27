import json
import os
from modules.expert_assistant import ExpertAssistant

def run_test():
    config_path = os.path.join("config", "google_ai.json")
    if not os.path.exists(config_path):
        print("Erro: Arquivo config/google_ai.json não encontrado.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
        api_key = config_data.get("gemini_api_key") or config_data.get("api_key")

    print("[TESTE] Iniciando Expert Assistant...")
    # Usando o modelo que você definiu que funciona bem com Grounding
    assistant = ExpertAssistant(api_key=api_key, model_id="gemini-2.5-flash")

    print("[TESTE] Consultando partida: Fluminense x Chapecoense (26/04/2026)")
    try:
        result = assistant.get_match_chronology(
            team1="Fluminense",
            team2="Chapecoense",
            competition="Brasileirão 2026",
            platform="YouTube",
            date="26/04/2026"
        )
        print("\n=== RESULTADO (JSON PARSEADO COM SUCESSO) ===")
        print(json.dumps(result, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"\n[ERRO FATAL] {e}")

if __name__ == "__main__":
    run_test()
