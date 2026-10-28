import os

path = os.path.join("modules", "autonomous_auditor.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = '"plataforma": plat_field or "Amazon Prime",'
replacement = '"plataforma": plat_field or "Outro",'

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("autonomous_auditor.py atualizado com sucesso!")
else:
    print("Target não encontrado em autonomous_auditor.py")
