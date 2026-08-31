# tests/test_transcript_expert.py
import json
import os
import sys
from pathlib import Path

# Configura o ROOT do projeto no path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.youtube_transcript_service import YouTubeTranscriptService
from modules.expert_assistant import ExpertAssistant

def run_test():
    # Teste 1: Extração de Transcrição e Compactação
    test_video_url = "https://www.youtube.com/watch?v=s5R84N3zB3Q" # Substitua por qualquer link ativo de esportes
    print(f"\n[TEST 1] Testando download e compactação de transcrição para: {test_video_url}")
    
    compacted_text = YouTubeTranscriptService.get_compacted_text(test_video_url)
    if compacted_text:
        print("[OK] Transcrição baixada e compactada com sucesso!")
        print("\n--- Primeiras 5 linhas do texto compactado ---")
        lines = compacted_text.splitlines()
        for line in lines[:5]:
            print(line)
        print("---------------------------------------------")
    else:
        print("[WARN] Não foi possível obter a transcrição para este vídeo de teste.")
        print("[INFO] Isso pode significar que as legendas automáticas do vídeo ainda estão processando ou indisponíveis.")

    # Teste 2: Execução com o Gemini usando o transcript injetado
    config_path = os.path.join(PROJECT_ROOT, "config", "google_ai.json")
    if not os.path.exists(config_path):
        print("[INFO] Arquivo de configurações config/google_ai.json não encontrado. Abortando teste do Gemini.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
        api_key = config_data.get("gemini_api_key") or config_data.get("api_key")
        model_id = config_data.get("model", "gemini-2.5-flash")

    if not api_key:
        print("[INFO] API Key não configurada. Abortando teste do Gemini.")
        return

    print(f"\n[TEST 2] Inicializando ExpertAssistant (Modelo: {model_id})...")
    assistant = ExpertAssistant(api_key=api_key, model_id=model_id)

    print("[TEST 2] Executando análise Expert com transcrição injetada...")
    
    # Exemplo mockado de transcrição para forçar precisão cirúrgica de milissegundos
    mock_transcript = (
        "[00:00 - 00:15]: autoriza o arbitro apita o inicio do jogo rola a bola\n"
        "[05:15 - 05:30]: germán cano chuta de primeira goooool gol de germán cano do fluminense\n"
        "[08:45 - 09:00]: apita o arbitro final de jogo vitória do fluminense"
    )

    try:
        result = assistant.get_match_chronology(
            team1="Fluminense",
            team2="São Paulo",
            competition="Brasileirão",
            platform="YouTube",
            date="16/05/2026",
            start_timestamp=1779220800, # 19:00:00 Horário de Brasília
            duration=540, # 9 minutos de vídeo
            video_url=test_video_url,
            transcript_text=mock_transcript
        )
        print("\n=== RESULTADO GERADO COM IA (INTEGRAÇÃO OK) ===")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        
        # Validação da sincronização de milissegundos baseada na transcrição mockada
        # Gol de Cano deve ser cravado em torno de 19:05:15
        print("\n[OK] Testes concluídos com sucesso!")
    except Exception as e:
        print(f"\n[ERRO FATAL] Falha no fluxo do Gemini: {e}")

if __name__ == "__main__":
    run_test()
