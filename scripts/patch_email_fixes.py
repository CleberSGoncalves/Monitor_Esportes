import os

# 1. Patch main_gui.py
main_gui_path = r"e:\desenvolvimento\Monitor_Esportes\gui\main_gui.py"
with open(main_gui_path, "r", encoding="utf-8") as f:
    text_gui = f.read()

old_gui_remove = '''def _remove_saved_email(email_str: str) -> list:

    emails = _load_saved_emails()

    email_str = email_str.strip()

    if email_str in emails:

        emails.remove(email_str)

        _save_config_file("saved_emails.json", emails)

    return emails'''

new_gui_remove = '''def _remove_saved_email(email_str: str) -> list:

    emails = _load_saved_emails()

    email_target = email_str.strip().lower()

    emails = [e for e in emails if e.strip().lower() != email_target]

    _save_config_file("saved_emails.json", emails)

    return emails'''

if '\r\n' in text_gui:
    old_gui_remove = old_gui_remove.replace('\n', '\r\n')
    new_gui_remove = new_gui_remove.replace('\n', '\r\n')

if old_gui_remove in text_gui:
    text_gui = text_gui.replace(old_gui_remove, new_gui_remove, 1)
    with open(main_gui_path, "w", encoding="utf-8") as f:
        f.write(text_gui)
    print("main_gui.py _remove_saved_email patched successfully!")
else:
    print("main_gui.py old_gui_remove NOT found!")

# 2. Patch nba_events_mixin.py
nba_mixin_path = r"e:\desenvolvimento\Monitor_Esportes\gui\nba_events_mixin.py"
with open(nba_mixin_path, "r", encoding="utf-8") as f:
    text_nba = f.read()

old_nba_del = '''                def _make_del(del_em=em):
                    def _do_del():
                        try:
                            with open("config/saved_emails.json", "r", encoding="utf-8") as f_r:
                                cur = json.load(f_r)
                            if del_em in cur:
                                cur.remove(del_em)
                                with open("config/saved_emails.json", "w", encoding="utf-8") as f_w:
                                    json.dump(cur, f_w, indent=2)
                        except Exception:
                            pass
                        _refresh_list()
                    return _do_del'''

new_nba_del = '''                def _make_del(del_em=em):
                    def _do_del():
                        try:
                            from gui.main_gui import _remove_saved_email
                            _remove_saved_email(del_em)
                        except Exception:
                            try:
                                from main_gui import _remove_saved_email
                                _remove_saved_email(del_em)
                            except Exception:
                                pass
                        _refresh_list()
                    return _do_del'''

old_nba_add = '''        def _do_add():
            new_val = entry_new.get().strip()
            if not new_val or "@" not in new_val or "." not in new_val:
                messagebox.showwarning("E-mail Invalido", "Por favor, digite um e-mail valido.")
                return
            try:
                import json
                cur = []
                try:
                    with open("config/saved_emails.json", "r", encoding="utf-8") as f_r:
                        cur = json.load(f_r)
                except Exception:
                    cur = []
                if new_val not in cur:
                    cur.append(new_val)
                    with open("config/saved_emails.json", "w", encoding="utf-8") as f_w:
                        json.dump(cur, f_w, indent=2)
                entry_new.delete(0, "end")
                _refresh_list()
            except Exception as ex:
                messagebox.showerror("Erro", f"Erro ao adicionar e-mail: {ex}")'''

new_nba_add = '''        def _do_add():
            new_val = entry_new.get().strip()
            if not new_val or "@" not in new_val or "." not in new_val:
                messagebox.showwarning("E-mail Invalido", "Por favor, digite um e-mail valido.")
                return
            try:
                try:
                    from gui.main_gui import _save_email
                    _save_email(new_val)
                except Exception:
                    from main_gui import _save_email
                    _save_email(new_val)
                entry_new.delete(0, "end")
                _refresh_list()
            except Exception as ex:
                messagebox.showerror("Erro", f"Erro ao adicionar e-mail: {ex}")'''

if '\r\n' in text_nba:
    old_nba_del = old_nba_del.replace('\n', '\r\n')
    new_nba_del = new_nba_del.replace('\n', '\r\n')
    old_nba_add = old_nba_add.replace('\n', '\r\n')
    new_nba_add = new_nba_add.replace('\n', '\r\n')

ok_del = old_nba_del in text_nba
ok_add = old_nba_add in text_nba

if ok_del:
    text_nba = text_nba.replace(old_nba_del, new_nba_del, 1)
    print("nba_events_mixin.py _make_del patched successfully!")
else:
    print("nba_events_mixin.py old_nba_del NOT found!")

if ok_add:
    text_nba = text_nba.replace(old_nba_add, new_nba_add, 1)
    print("nba_events_mixin.py _do_add patched successfully!")
else:
    print("nba_events_mixin.py old_nba_add NOT found!")

if ok_del or ok_add:
    with open(nba_mixin_path, "w", encoding="utf-8") as f:
        f.write(text_nba)
    print("nba_events_mixin.py saved successfully!")
