import os

file_path = "gui/main_gui.py"
with open(file_path, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

target = """        # Thread para verificar atualiza"""

# Locate check_updates block
start_str = "def check_updates():"
start_idx = content.find(start_str)
end_str = "threading.Thread(target=check_updates, daemon=True).start()"
end_idx = content.find(end_str) + len(end_str)

if start_idx != -1 and end_idx != -1:
    replacement = """def check_updates():
            try:
                has_update, remote_ver, download_url, changelog = updater.check_for_update()
                if has_update:
                    def notify_header():
                        if hasattr(self, "btn_header_update"):
                            self.btn_header_update.configure(
                                text=f"⚠️ Atualizar para v{remote_ver}", 
                                fg_color="#FF4500", 
                                hover_color="#CD3700",
                                state="normal"
                            )
                        if hasattr(self, "lbl_header_version"):
                            self.lbl_header_version.configure(text_color="#FFD700")
                    self.after(0, notify_header)
            except Exception as e_up:
                print(f"[AUTO-UPDATER WARN] Erro ao verificar atualizações: {e_up}")

        threading.Thread(target=check_updates, daemon=True).start()"""
    
    new_content = content[:start_idx] + replacement + content[end_idx:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Sucesso ao atualizar check_updates em main_gui.py!")
else:
    print(f"Não encontrado: start_idx={start_idx}, end_idx={end_idx}")
