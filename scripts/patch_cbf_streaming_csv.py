import os
import re

cbf_path = r"e:\desenvolvimento\Monitor_Esportes\modules\cbf_schedule_fetcher.py"
with open(cbf_path, "r", encoding="utf-8") as f:
    text = f.read()

target = 'tag": "🔥 Transmissão Exclusiva (Amazon Prime - Copa do Brasil)"\n        }\n    ]'
if target not in text:
    target = 'tag": "🔥 Transmissão Exclusiva (Amazon Prime - Copa do Brasil)"\r\n        }\r\n    ]'

replacement = '''tag": "🔥 Transmissão Exclusiva (Amazon Prime - Copa do Brasil)"
        }
    ]

    # 2. Ler e mesclar com o cronograma operacional autoritativo do Streaming_Scheduler
    try:
        import csv
        scheduler_csv = r"E:\\desenvolvimento\\Streaming_Scheduler\\data.csv"
        fallback_csv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "streaming_data.csv")
        csv_path = scheduler_csv if os.path.exists(scheduler_csv) else fallback_csv
        if os.path.exists(csv_path):
            with open(csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    partida = row.get("Partida", "").strip()
                    if not partida or " x " not in partida.lower():
                        continue
                    parts = partida.split(" x " if " x " in partida else " X ")
                    t1 = parts[0].strip()
                    t2 = parts[1].strip()
                    d_str = row.get("Data", "").strip()
                    t_str = (row.get("Horário") or row.get("Horario") or "20:00").strip()
                    plat = (row.get("Canal de Transmissão") or row.get("Canal de Transmissao") or "Amazon Prime").strip()
                    comp = row.get("Campeonato", "Brasileirão Série A").replace("CBF - ", "").strip()
                    
                    # Atualizar horário/plataforma de partida existente ou adicionar nova
                    existing = False
                    for fix in fixtures:
                        if fix["team1"].lower() == t1.lower() and fix["team2"].lower() == t2.lower() and fix["date"] == d_str:
                            fix["time"] = t_str
                            fix["platform"] = plat
                            existing = True
                            break
                    if not existing:
                        fixtures.append({
                            "comp": comp or "Brasileirão Série A",
                            "team1": t1,
                            "team2": t2,
                            "date": d_str,
                            "time": t_str,
                            "platform": plat,
                            "tag": f" Transmissão ({plat})"
                        })
    except Exception as e:
        logger.warning(f"Erro ao ler Streaming_Scheduler data.csv em get_real_cbf_fixtures: {e}")'''

if '\r\n' in text:
    replacement = replacement.replace('\n', '\r\n')

if target in text:
    text = text.replace(target, replacement, 1)
    with open(cbf_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("SUCCESS: cbf_schedule_fetcher.py patched with Streaming_Scheduler data.csv reader!")
else:
    print("Target not found!")
