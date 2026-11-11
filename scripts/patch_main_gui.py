# -*- coding: utf-8 -*-
import sys
import re

def main():
    file_path = "gui/main_gui.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Import
    t1 = """try:

    from gui.nba_events_mixin import NBAEventsMixin

except (ImportError, ModuleNotFoundError):

    from nba_events_mixin import NBAEventsMixin"""

    r1 = """try:

    from gui.nba_events_mixin import NBAEventsMixin

except (ImportError, ModuleNotFoundError):

    from nba_events_mixin import NBAEventsMixin

try:

    from gui.reporte_eventos_mixin import ReporteEventosMixin

except (ImportError, ModuleNotFoundError):

    from reporte_eventos_mixin import ReporteEventosMixin"""

    # 2. Class definition
    t2 = "class MonitorApp(MonitorCoreMixin, CanaisLiveMixin, NBAEventsMixin, ctk.CTk):"
    r2 = "class MonitorApp(MonitorCoreMixin, CanaisLiveMixin, NBAEventsMixin, ReporteEventosMixin, ctk.CTk):"

    # 3. Init call
    t3 = "        self._init_canais_live()"
    r3 = """        self._init_canais_live()
        self._init_reporte_eventos()"""

    # 4. Mode switch
    t4 = 'values=["Expert (API-Only)", "Visual (OBS)", "Ads & Merchan", "Canais Live", "🏀 Eventos NBA", "Config IA"],'
    r4 = 'values=["Expert (API-Only)", "Visual (OBS)", "Ads & Merchan", "Canais Live", "🏀 Eventos NBA", "📅 Reporte de Eventos", "Config IA"],'

    t4_w = 'width=820,'
    r4_w = 'width=980,'

    # 5. Tab creation and build
    t5 = """        self.tab_canais = self.tabs.add("📡 Canais Live")

        self.tab_nba = self.tabs.add("🏀 Eventos NBA")"""

    r5 = """        self.tab_canais = self.tabs.add("📡 Canais Live")

        self.tab_nba = self.tabs.add("🏀 Eventos NBA")

        self.tab_reporte = self.tabs.add("📅 Reporte de Eventos")"""

    t5_build = """        self._build_tab_canais_live()

        self._build_tab_nba()"""

    r5_build = """        self._build_tab_canais_live()

        self._build_tab_nba()

        self._build_tab_reporte_eventos()"""

    # 6. _on_mode_change
    t6 = """        is_nba    = (mode == "🏀 Eventos NBA")

        is_ia     = (mode == "Config IA")"""

    r6 = """        is_nba    = (mode == "🏀 Eventos NBA")

        is_reporte = (mode == "📅 Reporte de Eventos" or mode == "Reporte de Eventos")

        is_ia     = (mode == "Config IA")"""

    t6_top = "if not (is_canais or is_nba or is_ia or is_ads):"
    r6_top = "if not (is_canais or is_nba or is_ia or is_ads or is_reporte):"

    t6_tabs = 'ordered_tab_names = ["Monitoramento", "📊 Jogos Auditados", "🛡️ Auditoria", "📡 Canais Live", "🏀 Eventos NBA", "Dashboard", "Logs", "Config"]'
    r6_tabs = 'ordered_tab_names = ["Monitoramento", "📊 Jogos Auditados", "🛡️ Auditoria", "📡 Canais Live", "🏀 Eventos NBA", "📅 Reporte de Eventos", "Dashboard", "Logs", "Config"]'

    t6_select = """        elif is_nba and hasattr(self, "tabs"):

            try:

                self.tabs.set("🏀 Eventos NBA")

            except: pass"""

    r6_select = """        elif is_nba and hasattr(self, "tabs"):

            try:

                self.tabs.set("🏀 Eventos NBA")

            except: pass

        elif is_reporte and hasattr(self, "tabs"):

            try:

                self.tabs.set("📅 Reporte de Eventos")

            except: pass"""

    # 7. is_fullscreen_tab
    t7 = '["Canais Live", "Eventos NBA", "NBA", "Dashboard", "Logs", "Config", "Ads/Merchan"]'
    r7 = '["Reporte de Eventos", "Canais Live", "Eventos NBA", "NBA", "Dashboard", "Logs", "Config", "Ads/Merchan"]'

    replacements = [
        (t1, r1, "Import"),
        (t2, r2, "Class definition"),
        (t3, r3, "Init call"),
        (t4, r4, "Mode switch values"),
        (t4_w, r4_w, "Mode switch width"),
        (t5, r5, "Tab creation"),
        (t5_build, r5_build, "Tab build"),
        (t6, r6, "Mode change variable"),
        (t6_top, r6_top, "Top panel hide"),
        (t6_tabs, r6_tabs, "Ordered tab names"),
        (t6_select, r6_select, "Tab select on mode change"),
        (t7, r7, "Fullscreen tab check"),
    ]

    for target, repl, label in replacements:
        if target in content:
            content = content.replace(target, repl, 1)
            print(f"OK: {label}")
        else:
            print(f"FAILED to find: {label}")
            sys.exit(1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("ALL REPLACEMENTS APPLIED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
