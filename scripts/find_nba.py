with open(r"e:\desenvolvimento\Monitor_Esportes\gui\main_gui.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if "def " in line and "nba" in line.lower():
            print(f"{i+1}: {line.strip()}")
        elif "Monitor de Eventos NBA" in line:
            print(f"Header at {i+1}: {line.strip()}")
