"""
Script de correcao retroativa dos 4 relatorios problematicos no SharePoint.
Aplica correcoes baseadas na analise do Arthur (03/09/2026).
"""
import os
import sys
import json
import glob
from datetime import datetime

# Adicionar o projeto ao path
project_root = r"e:\desenvolvimento\Monitor_Esportes"
sys.path.insert(0, project_root)

scratch_dir = os.path.join(project_root, "scratch")

# ============================================================
# CORRECOES BASEADAS NA ANALISE DO ARTHUR + live_end_time
# ============================================================
# Chapecoense: match_end=20:24 (sumula CBF), post_game_end=live_end_time=21:35
# Cruzeiro x Flamengo: post_game_end=live_end_time=23:45 (era 23:05, inconsistente)
# Vasco x Vitoria: match_end=23:28 (imagens Arthur), post_game_end=live_end_time=00:15
# Palmeiras x Santos: post_game_end=live_end_time=21:00 (era 20:30, inconsistente)
CORRECTIONS = {
    "chapecoense_x_sao_paulo": {
        "keyword": "chapecoense",
        "match_end": "20:24:00",    # sumula CBF confirmada pelo Arthur
        "post_game_end": "21:35:00", # live_end_time do JSON
    },
    "cruzeiro_x_flamengo": {
        "keyword": "cruzeiro_x_flamengo",
        "post_game_end": "23:45:00", # live_end_time do JSON (era 23:05)
    },
    "vasco_x_vitoria": {
        "keyword": "vasco_x_vit",
        "match_end": "23:28:00",     # Arthur confirmou via imagens
        "post_game_end": "00:15:00", # live_end_time do JSON (era 23:35)
    },
    "palmeiras_x_santos": {
        "keyword": "palmeiras_x_santos",
        "post_game_end": "21:00:00", # live_end_time do JSON (era 20:30)
    },
}

def get_latest_json(keyword):
    pattern = os.path.join(scratch_dir, "*" + keyword + "*.json")
    files = sorted(glob.glob(pattern), reverse=True)
    # Excluir arquivos ja corrigidos
    files = [f for f in files if "_CORRIGIDO" not in os.path.basename(f)]
    if not files:
        return None, None
    return files[0], os.path.basename(files[0])

def apply_corrections_and_save(keyword, corrections):
    json_path, json_name = get_latest_json(keyword)
    if not json_path:
        print("[AVISO] JSON nao encontrado para: " + keyword)
        return None, None

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    # Determinar onde aplicar as correcoes: dentro de expert_results[0] ou no nivel raiz
    if "expert_results" in data and isinstance(data["expert_results"], list) and data["expert_results"]:
        target = data["expert_results"][0]
    else:
        target = data

    changed = []
    for field, new_val in corrections.items():
        if field == "keyword":
            continue
        old_val = target.get(field)
        if old_val != new_val:
            target[field] = new_val
            changed.append("  " + field + ": " + str(old_val) + " -> " + new_val)

    # Adicionar campos de rastreabilidade no nivel raiz
    data["corrigido_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["corrigido_por"] = "Arthur Luiz - Analise 03/09/2026"
    data["fonte_horario"] = "sumula_cbf + imagens_ag"

    if changed:
        corrected_name = json_name.replace(".json", "_CORRIGIDO.json")
        corrected_path = os.path.join(scratch_dir, corrected_name)
        with open(corrected_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("[OK] JSON corrigido: " + corrected_name)
        for c in changed:
            print(c)
        return corrected_path, data
    else:
        print("[INFO] Nenhuma alteracao para: " + keyword)
        return json_path, data

def regenerate_pdf(data, game_name):
    try:
        from modules.report_generator import ReportGenerator
        output_dir = os.path.join(project_root, "reports")
        os.makedirs(output_dir, exist_ok=True)
        gen = ReportGenerator(reports_dir=output_dir)
        # write_expert_report espera uma lista de dicts com campos diretos
        # Se o JSON tem expert_results, passar essa lista; senão, passar [data]
        if "expert_results" in data and isinstance(data["expert_results"], list):
            results_list = data["expert_results"]
        else:
            results_list = [data]
        pdf_path = gen.write_expert_report(results_list)
        if pdf_path and os.path.exists(pdf_path):
            print("[OK] PDF regenerado: " + os.path.basename(pdf_path))
            return pdf_path
        else:
            print("[AVISO] PDF nao gerado para: " + game_name)
            return None
    except Exception as e:
        print("[ERRO] Falha ao regenerar PDF para " + game_name + ": " + str(e))
        import traceback
        traceback.print_exc()
        return None

def upload_to_sharepoint(pdf_path, data):
    try:
        from modules.sharepoint_reporter import SharePointReporter
        # Usar dados de expert_results[0] se disponivel
        if "expert_results" in data and isinstance(data["expert_results"], list):
            r = data["expert_results"][0]
        else:
            r = data
        match_display = r.get("match_display", "Partida")
        competition = r.get("competition", "Copa do Brasil")
        platform = r.get("platform", "")
        date_str = r.get("date", "")
        time_str = r.get("time", "21:00")
        conf = r.get("confidence_score", 1.0)

        iso_date = SharePointReporter.format_iso_datetime(date_str, time_str)
        conf_str = SharePointReporter.normalizar_confianca(conf)

        print("[SP] Enviando '" + match_display + "' para SharePoint...")
        ok = SharePointReporter.sync_pdf_to_sharepoint(
            pdf_path, match_display, competition, platform,
            data_hora_iso=iso_date, confianca=conf_str
        )
        if ok:
            print("[SP] OK - '" + match_display + "' enviado com sucesso!")
        else:
            print("[SP] FALHOU para '" + match_display + "'")
        return ok
    except Exception as e:
        print("[SP ERRO] " + str(e))
        import traceback
        traceback.print_exc()
        return False

# ============================================================
# EXECUCAO PRINCIPAL
# ============================================================
print("=" * 65)
print("CORRECAO RETROATIVA DE RELATORIOS - ANALISE ARTHUR 03/09/2026")
print("=" * 65)

final_results = {}

for game_name, corr_data in CORRECTIONS.items():
    print("\n--- Processando: " + game_name + " ---")
    keyword = corr_data["keyword"]
    corrections = {k: v for k, v in corr_data.items() if k != "keyword"}

    json_path, data = apply_corrections_and_save(keyword, corrections)
    if not json_path or not data:
        final_results[game_name] = "JSON_NAO_ENCONTRADO"
        continue

    pdf_path = regenerate_pdf(data, game_name)
    if not pdf_path:
        final_results[game_name] = "PDF_ERRO"
        continue

    ok = upload_to_sharepoint(pdf_path, data)
    final_results[game_name] = "OK_SHAREPOINT" if ok else "PDF_OK_SP_FALHOU"

print("\n" + "=" * 65)
print("RESULTADO FINAL:")
for k, v in final_results.items():
    status_icon = "OK" if "OK" in v else "FALHOU"
    print("  [" + status_icon + "] " + k + ": " + v)
print("=" * 65)
