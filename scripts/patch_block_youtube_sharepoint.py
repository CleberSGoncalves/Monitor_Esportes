import os

# 1. Patch report_generator.py
rg_path = r"e:\desenvolvimento\Monitor_Esportes\modules\report_generator.py"
with open(rg_path, "r", encoding="utf-8") as f:
    rg_text = f.read()

target_rg = 'if not partida or partida.lower() in ["partida", "none", "n/a", "sem partida"] or res0.get("error"):'
replacement_rg = '''# REGRA FUNDAMENTAL: Proibicao absoluta de envio de testes/canais YouTube para Relatorios_de_Jogos
            p_lower = partida.lower()
            plat_lower = str(res0.get("platform") or "").lower()
            name_pfx = str(name_prefix or "").lower()
            if (
                "[ocorrência]" in p_lower or "[ocorrencia]" in p_lower
                or "caso_ocorrencia" in name_pfx or "auditoria_geral" in name_pfx or "canais" in name_pfx
                or "youtube" in plat_lower or "bagé" in p_lower or "bage" in p_lower
                or ("jornada" in p_lower and ("digital" in p_lower or "super" in p_lower))
                or res0.get("report_kind") == "narration" or res0.get("channel_name")
            ):
                print(f"[SharePoint] Bloqueado upload para Relatorios_de_Jogos: evento de canal YouTube/teste ('{partida}').")
                return pdf_path

            if not partida or partida.lower() in ["partida", "none", "n/a", "sem partida"] or res0.get("error"):'''

if target_rg in rg_text:
    rg_text = rg_text.replace(target_rg, replacement_rg, 1)
    with open(rg_path, "w", encoding="utf-8") as f:
        f.write(rg_text)
    print("report_generator.py patched successfully!")
else:
    print("Could not find target_rg in report_generator.py!")

# 2. Patch live_channel_monitor.py
lcm_path = r"e:\desenvolvimento\Monitor_Esportes\modules\live_channel_monitor.py"
with open(lcm_path, "r", encoding="utf-8") as f:
    lcm_text = f.read()

# Change sync_sharepoint=True to sync_sharepoint=False in generate_case_report_for_event
old_case = 'pdf = self.reporter.write_expert_report([res_payload], prefs={"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}, sync_sharepoint=True, name_prefix="caso_ocorrencia")'
new_case = 'pdf = self.reporter.write_expert_report([res_payload], prefs={"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}, sync_sharepoint=False, name_prefix="caso_ocorrencia")'

# Change sync_sharepoint=True to sync_sharepoint=False in generate_all_cases_audit_report
old_all = 'pdf = self.reporter.write_expert_report([res_payload], prefs=prefs, sync_sharepoint=True, name_prefix="auditoria_geral_lives")'
new_all = 'pdf = self.reporter.write_expert_report([res_payload], prefs=prefs, sync_sharepoint=False, name_prefix="auditoria_geral_lives")'

if old_case in lcm_text:
    lcm_text = lcm_text.replace(old_case, new_case)
    print("generate_case_report_for_event patched (sync_sharepoint=False).")
if old_all in lcm_text:
    lcm_text = lcm_text.replace(old_all, new_all)
    print("generate_all_cases_audit_report patched (sync_sharepoint=False).")

# Change sync_event_to_sharepoint to no-op
old_sync_method = 'def sync_event_to_sharepoint(self, vid: str) -> bool:'
target_block = '''def sync_event_to_sharepoint(self, vid: str) -> bool:
        """Sincroniza manualmente o relatório PDF de um evento diretamente no SharePoint."""
        from modules.sharepoint_reporter import SharePointReporter
        ev = self.get_event(vid)
        if not ev or not ev.get("pdf_path") or not os.path.exists(ev["pdf_path"]):
            self.log(f"⚠️ PDF não encontrado para sincronização no SharePoint: {vid}")
            return False'''

replacement_block = '''def sync_event_to_sharepoint(self, vid: str) -> bool:
        """Sincronizacao de canais do YouTube para Relatorios_de_Jogos desabilitada por regra de negocio."""
        self.log(f"ℹ️ Canais Live operam em modo isolado: nao enviam relatorios para a lista de futebol do SharePoint.")
        return False'''

if target_block in lcm_text:
    lcm_text = lcm_text.replace(target_block, replacement_block, 1)
    print("sync_event_to_sharepoint disabled for soccer SharePoint.")
else:
    # Try simpler replacement
    pattern_start = 'def sync_event_to_sharepoint(self, vid: str) -> bool:'
    idx = lcm_text.find(pattern_start)
    if idx != -1:
        # find end of method (next def)
        next_def = lcm_text.find('def generate_case_report_for_event', idx)
        if next_def != -1:
            lcm_text = lcm_text[:idx] + replacement_block + "\n\n    " + lcm_text[next_def:]
            print("sync_event_to_sharepoint replaced cleanly.")

with open(lcm_path, "w", encoding="utf-8") as f:
    f.write(lcm_text)
print("live_channel_monitor.py patched successfully!")
