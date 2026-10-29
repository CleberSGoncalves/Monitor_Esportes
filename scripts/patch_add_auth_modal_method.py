with open("gui/main_gui.py", "r", encoding="utf-8") as f:
    text = f.read()

target = 'self.btn_header_sharepoint.pack(side="left", padx=(6, 0))'
replacement = '''self.btn_header_sharepoint.pack(side="left", padx=(6, 0))

    def _open_global_sharepoint_auth_modal(self) -> None:
        """Abre o modal interativo para login Microsoft Device Code no SharePoint."""
        try:
            from gui.sharepoint_auth_modal import open_sharepoint_device_auth_modal
            open_sharepoint_device_auth_modal(self)
        except Exception as e:
            logger.error(f"[SharePoint Modal] Erro ao abrir modal: {e}")'''

if target in text:
    new_text = text.replace(target, replacement, 1)
    with open("gui/main_gui.py", "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Inserted _open_global_sharepoint_auth_modal method inside MonitorApp successfully!")
else:
    print("Target not found!")
