import sys

def main():
    path = r"gui/main_gui.py"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    old_target = """        self.btn_header_update.pack(side="left")"""

    new_target = """        self.btn_header_update.pack(side="left")

        self.btn_header_sharepoint = ctk.CTkButton(
            self.updater_header_frame,
            text="🔑 SharePoint",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=26,
            width=110,
            command=self._open_global_sharepoint_auth_modal
        )
        self.btn_header_sharepoint.pack(side="left", padx=(6, 0))"""

    if old_target in c:
        c = c.replace(old_target, new_target, 1)
        # Also add method _open_global_sharepoint_auth_modal
        method_code = """
    def _open_global_sharepoint_auth_modal(self) -> None:
        from gui.sharepoint_auth_modal import open_sharepoint_device_auth_modal
        open_sharepoint_device_auth_modal(self)
"""
        c += method_code
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        print("Successfully patched main_gui.py with global SharePoint auth button")
    else:
        print("Target not found in main_gui.py")

if __name__ == "__main__":
    main()
