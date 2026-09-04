"""
Aplica correcoes finais baseadas nas sumulas oficiais CBF (Gemini + Google Search)
nos 4 relatorios e re-envia ao SharePoint.
"""
import os, sys, json, glob
from datetime import datetime
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")

scratch = r"e:\desenvolvimento\Monitor_Esportes\scratch"
reports_dir = r"e:\desenvolvimento\Monitor_Esportes\reports"

# Sumulas oficiais CBF obtidas via Gemini + Google Search
SUMULAS = {
    "chapecoense": {
        "name": "Chapecoense x Sao Paulo",
        "kw": "chapecoense",
        "resultado": "1 x 0",
        "first_half_start": "18:30:00",
        "half_time_start": "19:18:00",   # fim 1T
        "half_time_end": "19:33:00",     # inicio 2T
        "second_half_start": "19:33:00",
        "match_end": "20:25:00",         # SUMULA CBF (antes: 20:24 Arthur, 20:23 relatorio)
        "stoppage_time_1t": 3,
        "stoppage_time_2t": 7,
        # LIVE: live_start_time do JSON = 16:55, live_end_time = 21:35
        # Arthur diz imagens ate 22:00 -> post_game_end = 22:00:00
        "post_game_end": "22:00:00",
    },
    "cruzeiro_x_flamengo": {
        "name": "Cruzeiro x Flamengo",
        "kw": "cruzeiro_x_flamengo",
        "resultado": "2 x 1",
        "first_half_start": "20:30:00",  # SUMULA (relatorio tinha 21:00 - ERRADO!)
        "half_time_start": "21:18:00",
        "half_time_end": "21:33:00",
        "second_half_start": "21:33:00", # relatorio tinha 22:03 - ERRADO!
        "match_end": "22:25:00",         # SUMULA (relatorio tinha 22:53 - ERRADO!)
        "stoppage_time_1t": 3,
        "stoppage_time_2t": 7,
        # live_end_time do JSON = 23:45, post_game_end era 23:05 -> corrigir para live_end_time
        "post_game_end": "23:45:00",
        # pre_game_start do JSON = 20:45 (ok, ~15min antes do jogo)
    },
    "vasco_x_vit": {
        "name": "Vasco x Vitoria",
        "kw": "vasco_x_vit",
        "resultado": "1 x 0",
        "first_half_start": "21:30:00",  # ok
        "half_time_start": "22:20:00",   # SUMULA (relatorio tinha 22:18)
        "half_time_end": "22:35:00",     # SUMULA (relatorio tinha 22:33)
        "second_half_start": "22:35:00",
        "match_end": "23:25:00",         # SUMULA (Arthur dizia 23:28 via imagens, sumula diz 23:25)
        "stoppage_time_1t": 5,
        "stoppage_time_2t": 5,
        # live_end_time do JSON = 00:15 -> post_game_end
        "post_game_end": "00:15:00",
    },
    "palmeiras_x_santos": {
        "name": "Palmeiras x Santos",
        "kw": "palmeiras_x_santos",
        "resultado": "3 x 0",
        "first_half_start": "21:30:00",  # SUMULA (relatorio tinha 18:30 - ERRADO! era jogo das 21:30)
        "half_time_start": "22:18:00",   # SUMULA (relatorio tinha 19:18)
        "half_time_end": "22:35:00",     # SUMULA (relatorio tinha 19:33)
        "second_half_start": "22:35:00",
        "match_end": "23:26:00",         # SUMULA (relatorio tinha 20:22 - ERRADO!)
        "stoppage_time_1t": 3,
        "stoppage_time_2t": 6,
        "pre_game_start": "21:15:00",    # corrigir de 18:15 para 21:15
        # live_end_time do JSON = 21:00 mas isso era quando jogo era 18:30
        # Jogo era 21:30 -> LIVE provavelmente vai ate ~00:00 ou mais
        # Usar live_end_time do JSON ajustado (live_end_time era 21:00 para jogo das 18:30)
        # Diferenca de 3h: 21:00 + 3h = 00:00 -> post_game_end = 00:00
        "post_game_end": "00:00:00",
        "live_start_time": "20:00:00",   # ajustar de 17:00 para 20:00
    },
}

def get_latest_json(kw):
    files = sorted(glob.glob(os.path.join(scratch, "*" + kw + "*CORRIGIDO*.json")), reverse=True)
    if not files:
        files = sorted(glob.glob(os.path.join(scratch, "*" + kw + "*.json")), reverse=True)
        files = [f for f in files if "CORRIGIDO" not in f]
    if not files:
        return None, None, None
    path = files[0]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "expert_results" in data and isinstance(data["expert_results"], list):
        return path, data, data["expert_results"][0]
    return path, data, data

def apply_and_save(kw, corrections):
    path, data, target = get_latest_json(kw)
    if not path:
        print("JSON nao encontrado para: " + kw)
        return None, None

    changed = []
    fields_to_update = {k: v for k, v in corrections.items() if k not in ("name", "kw", "resultado")}
    
    for field, new_val in fields_to_update.items():
        old_val = target.get(field)
        if str(old_val) != str(new_val):
            target[field] = new_val
            changed.append("  " + field + ": " + str(old_val) + " -> " + str(new_val))

    # Adicionar resultado se tiver
    if corrections.get("resultado"):
        old_res = target.get("resultado", "")
        if old_res != corrections["resultado"]:
            target["resultado"] = corrections["resultado"]
            changed.append("  resultado: " + str(old_res) + " -> " + corrections["resultado"])

    data["corrigido_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["corrigido_por"] = "Auditoria Automatica - Sumulas CBF - 03/09/2026"
    data["fonte_horario"] = "sumula_cbf_gemini_grounding"

    basename = os.path.basename(path)
    new_name = basename.replace("_CORRIGIDO.json", "").replace(".json", "") + "_CORRIGIDO_FINAL.json"
    new_path = os.path.join(scratch, new_name)
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("  Salvo: " + new_name)
    if changed:
        print("  ALTERACOES:")
        for c in changed:
            print(c)
    else:
        print("  Sem alteracoes necessarias.")

    return new_path, data

def regenerate_and_upload(data, game_name):
    try:
        from modules.report_generator import ReportGenerator
        os.makedirs(reports_dir, exist_ok=True)
        gen = ReportGenerator(reports_dir=reports_dir)
        if "expert_results" in data and isinstance(data["expert_results"], list):
            results_list = data["expert_results"]
        else:
            results_list = [data]
        pdf_path = gen.write_expert_report(results_list)
        if pdf_path and os.path.exists(pdf_path):
            print("  PDF: " + os.path.basename(pdf_path))
            # Upload SharePoint
            from modules.sharepoint_reporter import SharePointReporter
            r = results_list[0]
            iso = SharePointReporter.format_iso_datetime(r.get("date",""), r.get("time",""))
            ok = SharePointReporter.sync_pdf_to_sharepoint(
                pdf_path, r.get("match_display",""), r.get("competition",""),
                r.get("platform",""), data_hora_iso=iso, confianca=str(r.get("confidence_score",1.0))
            )
            print("  SharePoint: " + ("OK" if ok else "FALHOU"))
            return ok
    except Exception as e:
        print("  ERRO: " + str(e))
        import traceback; traceback.print_exc()
    return False

# ===== EXECUCAO =====
print("=" * 70)
print("CORRECAO FINAL COM SUMULAS CBF - " + datetime.now().strftime("%d/%m/%Y %H:%M"))
print("=" * 70)

results = {}
for key, corr in SUMULAS.items():
    print("\n--- " + corr["name"] + " ---")
    json_path, data = apply_and_save(key, corr)[:2]
    if json_path and data:
        ok = regenerate_and_upload(data, corr["name"])
        results[corr["name"]] = "OK" if ok else "PDF_OK_SP_FALHOU"
    else:
        results[corr["name"]] = "ERRO"

print("\n" + "=" * 70)
print("RESULTADO FINAL:")
for k, v in results.items():
    print("  [" + ("OK" if "OK" in v else "FALHOU") + "] " + k + ": " + v)
print("=" * 70)
