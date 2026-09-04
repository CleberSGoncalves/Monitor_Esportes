"""
Auditor automatico: busca sumulas CBF para os 4 jogos,
compara com os relatorios e corrige todas as inconsistencias.
"""
import os, sys, json, glob, re
from datetime import datetime
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")

scratch = r"e:\desenvolvimento\Monitor_Esportes\scratch"

GAMES = [
    {"name": "Chapecoense x Sao Paulo",  "team1": "Chapecoense", "team2": "Sao Paulo",  "date": "23/08/2026", "comp": "Copa do Brasil", "kw": "chapecoense"},
    {"name": "Cruzeiro x Flamengo",      "team1": "Cruzeiro",    "team2": "Flamengo",    "date": "22/08/2026", "comp": "Copa do Brasil", "kw": "cruzeiro_x_flamengo"},
    {"name": "Vasco x Vitoria",          "team1": "Vasco",       "team2": "Vitoria",     "date": "26/08/2026", "comp": "Copa do Brasil", "kw": "vasco_x_vit"},
    {"name": "Palmeiras x Santos",       "team1": "Palmeiras",   "team2": "Santos",      "date": "26/08/2026", "comp": "Copa do Brasil", "kw": "palmeiras_x_santos"},
]

def get_corrected_json(kw):
    files = sorted(glob.glob(os.path.join(scratch, "*" + kw + "*CORRIGIDO*.json")), reverse=True)
    if not files:
        files = sorted(glob.glob(os.path.join(scratch, "*" + kw + "*.json")), reverse=True)
        files = [f for f in files if "CORRIGIDO" not in f]
    if not files:
        return None, None
    with open(files[0], encoding="utf-8") as f:
        data = json.load(f)
    if "expert_results" in data and isinstance(data["expert_results"], list):
        return files[0], data["expert_results"][0]
    return files[0], data

def fetch_sumula_via_gemini(team1, team2, date_str, comp):
    """Usa o ExpertAssistant para buscar a sumula CBF via Gemini."""
    from modules.expert_assistant import ExpertAssistant
    
    # Carregar API key do config local
    api_key = ""
    cfg_paths = [
        r"e:\desenvolvimento\Monitor_Esportes\config\google_ai.json",
        os.path.join(os.environ.get("APPDATA",""), "Monitor_Esportes", "config", "google_ai.json"),
    ]
    for cp in cfg_paths:
        if os.path.exists(cp):
            with open(cp, encoding="utf-8") as f:
                cfg = json.load(f)
            api_key = cfg.get("api_key", "")
            if api_key:
                break
    
    if not api_key:
        print("  ERRO: API key nao encontrada!")
        return None, None
    
    ea = ExpertAssistant(api_key=api_key)
    try:
        url = ea.find_sumula_url_via_gemini(team1, team2, date_str, comp)
        if url:
            from modules.cbf_schedule_fetcher import CBFScheduleFetcher
            text = CBFScheduleFetcher.fetch_sumula_text(team1, team2, date_str, sumula_url=url)
            if text:
                return text, url
    except Exception as e:
        print("  [WARN] find_sumula_url_via_gemini falhou: " + str(e))
    
    # Fallback: busca direta no CBF
    try:
        from modules.cbf_schedule_fetcher import CBFScheduleFetcher
        text = CBFScheduleFetcher.fetch_sumula_text(team1, team2, date_str)
        return text, None
    except Exception as e2:
        print("  [WARN] fetch_sumula_text fallback falhou: " + str(e2))
    return None, None

def parse_time_from_sumula(text, label_patterns):
    """Extrai horario do texto da sumula baseado em padroes."""
    if not text:
        return None
    for pattern in label_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None

def time_to_seconds(t):
    """Converte HH:MM:SS ou HH:MM em segundos."""
    if not t:
        return 0
    parts = str(t).replace("h", ":").split(":")
    try:
        h = int(parts[0]) if len(parts) > 0 else 0
        m = int(parts[1]) if len(parts) > 1 else 0
        s = int(parts[2]) if len(parts) > 2 else 0
        return h * 3600 + m * 60 + s
    except:
        return 0

def diff_minutes(t1, t2):
    """Diferenca em minutos entre dois horarios."""
    return abs(time_to_seconds(t1) - time_to_seconds(t2)) // 60

# ===== EXECUCAO =====
print("=" * 70)
print("AUDITORIA COMPLETA COM SUMULAS CBF - " + datetime.now().strftime("%d/%m/%Y %H:%M"))
print("=" * 70)

all_corrections = {}

for g in GAMES:
    print("\n" + "=" * 70)
    print("JOGO: " + g["name"] + " | " + g["date"] + " | " + g["comp"])
    print("=" * 70)
    
    # 1. Ler JSON atual
    json_path, r = get_corrected_json(g["kw"])
    if not r:
        print("  ERRO: JSON nao encontrado!")
        continue
    
    print("\nDADOS ATUAIS NO RELATORIO:")
    print("  match_start  : " + str(r.get("first_half_start", r.get("match_start", "?"))))
    print("  match_end    : " + str(r.get("match_end", "?")))
    print("  live_start   : " + str(r.get("live_start_time", r.get("pre_game_start", "?"))))
    print("  live_end     : " + str(r.get("live_end_time", r.get("post_game_end", "?"))))
    print("  pre_game     : " + str(r.get("pre_game_start", "?")))
    print("  post_game    : " + str(r.get("post_game_end", "?")))
    
    # 2. Buscar sumula CBF
    print("\nBuscando sumula CBF...")
    sumula_text, sumula_url = fetch_sumula_via_gemini(g["team1"], g["team2"], g["date"], g["comp"])
    
    if sumula_text:
        print("  Sumula obtida! (" + str(len(sumula_text)) + " chars)")
        if sumula_url:
            print("  URL: " + sumula_url)
        # Mostrar trecho relevante
        lines = [l.strip() for l in sumula_text.split("\n") if l.strip()]
        for line in lines[:30]:
            print("  | " + line)
        
        # Extrair horarios da sumula
        inicio_jogo = parse_time_from_sumula(sumula_text, [
            r"inicio.*?(\d{2}:\d{2})", r"come.o.*?(\d{2}:\d{2})",
            r"(\d{2}:\d{2}).*?inicio", r"partida.*?(\d{2}:\d{2})",
            r"1.*tempo.*?(\d{2}:\d{2})", r"primeiro.*tempo.*?(\d{2}:\d{2})"
        ])
        fim_jogo = parse_time_from_sumula(sumula_text, [
            r"fim.*?(\d{2}:\d{2})", r"encerramento.*?(\d{2}:\d{2})",
            r"apito.*?final.*?(\d{2}:\d{2})", r"termino.*?(\d{2}:\d{2})",
            r"final.*?partida.*?(\d{2}:\d{2})"
        ])
        
        print("\nHORARIOS EXTRAIDOS DA SUMULA:")
        print("  Inicio jogo (sumula): " + str(inicio_jogo))
        print("  Fim jogo (sumula)   : " + str(fim_jogo))
        
        all_corrections[g["name"]] = {
            "json_path": json_path,
            "current": r,
            "sumula_inicio": inicio_jogo,
            "sumula_fim": fim_jogo,
            "sumula_text": sumula_text[:500]
        }
    else:
        print("  AVISO: Nao foi possivel obter sumula CBF para este jogo.")
        all_corrections[g["name"]] = {
            "json_path": json_path,
            "current": r,
            "sumula_inicio": None,
            "sumula_fim": None,
            "sumula_text": None
        }

print("\n" + "=" * 70)
print("RESUMO DA AUDITORIA")
print("=" * 70)
for nome, info in all_corrections.items():
    r = info["current"]
    print("\n" + nome + ":")
    me = r.get("match_end", "?")
    sf = info["sumula_fim"]
    if sf:
        diff = diff_minutes(me, sf + ":00" if len(sf) == 5 else sf)
        flag = " <-- DIVERGENCIA de " + str(diff) + " min!" if diff > 2 else " OK"
        print("  match_end atual: " + me + " | sumula: " + sf + flag)
    else:
        print("  match_end atual: " + me + " | sumula: N/A (busca manual necessaria)")
    pe = r.get("post_game_end", "?")
    lt = r.get("live_end_time", "?")
    if pe != lt:
        print("  post_game_end: " + pe + " | live_end_time: " + lt + " <-- INCONSISTENCIA INTERNA!")
    else:
        print("  post_game_end: " + pe + " | live_end_time: " + lt + " OK")

# Salvar para uso no proximo passo
with open(os.path.join(scratch, "audit_result.json"), "w", encoding="utf-8") as f:
    safe = {k: {kk: vv for kk, vv in v.items() if kk not in ("current",)} for k, v in all_corrections.items()}
    json.dump(safe, f, ensure_ascii=False, indent=2)
print("\nResultado salvo em audit_result.json")
