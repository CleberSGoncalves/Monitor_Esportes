import os

path = os.path.join("gui", "main_gui.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = 'if is_future or (is_recent and g.get("status") in ("pending", "running")):'
replacement = 'if is_future or g.get("status") in ("pending", "running"):'

assert target in content, "Target não encontrado em main_gui.py"
content = content.replace(target, replacement, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("main_gui.py ajustado: Jogos pendentes nunca mais são purgados antes de auditar!")
