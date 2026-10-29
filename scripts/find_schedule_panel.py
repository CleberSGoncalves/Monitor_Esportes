with open("gui/main_gui.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if "FILA DE AGENDAMENTOS" in line or "_update_schedule_panel_ui" in line or "Agendamento de Fila de Auditoria" in line:
            clean = line.strip().encode("ascii", "replace").decode("ascii")
            print(f"{i+1}: {clean[:100]}")
