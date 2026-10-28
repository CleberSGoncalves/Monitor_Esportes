import os

path = os.path.join("modules", "cbf_schedule_fetcher.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = '''        {
            "comp": "Brasileirão Série A",
            "team1": "Coritiba",
            "team2": "Botafogo",
            "score": "1 x 1",
            "date": "11/10/2026",
            "time": "19:30",
            "platform": "Amazon Prime",
            "tag": "⚡ Auditoria Concluída"
        }
    ]
    return finished'''

replacement = '''        {
            "comp": "Brasileirão Série A",
            "team1": "Coritiba",
            "team2": "Botafogo",
            "score": "1 x 1",
            "date": "11/10/2026",
            "time": "19:30",
            "platform": "Amazon Prime",
            "tag": "⚡ Auditoria Concluída"
        },
        # Rodada 31 - 17/10/2026
        {
            "comp": "Brasileirão Série A",
            "team1": "Botafogo",
            "team2": "Chapecoense",
            "score": "2 x 0",
            "date": "17/10/2026",
            "time": "18:00",
            "platform": "CazéTV",
            "tag": "⚡ Auditoria Concluída"
        },
        # Rodada 31 - 18/10/2026
        {
            "comp": "Brasileirão Série A",
            "team1": "Athletico-PR",
            "team2": "Palmeiras",
            "score": "0 x 2",
            "date": "18/10/2026",
            "time": "19:30",
            "platform": "Amazon Prime",
            "tag": "⚡ Auditoria Concluída"
        },
        # Rodada 32 - 24/10/2026
        {
            "comp": "Brasileirão Série A",
            "team1": "Cruzeiro",
            "team2": "Fortaleza",
            "score": "1 x 1",
            "date": "24/10/2026",
            "time": "18:30",
            "platform": "CazéTV",
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
        }
    ]

    # MIGRAÇÃO AUTOMÁTICA E DINÂMICA: Qualquer partida da tabela CBF cujo horário já passou entra imediatamente para auditoria autônoma
    try:
        now = datetime.now()
        for fix in get_real_cbf_fixtures():
            try:
                f_dt = datetime.strptime(f"{fix.get('date')} {fix.get('time')}", "%d/%m/%Y %H:%M")
                if f_dt <= now:
                    if not any(f["team1"].lower() == fix["team1"].lower() and f["team2"].lower() == fix["team2"].lower() and f["date"] == fix["date"] for f in finished):
                        finished.append({
                            "comp": fix["comp"],
                            "team1": fix["team1"],
                            "team2": fix["team2"],
                            "score": fix.get("score", "Finalizado"),
                            "date": fix["date"],
                            "time": fix["time"],
                            "platform": fix["platform"],
                            "tag": "⚡ Auditoria Concluída"
                        })
            except Exception:
                pass
    except Exception:
        pass

    return finished'''

assert target in content, "Target não encontrado em cbf_schedule_fetcher.py"
content = content.replace(target, replacement, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("cbf_schedule_fetcher.py atualizado com sucesso!")
