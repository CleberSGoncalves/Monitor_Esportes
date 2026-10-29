def main():
    path = r"gui/main_gui.py"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    old_block = """            changed = False
            for de in default_emails:
                if de not in emails:
                    emails.append(de)
                    changed = True
            if changed:
                _save_config_file("saved_emails.json", emails)
            return emails"""

    new_block = """            return emails"""

    # Normalize whitespace/newlines for replacement
    c_norm = c.replace("\r\n", "\n")
    # Also handle if spaced out with blank lines
    import re
    pattern = r"changed = False\s+for de in default_emails:\s+if de not in emails:\s+emails\.append\(de\)\s+changed = True\s+if changed:\s+_save_config_file\(\"saved_emails\.json\", emails\)\s+return emails"
    
    if re.search(pattern, c_norm):
        c_norm = re.sub(pattern, "return emails", c_norm, count=1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(c_norm)
        print("Successfully patched _load_saved_emails in main_gui.py")
    else:
        print("Pattern not matched in main_gui.py")

if __name__ == "__main__":
    main()
