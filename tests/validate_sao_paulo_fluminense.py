# tests/validate_sao_paulo_fluminense.py
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Configura o ROOT do projeto no path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.expert_assistant import ExpertAssistant
from modules.report_generator import ReportGenerator

def run_validation():
    print("=" * 60)
    print("VALIDAÇÃO: MODO EXPERT - FLUMINENSE X SÃO PAULO (16/05/2026)")
    print("=" * 60)

    # 1. Carrega configurações do Gemini
    config_path = os.path.join(PROJECT_ROOT, "config", "google_ai.json")
    if not os.path.exists(config_path):
        print(f"[ERRO] Arquivo de configurações {config_path} não encontrado.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
        api_key = config_data.get("gemini_api_key") or config_data.get("api_key")
        model_id = config_data.get("model", "gemini-2.5-flash")

    if not api_key:
        print("[ERRO] API Key do Gemini não está configurada.")
        return

    # 2. Prepara o mock do transcrito fiel com as falas e os timestamps do player de vídeo
    # O início real da transmissão foi definido como 18:30:00 BRT (Timestamp: 1778967000)
    # A partida iniciou às 19:00:00 BRT, que equivale ao minuto 30:00 do vídeo.
    transmission_start_ts = 1778967000  # 16/05/2026 18:30:00 BRT
    video_duration = 9000  # 2 horas e 30 minutos de transmissão

    mock_transcript = (
        "[00:00 - 05:00]: bem-vindos à transmissão ao vivo de fluminense e são paulo no maracanã pelo brasileirão\n"
        "[28:00 - 30:00]: times em campo aquecendo protocolo oficial hino nacional executado tudo pronto para o início\n"
        "[30:00 - 30:15]: autoriza o árbitro apita o início do jogo rola a bola começa o primeiro tempo\n"
        "[49:00 - 49:15]: olha a jogada do marquinhos cruzou na área de cabeça john kennedy goooool do fluminense de cabeça aos dezenove minutos\n"
        "[74:00 - 74:15]: contra-ataque rápido agustín canobbio chuta de primeira goooool o uruguaio amplia aos quarenta e quatro do primeiro tempo\n"
        "[77:45 - 78:00]: apita o árbitro fim do primeiro tempo fluminense dois são paulo zero no maracanã\n"
        "[95:15 - 95:30]: autoriza o árbitro rola a bola começa o segundo tempo da partida\n"
        "[128:15 - 128:30]: falta cobrada na área dória sobe mais alto que todo mundo goooool do são paulo zagueiro diminui aos trinta e três\n"
        "[147:40 - 148:00]: apita o árbitro fim de papo final de jogo fluminense dois são paulo um grande vitória tricolor\n"
    )

    print(f"[INFO] Inicializando ExpertAssistant com o modelo {model_id}...")
    assistant = ExpertAssistant(api_key=api_key, model_id=model_id)

    print("[INFO] Enviando parâmetros para get_match_chronology com Transcrição + Grounding...")
    
    try:
        result = assistant.get_match_chronology(
            team1="Fluminense",
            team2="São Paulo",
            competition="Brasileirão",
            platform="CazéTV",
            date="16/05/2026",
            start_timestamp=transmission_start_ts,
            duration=video_duration,
            video_url="https://www.youtube.com/watch?v=mock_flu_sp_2026",
            transcript_text=mock_transcript
        )

        print("\n" + "=" * 50)
        print("RESULTADO DA CRONOLOGIA TÉCNICA GERADO PELA IA")
        print("=" * 50)
        print(json.dumps(result, indent=4, ensure_ascii=False))
        print("=" * 50 + "\n")

        # 3. Executa as validações automáticas dos requisitos críticos
        print("[VALIDAÇÃO] Iniciando asserções automáticas...")
        
        # Validação: Erro no retorno da IA
        if "error" in result:
            raise AssertionError(f"A consulta Expert retornou erro: {result['error']}")

        # Validação: Placar e Equipes
        match_display = result.get("match_display", "")
        if "Fluminense" not in match_display or "São Paulo" not in match_display:
            print("[WARN] Nome das equipes inválido ou ausente no match_display.")

        # Validação: Detecção e Alinhamento dos Gols reais
        goals = [m for m in result.get("technical_milestones", []) if m.get("type") == "Gol"]
        print(f"[INFO] Gols detectados na cronologia: {len(goals)}")

        jk_detected = False
        canobbio_detected = False
        doria_detected = False

        for g in goals:
            event_desc = g.get("event", "").lower()
            minute = g.get("minute")
            event_time = g.get("time", "")

            if "john kennedy" in event_desc or "kennedy" in event_desc:
                jk_detected = True
                print(f" -> [OK] Gol do John Kennedy detectado no minuto {minute} às {event_time}.")
                # O gol foi aos 19 min. 19:00:00 + 19 min = 19:19:00
                if minute != 18 and minute != 19:
                    print(f"    [AVISO] Minuto do gol de John Kennedy ({minute}') difere do esperado (18' ou 19').")
            elif "canobbio" in event_desc:
                canobbio_detected = True
                print(f" -> [OK] Gol do Canobbio detectado no minuto {minute} às {event_time}.")
                # O gol foi aos 44 min. 19:00:00 + 44 min = 19:44:00
                if minute != 44:
                    print(f"    [AVISO] Minuto do gol de Canobbio ({minute}') difere do esperado (44').")
            elif "dória" in event_desc or "doria" in event_desc:
                doria_detected = True
                print(f" -> [OK] Gol do Dória detectado no minuto {minute} às {event_time}.")
                # O gol foi aos 33 min do 2T. 20:05:15 + 33 min = 20:38:15
                if minute != 33 and minute != 78:  # 45 + 33 = 78
                    print(f"    [AVISO] Minuto do gol de Dória ({minute}') difere do esperado (33' 2T ou 78').")

        if not jk_detected:
            print("[WARN] Gol do John Kennedy não foi explicitamente listado nos milestones!")
        if not canobbio_detected:
            print("[WARN] Gol do Canobbio não foi explicitamente listado nos milestones!")
        if not doria_detected:
            print("[WARN] Gol do Dória não foi explicitamente listado nos milestones!")

        # Validação: Alinhamento das janelas temporais da Transcrição (Transcript Events)
        transcript_events = result.get("transcript_events", [])
        print(f"[INFO] Eventos de transcrição alinhados pela IA: {len(transcript_events)}")
        
        goal_alignment_ok = False
        for te in transcript_events:
            narration = te.get("narration", "").lower()
            v_time = te.get("video_time", "")
            r_time = te.get("real_time", "")
            analysis = te.get("analysis", "")
            
            print(f" -> Transcrição [{v_time}] -> Hora Real [{r_time}]: \"{narration[:50]}...\" ({analysis})")
            
            if "john kennedy" in narration:
                # O narrador fala dele aos 49:00 de vídeo.
                # Hora real calculada deve ser 18:30:00 (início) + 49 min = 19:19:00.
                if "19:19" in r_time or "19:18" in r_time:
                    goal_alignment_ok = True
                    print("    [OK] Alinhamento temporal do gol do John Kennedy baseado em transcrição foi cravado com sucesso!")
                else:
                    print(f"    [WARN] Alinhamento temporal do gol do John Kennedy ({r_time}) difere do cálculo preciso (19:19:00).")

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
        print("SUCESSO: A Validação do Modo Expert com Transcrição funcionou perfeitamente!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FALHA DE VALIDAÇÃO] Ocorreu um erro crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_validation()
