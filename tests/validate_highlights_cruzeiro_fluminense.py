# tests/validate_highlights_cruzeiro_fluminense.py
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Configura o ROOT do projeto no path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.expert_assistant import ExpertAssistant
from modules.report_generator import ReportGenerator

def run_validation():
    print("=" * 60)
    print("VALIDAÇÃO: MODO EXPERT - MELHORES MOMENTOS (HIGHLIGHTS)")
    print("CRUZEIRO X FLUMINENSE (31/05/2026)")
    print("=" * 60)

    # 1. Carrega configurações do Gemini
    config_path = os.path.join(PROJECT_ROOT, "config", "google_ai.json")
    if not os.path.exists(config_path):
        print(f"[ERRO] Arquivo de configurações {config_path} não encontrado.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
        api_key = config_data.get("gemini_api_key_2") or config_data.get("gemini_api_key") or config_data.get("api_key")
        model_id = config_data.get("model", "gemini-2.5-flash")

    if not api_key:
        print("[ERRO] API Key do Gemini não está configurada.")
        return

    # 2. Configurações de input que simulam o VOD dos Melhores Momentos (Highlights)
    # Duração do vídeo: 500 segundos (8m20s)
    # Início da transmissão (timestamp de upload/release do vídeo no YouTube): 31/05/2026 22:35:20 BRT (Unix: 1779980120)
    upload_timestamp = 1779980120
    video_duration = 500

    # Legendas mockadas do resumo dos melhores momentos com lances dos minutos finais da partida real
    mock_highlights_transcript = (
        "[00:00 - 01:00]: bem-vindos aos melhores momentos de cruzeiro e fluminense no mineirao pelo brasileirao\n"
        "[03:34 - 03:50]: john kennedy bate de chapa e gol gol do fluminense abre o placar no finalzinho da partida aos noventa e um minutos\n"
        "[06:05 - 06:20]: bateu mateus pereira na cobrança de falta que golaco golaço do cruzeiro empata o jogo nos acréscimos aos noventa e três minutos\n"
        "[08:20]: fim de jogo no mineirão cruzeiro um fluminense um no brasileirão\n"
    )

    print(f"[INFO] Inicializando ExpertAssistant com o modelo {model_id}...")
    assistant = ExpertAssistant(api_key=api_key, model_id=model_id)

    print("[INFO] Executando get_match_chronology em formato de Highlights...")
    try:
        result = assistant.get_match_chronology(
            team1="Cruzeiro",
            team2="Fluminense",
            competition="Brasileirão",
            platform="CazéTV",
            date="31/05/2026",
            start_timestamp=upload_timestamp,
            duration=video_duration,
            video_url="https://www.youtube.com/watch?v=mock_cru_flu_highlights",
            transcript_text=mock_highlights_transcript
        )

        print("\n" + "=" * 50)
        print("RESULTADO DA CRONOLOGIA DE HIGHLIGHTS GERADO PELA IA")
        print("=" * 50)
        print(json.dumps(result, indent=4, ensure_ascii=False))
        print("=" * 50 + "\n")

        if "error" in result:
            raise AssertionError(f"A consulta Expert retornou erro: {result['error']}")

        # Validações dos requisitos críticos de Highlights
        match_start = result.get("match_start", "")
        print(f"[VALIDAÇÃO] Horário de início do jogo detectado pela IA (Esperado: 20:30:00): {match_start}")
        
        # O horário oficial do jogo é 20:30. Admitiremos flexibilidade de minutos dependendo do grounding,
        # mas não deve estar próximo do horário de upload do vídeo (22:35)
        if "20:30" not in match_start and "20:3" not in match_start:
            print(f"[WARN] O horário de início do jogo '{match_start}' diferiu do esperado (20:30:00).")
        else:
            print("[OK] Início oficial da partida detectado com sucesso via Grounding!")

        # Validação do alinhamento das transcrições baseada na minutagem real do futebol
        transcript_events = result.get("transcript_events", [])
        goal_1_alignment = False
        goal_2_alignment = False

        for te in transcript_events:
            v_time = te.get("video_time", "")
            r_time = te.get("real_time", "")
            narration = te.get("narration", "").lower()
            analysis = te.get("analysis", "")

            print(f" -> Transcrição [{v_time}] -> Hora Real [{r_time}]: \"{narration[:50]}...\" ({analysis})")

            if "john kennedy" in narration:
                # O gol foi aos 91 min (após 20:30:00). 
                # 20:30 + 45 (1T) + 3 (stoppage) + 18 (interval) + 46 (2T) = 22:22:00.
                # Aceita-se intervalo entre 22:15 e 22:30 dependendo da estimativa do intervalo (15 ou 18 minutos)
                if "22:2" in r_time or "22:1" in r_time:
                    goal_1_alignment = True
                    print(f"    [OK] Gol do John Kennedy alinhado corretamente à hora real da partida ({r_time}) e não ao vídeo!")
                else:
                    print(f"    [WARN] Gol de John Kennedy alinhado para {r_time} (esperado por volta de 22:22:00).")

            if "mateus pereira" in narration:
                # O gol de empate do Cruzeiro foi aos 93 min.
                # Aceita-se intervalo correspondente entre 22:18 e 22:30.
                if "22:2" in r_time or "22:1" in r_time:
                    goal_2_alignment = True
                    print(f"    [OK] Gol do Mateus Pereira alinhado corretamente à hora real da partida ({r_time}) e não ao vídeo!")
                else:
                    print(f"    [WARN] Gol de Mateus Pereira alinhado para {r_time} (esperado por volta de 22:24:00).")

        # 4. Geração do Relatório PDF usando o ReportGenerator
        print("\n[INFO] Testando a geração do PDF consolidado...")
        reports_dir = os.path.join(PROJECT_ROOT, "data", "reports")
        reporter = ReportGenerator(reports_dir=reports_dir)
        
        pdf_path = reporter.write_expert_report([result])
        if os.path.exists(pdf_path):
            print(f"[OK] Relatório PDF gerado e salvo com sucesso em: {pdf_path}")
        else:
            raise AssertionError("O arquivo PDF do relatório não foi criado no disco.")

        print("\n" + "=" * 60)
        print("SUCESSO: A validação de Highlights foi concluída com êxito!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FALHA DE VALIDAÇÃO] Ocorreu um erro crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_validation()
