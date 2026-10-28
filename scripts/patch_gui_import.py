import os

with open('gui/main_gui.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Atualizar bootstrap
old_boot = """if getattr(sys, "frozen", False):
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and meipass not in sys.path:
        sys.path.insert(0, meipass)
    exe_dir = str(Path(sys.executable).parent)
    if exe_dir not in sys.path:
        sys.path.insert(0, exe_dir)
    try:
        os.chdir(Path(sys.executable).parent)
    except Exception:
        pass
else:
    file_dir = Path(__file__).resolve().parent
    root_dir = str(file_dir.parent) if file_dir.name == "gui" else str(file_dir)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)"""

new_boot = """if getattr(sys, "frozen", False):
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        if meipass not in sys.path:
            sys.path.insert(0, meipass)
        gui_dir = os.path.join(meipass, "gui")
        if os.path.exists(gui_dir) and gui_dir not in sys.path:
            sys.path.insert(0, gui_dir)
    exe_dir = str(Path(sys.executable).parent)
    if exe_dir not in sys.path:
        sys.path.insert(0, exe_dir)
    try:
        os.chdir(Path(sys.executable).parent)
    except Exception:
        pass
else:
    file_dir = Path(__file__).resolve().parent
    root_dir = str(file_dir.parent) if file_dir.name == "gui" else str(file_dir)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    gui_dir = os.path.join(root_dir, "gui")
    if os.path.exists(gui_dir) and gui_dir not in sys.path:
        sys.path.insert(0, gui_dir)"""

# 2. Atualizar imports de mixins
old_imp = """from gui.canais_live_mixin import CanaisLiveMixin
from gui.nba_events_mixin import NBAEventsMixin"""

new_imp = """try:
    from gui.canais_live_mixin import CanaisLiveMixin
except (ImportError, ModuleNotFoundError):
    from canais_live_mixin import CanaisLiveMixin

try:
    from gui.nba_events_mixin import NBAEventsMixin
except (ImportError, ModuleNotFoundError):
    from nba_events_mixin import NBAEventsMixin"""

text = text.replace(old_boot, new_boot, 1)
text = text.replace(old_imp, new_imp, 1)

with open('gui/main_gui.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("main_gui.py atualizado com sucesso!")
