"""
scripts/audit_nba_videos.py
Audita os 50 jogos da NBA em cache: aplica a seleção ESTRITA de vídeo oficial e compara com o vídeo que
foi usado no lote anterior (lido do log). Gera config/nba_reprocess_list.json com os jogos a reprocessar:
- vídeo diferente do usado antes (o anterior não era oficial/compatível);
- nenhum vídeo oficial encontrado;
- jogos que tiveram frame sintético no lote anterior.
"""
import os, re, sys, json
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from modules.nba_service import NBA_TEAMS
from modules.nba_visual_proof_service import NBAVisualProofService

LOG = sys.argv[1]
TRI_TO_NAME = {v: k for k, v in NBA_TEAMS.items()}

# 1) Ler log do lote anterior: vídeo usado e se houve frame sintético, por jogo
prev = {}
cur_vid, cur_synth = None, False
for line in open(LOG, encoding="utf-8", errors="ignore"):
    m = re.search(r"deo resolvido: '.*' \(ID: (\w{11})", line)
    if m:
        cur_vid, cur_synth = m.group(1), False
        continue
    if "frame sint" in line:
        cur_synth = True
        continue
    m = re.search(r"expert_nba_nba_league_pass_([a-z]{3})_at_([a-z]{3})_(\d{8})\.pdf", line)
    if m:
        prev[f"{m.group(3)}_{m.group(1).upper()}{m.group(2).upper()}"] = (cur_vid, cur_synth)
# jogos feitos antes do log (verificados manualmente)
prev.setdefault("20261027_BKNBOS", ("Roz4iFs4Rto", False))
prev.setdefault("20261020_BOSDET", ("NZmml7nxVaI", False))

cache = os.path.join(ROOT, "config", "nba_cache")
files = sorted(f for f in os.listdir(cache) if f.endswith("_book.pdf"))
reprocess, ok = [], []
for f in files:
    m = re.match(r"(\d{8})_([A-Z]{3})([A-Z]{3})_book\.pdf", f)
    d, a, h = m.groups()
    key = f"{d}_{a}{h}"
    away, home = TRI_TO_NAME.get(a, a), TRI_TO_NAME.get(h, h)
    v = NBAVisualProofService.resolve_nba_video(away, home, date_clean=d)
    new_id = v["id"] if v else None
    old_id, had_synth = prev.get(key, (None, False))
    reasons = []
    if new_id is None:
        reasons.append("sem video oficial")
    elif old_id != new_id:
        reasons.append(f"video mudou ({old_id} -> {new_id})")
    if had_synth:
        reasons.append("frame sintetico no lote anterior")
    row = {"file": f, "key": key, "new_video": new_id, "old_video": old_id, "reasons": reasons}
    (reprocess if reasons else ok).append(row)
    print(("REPROCESSAR " if reasons else "ok          ") + key, new_id, reasons, flush=True)

json.dump({"reprocess": reprocess, "ok": [r["key"] for r in ok]},
          open(os.path.join(ROOT, "config", "nba_reprocess_list.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\nTOTAL {len(files)} | ok {len(ok)} | reprocessar {len(reprocess)}")
