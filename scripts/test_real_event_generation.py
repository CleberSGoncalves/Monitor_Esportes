import sys
import os
import json

sys.path.insert(0, ".")

from modules.live_channel_monitor import LiveNarrationService, video_info
from modules.narration_transcriber import fetch_caption_lines, transcribe_event
from modules.narration_chronology import generate_narration_chronology, _parse_json
from modules.report_generator import ReportGenerator

# Carrega credenciais do google_ai.json
with open("config/google_ai.json", "r", encoding="utf-8") as f:
    creds = json.load(f)

api_key = creds.get("gemini_api_keys") or creds.get("gemini_api_key") or creds.get("api_key")
model_id = creds.get("model") or "gemini-2.5-flash"

print(f"API Key configurada: ...{api_key[-6:]}")
print(f"Model ID: {model_id}")

# Testa com o evento do dia 24/10: Inter x Botafogo na Baldasso TV (i7QmmNSvwPs)
# ou Bagé TV (Ohnl5lJYD0w)
vid = "Ohnl5lJYD0w"  # Coritiba x Grêmio que falhou na tela do usuário
print(f"[*] Testando com vídeo: {vid}")

info = video_info(vid)
print(f"Titulo: {info.get('title', '').encode('ascii', 'ignore').decode()}")
print(f"Duracao: {info.get('duration')}s")

# Cria evento simulado
narr_dir = os.path.join(os.environ.get("APPDATA", ""), "Monitor_Esportes", "live_channels", "narracoes")
os.makedirs(narr_dir, exist_ok=True)
narr_path = os.path.join(narr_dir, f"test_narr_{vid}.txt")

event = {
    "video_id": vid,
    "title": info.get("title", "Transmissão"),
    "channel_name": "Bagé TV",
    "url": f"https://www.youtube.com/watch?v={vid}",
    "actual_start_epoch": info.get("actual_start_epoch") or 1729967580,
    "duration": info.get("duration") or 27676,
    "narration_path": narr_path
}

# Se não tem a narração ainda, obtém as legendas
if not os.path.exists(narr_path) or os.path.getsize(narr_path) == 0:
    print("[*] Baixando legendas...")
    lines, lang = fetch_caption_lines(event["url"], event["actual_start_epoch"])
    print(f"Legendas obtidas: {len(lines)} linhas (idioma: {lang})")
    with open(narr_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

meta = {
    "team1": "Coritiba",
    "team2": "Grêmio",
    "competition": "Brasileirão Série A",
    "date": "26/10/2026"
}

def safe_log(m):
    try:
        sys.stdout.buffer.write((str(m) + "\n").encode("utf-8"))
        sys.stdout.flush()
    except Exception:
        pass

print("[*] Chamando generate_narration_chronology com o novo parser...")
res = generate_narration_chronology(event, meta, api_key=api_key, model_id=model_id, log=safe_log)

if res.get("error"):
    print(f"\n[ERRO NA GERAÇÃO]: {res['error']}")
else:
    print("\n[SUCESSO ABSOLUTO] Cronologia gerada com sucesso!")
    print(f"Final Score: {res.get('final_score')}")
    print(f"Milestones detectados: {len(res.get('technical_milestones', []))}")
    print(f"Brand mentions detectadas: {len(res.get('brand_mentions', []))}")
    
    # Gera o PDF para validar até o fim
    print("[*] Gerando PDF...")
    reporter = ReportGenerator("reports")
    prefs = {"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}
    pdf = reporter.write_expert_report([res], prefs=prefs, sync_sharepoint=False, name_prefix="teste_real")
    print(f"[PDF GERADO COM SUCESSO]: {pdf}")
