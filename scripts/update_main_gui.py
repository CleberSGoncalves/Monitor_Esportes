import sys

with open("gui/main_gui.py", "r", encoding="utf-8") as f:
    content = f.read()

target1 = "self._on_autostop_change() # Sync inicial"
replacement1 = target1 + """

        # Inicia o Auditor Autônomo e Sincronizador de Agenda da NBA
        try:
            from modules.nba_autonomous_auditor import NBAAutonomousAuditor
            nba_auditor = NBAAutonomousAuditor.get_instance(check_interval_sec=180, log_callback=self._log)
            nba_auditor.start()
        except Exception as e:
            self._log(f"⚠️ [NBA] Não foi possível iniciar Auditor Autônomo da NBA: {e}")"""

target2 = "def _on_close(self) -> None:"
replacement2 = target2 + """
        try:
            from modules.nba_autonomous_auditor import NBAAutonomousAuditor
            NBAAutonomousAuditor.get_instance().stop()
        except Exception:
            pass"""

if target1 not in content:
    print("target1 already replaced or not found")
else:
    content = content.replace(target1, replacement1, 1)

if target2 not in content:
    print("target2 already replaced or not found")
else:
    content = content.replace(target2, replacement2, 1)

with open("gui/main_gui.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main_gui.py successfully patched!")
