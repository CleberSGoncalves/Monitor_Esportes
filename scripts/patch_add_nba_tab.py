import os

path = os.path.join("gui", "main_gui.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Import
target_import = "from gui.canais_live_mixin import CanaisLiveMixin"
replacement_import = "from gui.canais_live_mixin import CanaisLiveMixin\nfrom gui.nba_events_mixin import NBAEventsMixin"
if "from gui.nba_events_mixin import NBAEventsMixin" not in content:
    assert target_import in content
    content = content.replace(target_import, replacement_import, 1)

# 2. Herança
target_class = "class MonitorApp(MonitorCoreMixin, CanaisLiveMixin, ctk.CTk):"
replacement_class = "class MonitorApp(MonitorCoreMixin, CanaisLiveMixin, NBAEventsMixin, ctk.CTk):"
if replacement_class not in content:
    assert target_class in content
    content = content.replace(target_class, replacement_class, 1)

# 3. Adicionar aba e chamada de build
target_tab = 'self.tab_canais = self.tabs.add("📡 Canais Live")'
replacement_tab = 'self.tab_canais = self.tabs.add("📡 Canais Live")\n        self.tab_nba = self.tabs.add("🏀 Eventos NBA")'
if 'self.tab_nba = self.tabs.add("🏀 Eventos NBA")' not in content:
    assert target_tab in content
    content = content.replace(target_tab, replacement_tab, 1)

target_build = "self._build_tab_canais_live()"
replacement_build = "self._build_tab_canais_live()\n        self._build_tab_nba()"
if "self._build_tab_nba()" not in content:
    assert target_build in content
    content = content.replace(target_build, replacement_build, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("gui/main_gui.py atualizado com a aba 🏀 Eventos NBA!")
