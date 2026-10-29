import os
import re

main_gui_path = r"e:\desenvolvimento\Monitor_Esportes\gui\main_gui.py"
with open(main_gui_path, "r", encoding="utf-8") as f:
    text = f.read()

# Target block to replace:
# From self.btn_header_sharepoint.pack(side="left", padx=(6, 0))
# to threading.Thread(target=run_silent, daemon=True).start()

pattern = re.compile(
    r'(self\.btn_header_sharepoint\.pack\(side="left", padx=\(6, 0\)\)\s*)'
    r'(?:def _open_global_sharepoint_auth_modal.*?)(?:def _check_update_silent_startup.*?threading\.Thread\(target=run_silent, daemon=True\)\.start\(\))',
    re.DOTALL
)

m = pattern.search(text)
if m:
    print("Found target block inside _build_ui!")
    replacement = r'''\1

        # Disparar checagem automatica silenciosa na inicializacao
        def _run_silent_update_check():
            try:
                updater = AutoUpdater()
                has_update, remote_ver, download_url, changelog = updater.check_for_update()
                if has_update:
                    def highlight_ui():
                        if hasattr(self, "btn_header_update") and self.btn_header_update:
                            self.btn_header_update.configure(
                                text=f"🚀 NOVA VERSÃO DISPONÍVEL (v{remote_ver})",
                                fg_color="#FF3300",
                                hover_color="#CC0000",
                                text_color="#FFFFFF"
                            )
                        if hasattr(self, "lbl_header_version") and self.lbl_header_version:
                            self.lbl_header_version.configure(
                                text=f"v{updater.current_version} (⚠️ Desatualizado!)",
                                text_color="#FF6666"
                            )
                        self._log(f"🔔 [AUTO UPDATER] Nova versão v{remote_ver} disponível no GitHub! Clique no botão vermelho no topo para atualizar.")
                    self.after(0, highlight_ui)
            except Exception:
                pass

        threading.Thread(target=_run_silent_update_check, daemon=True).start()'''
    text = pattern.sub(replacement, text, count=1)
    
    # Now place _open_global_sharepoint_auth_modal right before _on_mode_change
    target_on_mode = "    def _on_mode_change(self, mode: str) -> None:"
    modal_method = """    def _open_global_sharepoint_auth_modal(self) -> None:
        \"\"\"Abre o modal interativo para login Microsoft Device Code no SharePoint.\"\"\"
        try:
            from gui.sharepoint_auth_modal import open_sharepoint_device_auth_modal
            open_sharepoint_device_auth_modal(self)
        except Exception as e:
            logger.error(f"[SharePoint Modal] Erro ao abrir modal: {e}")

"""
    if target_on_mode in text:
        text = text.replace(target_on_mode, modal_method + target_on_mode, 1)
        print("Inserted _open_global_sharepoint_auth_modal before _on_mode_change.")
    else:
        print("Warning: _on_mode_change not found!")

    with open(main_gui_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("SUCCESS: main_gui.py fixed!")
else:
    print("ERROR: Target block pattern not found!")
