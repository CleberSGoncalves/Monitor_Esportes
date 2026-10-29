import re

cbf_path = r"e:\desenvolvimento\Monitor_Esportes\modules\cbf_schedule_fetcher.py"
with open(cbf_path, "r", encoding="utf-8") as f:
    text = f.read()

# Pattern to find Grêmio x Internacional 25/10/2026
pattern = r'(\s*# Rodada 32 - 25/10/2026\s*\{\s*"comp": "Brasileirão Série A",\s*"team1": "Grêmio",\s*"team2": "Internacional",\s*"score": "1 x 1",\s*"date": "25/10/2026",\s*"time": "19:30",\s*"platform": "Amazon Prime",\s*"tag": "⚡ Auditoria Concluída"\s*\}\s*\])'

new_block = '''        # Rodada 32 - 24/10/2026
        {
            "comp": "Brasileirão Série A",
            "team1": "Vasco da Gama",
            "team2": "Corinthians",
            "score": "3 x 2",
            "date": "24/10/2026",
            "time": "18:30",
            "platform": "CazéTV",
            "tag": "⚡ Auditoria Concluída"
        },
        {
            "comp": "Brasileirão Série A",
            "team1": "Chapecoense",
            "team2": "Fluminense",
            "score": "2 x 1",
            "date": "24/10/2026",
            "time": "19:30",
            "platform": "Amazon Prime",
            "tag": "⚡ Auditoria Concluída"
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
            "tag": "⚡ Auditoria Concluída"
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
            "tag": "⚡ Auditoria Concluída"
        }
    ]'''

m = re.search(pattern, text)
if m:
    text = text[:m.start()] + "\n" + new_block + text[m.end():]
    with open(cbf_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("SUCCESS: cbf_schedule_fetcher.py updated!")
else:
    print("Pattern not matched!")
