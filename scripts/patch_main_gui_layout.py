with open("gui/main_gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update _on_mode_change packing of self.top and self.expert_manual_frame
target_mode = """        # 1. Barra de Pesquisa do YouTube / Canais (self.top)
        if hasattr(self, "top") and self.top:
            self.top.pack_forget()
            self.top.pack(side="bottom", fill="x", padx=12, pady=(4, 4))

        # 2. Painel de Dados da Partida para Auditoria
        if hasattr(self, "expert_manual_frame") and self.expert_manual_frame:
            self.expert_manual_frame.pack_forget()
            self.expert_manual_frame.pack(side="bottom", fill="x", padx=12, pady=(4, 4))"""

replacement_mode = """        # 1. Barra de Pesquisa do YouTube / Canais (self.top)
        if hasattr(self, "top") and self.top:
            self.top.pack_forget()
            if not (is_canais or is_nba or is_ia or is_ads):
                self.top.pack(side="bottom", fill="x", padx=12, pady=(4, 4))

        # 2. Painel de Dados da Partida para Auditoria
        if hasattr(self, "expert_manual_frame") and self.expert_manual_frame:
            self.expert_manual_frame.pack_forget()
            if not (is_canais or is_nba or is_ia or is_ads):
                self.expert_manual_frame.pack(side="bottom", fill="x", padx=12, pady=(4, 4))"""

# Normalize CRLF for matching
content_norm = content.replace("\r\n", "\n")
target_mode_norm = target_mode.replace("\r\n", "\n")
replacement_mode_norm = replacement_mode.replace("\r\n", "\n")

assert target_mode_norm in content_norm, "target_mode not found in content"
content_norm = content_norm.replace(target_mode_norm, replacement_mode_norm, 1)

# 2. Update _on_main_tab_changed
target_tab = """    def _on_main_tab_changed(self) -> None:
        \"\"\"Oculta os painéis laterais e barras legadas quando a aba '📡 Canais Live' está ativa para ampliar a área útil.\"\"\"
        if not hasattr(self, "tabs"):
            return
        try:
            active_tab = self.tabs.get()
        except Exception:
            return

        if active_tab in ["📡 Canais Live", "🏀 Eventos NBA"]:
            if hasattr(self, "left_sidebar") and self.left_sidebar and self.left_sidebar.winfo_ismapped():
                self.left_sidebar.pack_forget()
            if hasattr(self, "right_sidebar") and self.right_sidebar and self.right_sidebar.winfo_ismapped():
                self.right_sidebar.pack_forget()
            if hasattr(self, "top") and self.top and self.top.winfo_ismapped():
                self.top.pack_forget()
            if hasattr(self, "expert_manual_frame") and self.expert_manual_frame and self.expert_manual_frame.winfo_ismapped():
                self.expert_manual_frame.pack_forget()
        else:
            if hasattr(self, "left_sidebar") and self.left_sidebar and not self.left_sidebar.winfo_ismapped():
                if hasattr(self, "center_panel") and self.center_panel:
                    self.left_sidebar.pack(side="left", fill="y", padx=(12, 8), pady=12, before=self.center_panel)
                else:
                    self.left_sidebar.pack(side="left", fill="y", padx=(12, 8), pady=12)
            if hasattr(self, "right_sidebar") and self.right_sidebar and not self.right_sidebar.winfo_ismapped():
                if hasattr(self, "center_panel") and self.center_panel:
                    self.right_sidebar.pack(side="right", fill="y", padx=(8, 12), pady=12, before=self.center_panel)
                else:
                    self.right_sidebar.pack(side="right", fill="y", padx=(8, 12), pady=12)"""

replacement_tab = """    def _on_main_tab_changed(self) -> None:
        \"\"\"Oculta os painéis laterais e barras inferiores quando abas de tela cheia (NBA, Canais Live) estão ativas.\"\"\"
        if not hasattr(self, "tabs"):
            return
        try:
            active_tab = str(self.tabs.get() or "")
        except Exception:
            return

        is_fullscreen_tab = any(k in active_tab for k in ["Canais Live", "Eventos NBA", "NBA", "Dashboard", "Logs", "Config", "Ads/Merchan"])

        if is_fullscreen_tab:
            if hasattr(self, "left_sidebar") and self.left_sidebar:
                try: self.left_sidebar.pack_forget()
                except Exception: pass
            if hasattr(self, "right_sidebar") and self.right_sidebar:
                try: self.right_sidebar.pack_forget()
                except Exception: pass
            if hasattr(self, "top") and self.top:
                try: self.top.pack_forget()
                except Exception: pass
            if hasattr(self, "expert_manual_frame") and self.expert_manual_frame:
                try: self.expert_manual_frame.pack_forget()
                except Exception: pass
        else:
            if hasattr(self, "left_sidebar") and self.left_sidebar and not self.left_sidebar.winfo_ismapped():
                if hasattr(self, "center_panel") and self.center_panel:
                    self.left_sidebar.pack(side="left", fill="y", padx=(12, 8), pady=12, before=self.center_panel)
                else:
                    self.left_sidebar.pack(side="left", fill="y", padx=(12, 8), pady=12)
            if hasattr(self, "right_sidebar") and self.right_sidebar and not self.right_sidebar.winfo_ismapped():
                if hasattr(self, "center_panel") and self.center_panel:
                    self.right_sidebar.pack(side="right", fill="y", padx=(8, 12), pady=12, before=self.center_panel)
                else:
                    self.right_sidebar.pack(side="right", fill="y", padx=(8, 12), pady=12)
            if hasattr(self, "top") and self.top and not self.top.winfo_ismapped():
                self.top.pack(side="bottom", fill="x", padx=12, pady=(4, 4))
            if hasattr(self, "expert_manual_frame") and self.expert_manual_frame and not self.expert_manual_frame.winfo_ismapped():
                self.expert_manual_frame.pack(side="bottom", fill="x", padx=12, pady=(4, 4))"""

target_tab_norm = target_tab.replace("\r\n", "\n")
replacement_tab_norm = replacement_tab.replace("\r\n", "\n")

assert target_tab_norm in content_norm, "target_tab not found in content"
content_norm = content_norm.replace(target_tab_norm, replacement_tab_norm, 1)

with open("gui/main_gui.py", "w", encoding="utf-8") as f:
    f.write(content_norm.replace("\n", "\r\n"))

print("Layout patched in main_gui.py successfully!")
