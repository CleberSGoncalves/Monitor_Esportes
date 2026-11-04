"""
scripts/reprocess_nba_visual.py
Regenera os relatórios NBA com a regra ESTRITA de vídeo oficial (force=True: re-extrai todos os frames)
e publica no SharePoint. Ordem: primeiro os jogos que a auditoria marcou para reprocessar
(vídeo errado / frame sintético), depois os demais. Retomável via config/nba_visual_sync_v2_done.json.

Uso: python -u scripts/reprocess_nba_visual.py
"""
import os, re, sys, json, time
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from modules.nba_service import NBAService, NBA_TEAMS
from modules.nba_report_generator import NBAReportGenerator
from modules.nba_visual_proof_service import NBAVisualProofService
from modules.sharepoint_nba_reporter import SharePointNBAReporter

TRI_TO_NAME = {v: k for k, v in NBA_TEAMS.items()}
DONE_PATH = os.path.join(ROOT, "config", "nba_visual_sync_v2_done.json")
LIST_PATH = os.path.join(ROOT, "config", "nba_reprocess_list.json")


def main():
    cache = os.path.join(ROOT, "config", "nba_cache")
    all_files = sorted(f for f in os.listdir(cache) if f.endswith("_book.pdf"))
    try:
        priority = [r["file"] for r in json.load(open(LIST_PATH, encoding="utf-8"))["reprocess"]]
    except Exception:
        priority = []
    ordered = priority + [f for f in all_files if f not in priority]

    try:
        done = set(json.load(open(DONE_PATH, encoding="utf-8")))
    except Exception:
        done = set()

    print(f"Reprocessando {len(ordered)} jogos ({len(priority)} prioritarios, {len(done)} ja concluidos)", flush=True)
    ok = fail = unavailable = 0

    for idx, f in enumerate(ordered, 1):
        if f in done:
            print(f"[{idx:2d}/{len(ordered)}] [SKIP] {f}", flush=True)
            continue
        m = re.match(r"(\d{8})_([A-Z]{3})([A-Z]{3})_book\.pdf", f)
        d, away_tri, home_tri = m.groups()
        away, home = TRI_TO_NAME.get(away_tri, away_tri), TRI_TO_NAME.get(home_tri, home_tri)
        try:
            parsed = NBAService.parse_gamebook(os.path.join(cache, f), home_tri=home_tri, date_clean=d)
            first = parsed.get("milestones", [{}])[0].get("time_brt", "19:00:00")
            game = {
                "away_team": away, "home_team": home, "away_tri": away_tri, "home_tri": home_tri,
                "match_display": f"{away} @ {home}", "date_clean": d,
                "date_display": f"{d[6:8]}/{d[4:6]}/{d[:4]}",
                "time_brt": ":".join(first.split(":")[:2]),
                "platform": "NBA League Pass", "score_display": "Finalizado", "is_finished": True,
            }
            proofs = NBAVisualProofService.generate_nba_visual_proofs(game, parsed, force=True)
            real = sum(1 for p in proofs if p.get("frame_available"))
            pdf = NBAReportGenerator.generate_report(game, parsed, visual_proofs=proofs, auto_generate_proofs=False)
            if SharePointNBAReporter.sync_nba_report(pdf, game):
                ok += 1
                unavailable += (len(proofs) - real)
                done.add(f)
                json.dump(sorted(done), open(DONE_PATH, "w", encoding="utf-8"))
                print(f"[{idx:2d}/{len(ordered)}] [OK] {away_tri}@{home_tri} {d} | frames reais {real}/{len(proofs)} | {os.path.getsize(pdf)//1024} KB", flush=True)
            else:
                fail += 1
                print(f"[{idx:2d}/{len(ordered)}] [ERRO] upload {away_tri}@{home_tri} {d}", flush=True)
        except Exception as e:
            fail += 1
            print(f"[{idx:2d}/{len(ordered)}] [EXCECAO] {away_tri}@{home_tri} {d}: {e}", flush=True)
        time.sleep(3)

    print(f"\nConcluido: {ok} enviados, {fail} falhas, {unavailable} etapas sem frame real.", flush=True)


if __name__ == "__main__":
    main()
