import os
import json

appdata_config = os.path.expandvars(r"%APPDATA%\Monitor_Esportes\config")
os.makedirs(appdata_config, exist_ok=True)

# 1. Copiar google_ai.json para APPDATA se não existir
src_ai = r"E:\desenvolvimento\Monitor_Esportes\config\google_ai.json"
dst_ai = os.path.join(appdata_config, "google_ai.json")
if os.path.exists(src_ai):
    with open(src_ai, "r", encoding="utf-8") as f:
        ai_data = json.load(f)
    with open(dst_ai, "w", encoding="utf-8") as f:
        json.dump(ai_data, f, indent=2, ensure_ascii=False)
    print("google_ai.json copiado para APPDATA com sucesso.")

# 2. Atualizar saved_emails.json em ambos os locais
emails = ["cleber.goncalves@ibope.com", "arthur@mediadna.com.br"]
for p in [r"E:\desenvolvimento\Monitor_Esportes\config\saved_emails.json", os.path.join(appdata_config, "saved_emails.json")]:
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(emails, f, indent=2, ensure_ascii=False)
        print(f"saved_emails.json atualizado em: {p}")
    except Exception as ex:
        print(f"Erro ao salvar {p}: {ex}")

# 3. Corrigir gui/main_gui.py
with open("gui/main_gui.py", "r", encoding="utf-8") as f:
    code = f.read()

target = """def _load_saved_emails() -> list:
    path = _get_config_read_path("saved_emails.json")
    default_emails = ["cleber.goncalves@ibope.com"]
    if not os.path.exists(path):
        _save_config_file("saved_emails.json", default_emails)
        return default_emails
    try:
        with open(path, "r", encoding="utf-8") as f:
            emails = json.load(f)
            if "arthur@mediadna.com.br" in emails:
                emails.remove("arthur@mediadna.com.br")
                _save_config_file("saved_emails.json", emails)
            return emails
    except:
        return default_emails"""

replacement = """def _load_saved_emails() -> list:
    path = _get_config_read_path("saved_emails.json")
    default_emails = ["cleber.goncalves@ibope.com", "arthur@mediadna.com.br"]
    if not os.path.exists(path):
        _save_config_file("saved_emails.json", default_emails)
        return default_emails
    try:
        with open(path, "r", encoding="utf-8") as f:
            emails = json.load(f)
            if not isinstance(emails, list):
                emails = default_emails
            changed = False
            for de in default_emails:
                if de not in emails:
                    emails.append(de)
                    changed = True
            if changed:
                _save_config_file("saved_emails.json", emails)
            return emails
    except Exception:
        return default_emails"""

crlf = "\r\n" in code
code_norm = code.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")
replacement_norm = replacement.replace("\r\n", "\n")

if target_norm in code_norm:
    new_code = code_norm.replace(target_norm, replacement_norm)
    if crlf:
        new_code = new_code.replace("\n", "\r\n")
    with open("gui/main_gui.py", "w", encoding="utf-8") as f:
        f.write(new_code)
    print("gui/main_gui.py corrigido com sucesso!")
else:
    print("Target não encontrado em main_gui.py.")
