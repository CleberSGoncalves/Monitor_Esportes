import os

path = os.path.join("modules", "live_channel_monitor.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = '''        attachments = []
        narr_path = ev.get("narration_path")
        large_narr_omitted = False
        if narr_path and os.path.exists(narr_path):
            try:
                sz = os.path.getsize(narr_path)
                # Se a narração tiver menos de 10 MB, anexa normalmente
                if sz <= 10 * 1024 * 1024:
                    attachments.append(narr_path)
                else:
                    large_narr_omitted = True
            except Exception:
                pass'''

replacement = '''        attachments = []
        # Para garantir entrega imediata e evitar recusas do servidor SMTP por volume de socket,
        # anexamos estritamente o Relatório Oficial em PDF de alta resolução.'''

if target in content:
    content = content.replace(target, replacement, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("live_channel_monitor.py ajustado com sucesso!")
else:
    print("Target não encontrado em live_channel_monitor.py")
