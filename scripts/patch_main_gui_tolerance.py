# -*- coding: utf-8 -*-
from pathlib import Path
import re

p = Path("gui/main_gui.py")
content = p.read_text(encoding="utf-8")

pattern = r'elif passed_tolerance and attempts >= 2:\s*_game\["status"\] = "failed"\s*self\._log\(f"[^"]*não encontrada após múltiplas tentativas[^"]*"\)\s*_save_scheduled_games\(getattr\(self, "_scheduled_games", \[\]\)\)\s*self\.after\(0, self\._update_schedule_panel_ui\)'

replacement = '''elif passed_tolerance:
                                              _game["_sumula_attempts"] = attempts + 1
                                              self._log(f"📋 [AGENDAMENTO] Súmula da CBF ainda não disponível. Ativando auditoria autônoma via Web/Gemini Grounding para {_game.get('team1')} x {_game.get('team2')}...")
                                              self.after(0, lambda: self._trigger_scheduled_audit(_game))'''

new_content, count = re.subn(pattern, replacement, content, count=1)
if count:
    p.write_text(new_content, encoding="utf-8")
    print("SUCCESS: main_gui.py check_sumula_thread patched!")
else:
    print("WARNING: Pattern not matched in main_gui.py")
