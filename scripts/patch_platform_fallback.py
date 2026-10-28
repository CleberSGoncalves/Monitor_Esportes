import os

path = os.path.join("modules", "report_generator.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = 'plat = str(res0.get("platform") or "Amazon Prime").strip()'
replacement = 'plat = str(res0.get("platform") or "Outro").strip()'

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("report_generator.py atualizado com sucesso!")
else:
    print("Aviso: target não encontrado em report_generator.py (talvez já alterado)")
