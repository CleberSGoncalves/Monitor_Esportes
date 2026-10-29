import os

cbf_path = r"e:\desenvolvimento\Monitor_Esportes\modules\cbf_schedule_fetcher.py"
with open(cbf_path, "r", encoding="utf-8") as f:
    text = f.read()

target = '''        # Rodada 32 - 25/10/2026
        {
            "comp": "Brasileirão Série A",
            "team1": "Grêmio",
            "team2": "Internacional",
            "score": "1 x 1",
            "date": "25/10/2026",
            "time": "19:30",
            "platform": "Amazon Prime",
            "tag": "✅ Auditoria Concluída"
        }
    ]'''

replacement = '''        # Rodada 32 - 24/10/2026
        {
            "comp": "Brasileirão Série A",
            "team1": "Vasco da Gama",
            "team2": "Corinthians",
            "score": "3 x 2",
            "date": "24/10/2026",
            "time": "18:30",
            "platform": "CazéTV",
            "tag": "✅ Auditoria Concluída"
        },
        {
            "comp": "Brasileirão Série A",
            "team1": "Chapecoense",
            "team2": "Fluminense",
            "score": "2 x 1",
            "date": "24/10/2026",
            "time": "19:30",
            "platform": "Amazon Prime",
            "tag": "✅ Auditoria Concluída"
        },
        # Rodada 32 - 25/10/2026
        {
            "comp": "Brasileirão Série A",
            "team1": "Grêmio",
            "team2": "Internacional",
            "score": "1 x 1",
            "date": "25/10/2026",
            "time": "19:30",
            "platform": "Amazon Prime",
            "tag": "✅ Auditoria Concluída"
        },
        # Rodada 33 - 28/10/2026
        {
            "comp": "Brasileirão Série A",
            "team1": "Fluminense",
            "team2": "Internacional",
            "score": "2 x 1",
            "date": "28/10/2026",
            "time": "18:30",
            "platform": "CazéTV",
            "tag": "✅ Auditoria Concluída"
        }
    ]'''

if target in text:
    text = text.replace(target, replacement, 1)
    with open(cbf_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("cbf_schedule_fetcher.py patched with all official matches!")
else:
    print("Target block not found in cbf_schedule_fetcher.py!")
