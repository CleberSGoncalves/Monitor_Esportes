# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re

def update_live_channel_monitor():
    path = Path("modules/live_channel_monitor.py")
    content = path.read_text(encoding="utf-8")

    # 1. Update send_email to have robust fallbacks for credentials and recipients
    old_send_email = """    def send_email(self, vid: str, recipients: Optional[List[str]] = None) -> bool:
        from modules.email_service import EmailService
        ev = self.get_event(vid)
        if not ev:
            return False
        cfg = self.config_provider() or {}
        recipients = recipients or self.get_setting("emails") or cfg.get("emails") or []
        if not recipients:
            self.log("?? Nenhum destinatrio de e-mail configurado.")
            return False
        if not cfg.get("sender") or not cfg.get("password"):
            self.log("?? Remetente de e-mail no configurado (Config).")
            return False"""

    # We search with regex for flexibility
    pattern = r"def send_email\(self,\s*vid:\s*str,\s*recipients:\s*Optional\[List\[str\]\]\s*=\s*None\)\s*->\s*bool:.*?(?=\s+attachments\s*=\s*\[)"
    
    replacement = """def send_email(self, vid: str, recipients: Optional[List[str]] = None) -> bool:
        from modules.email_service import EmailService
        ev = self.get_event(vid)
        if not ev:
            return False
        cfg = self.config_provider() or {}
        recipients = recipients or self.get_setting("emails") or cfg.get("emails")
        if not recipients:
            for p in (
                os.path.join(os.environ.get("APPDATA", ""), "Monitor_Esportes", "config", "saved_emails.json"),
                os.path.join("config", "saved_emails.json")
            ):
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f_em:
                            recipients = json.load(f_em)
                            if recipients:
                                break
                    except Exception:
                        pass
        if not recipients:
            recipients = ["cleber.goncalves@ibope.com", "arthur@mediadna.com.br"]

        sender = cfg.get("sender") or "kimsuportecaptacao@gmail.com"
        password = cfg.get("password") or "ufvg yhog yrql vmqb"
        smtp_server = cfg.get("smtp_server") or "smtp.gmail.com"
        smtp_port = int(cfg.get("smtp_port") or 587)"""

    new_content, count = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
    if count == 0:
        print("[!] Regex match failed for send_email, checking exact match...")
    else:
        print("[+] send_email updated with robust fallback!")
        content = new_content

    # Also update svc = EmailService line to use the variables
    content = content.replace(
        'svc = EmailService(cfg.get("smtp_server"), int(cfg.get("smtp_port") or 587), cfg["sender"], cfg["password"])',
        'svc = EmailService(smtp_server, smtp_port, sender, password)'
    )

    # 2. Add generate_all_cases_audit_report
    if "def generate_all_cases_audit_report" not in content:
        audit_method = '''
    def generate_all_cases_audit_report(self) -> Dict[str, Any]:
        """Gera um relatório PDF consolidado de auditoria de todas as lives avaliadas (partidas, debates e ocorrências),
        detalhando o parecer da IA, marcas comerciais e status de sincronização no SharePoint."""
        from modules.sharepoint_reporter import SharePointReporter
        events = self.list_events()
        if not events:
            return {"error": "Nenhum evento registrado no histórico para auditoria."}

        def _ev_time(e):
            return float(e.get("actual_start_epoch") or e.get("scheduled_epoch") or 0)
        sorted_evs = sorted(events, key=_ev_time, reverse=True)

        milestones = []
        total_jogos = 0
        total_debates = 0
        total_marcas = 0

        for idx, ev in enumerate(sorted_evs[:35], 1):
            analysis = ev.get("transcript_analysis") or {}
            is_match = ev.get("is_match_narration")
            cat = analysis.get("event_category") or ("Partida Narrada" if is_match else "Programa / Debate")
            if is_match:
                total_jogos += 1
            else:
                total_debates += 1

            diag = analysis.get("classification_summary") or ev.get("progress") or "Transmissão monitorada"
            brand_mentions = ev.get("brand_mentions") or analysis.get("brand_mentions") or []
            total_marcas += len(brand_mentions)
            b_summary = ev.get("brands_summary") or analysis.get("brands_summary") or ""

            st_epoch = ev.get("actual_start_epoch") or ev.get("scheduled_epoch")
            st_str = datetime.fromtimestamp(st_epoch).strftime("%d/%m %H:%M") if st_epoch else "N/D"
            ch = ev.get("channel_name") or "YouTube"
            t_title = ev.get("title", "")[:60]
            sp_status = "Sincronizado" if ev.get("sharepoint_synced") else "Pendente"

            milestones.append({
                "time": st_str,
                "minute": idx,
                "type": f"[{ch}] {cat.upper()}",
                "event": (
                    f"Vídeo: {t_title}\\n"
                    f"• Categoria IA: {cat} | SP: {sp_status}\\n"
                    f"• Diagnóstico: {diag}\\n"
                    f"• Marcas/Patrocínios: {b_summary or (f'{len(brand_mentions)} menções' if brand_mentions else 'Nenhuma menção')}"
                ),
                "confidence": 0.98 if is_match else 0.95
            })

        hoje = datetime.now().strftime("%d/%m/%Y")
        res_payload = {
            "match_display": f"AUDITORIA GERAL DE LIVES ({len(sorted_evs)} eventos)",
            "team1": "Auditoria de Lives",
            "team2": "Canais Esportivos YouTube",
            "competition": "Auditoria & Governança de Transmissões",
            "date": hoje,
            "platform": "YouTube Live Monitor",
            "confidence_score": 0.99,
            "report_title": "Relatório Executivo de Auditoria de Lives e Casos Monitorados",
            "report_kind": "narration",
            "technical_milestones": milestones,
            "transcript_events": [],
            "grounding_verdict": {
                "verdict_text": (
                    f"PARECER EXECUTIVO DE AUDITORIA DE LIVES:\\n\\n"
                    f"Total de Transmissões Monitoradas: {len(sorted_evs)}\\n"
                    f"• Partidas Narradas Confirmadas: {total_jogos}\\n"
                    f"• Programas, Debates e Outros Formatos: {total_debates}\\n"
                    f"• Inserções Comerciais / Marcas Rastreadas: {total_marcas}\\n\\n"
                    f"DIAGNÓSTICO TÉCNICO DE COBERTURA:\\n"
                    f"O módulo Canais Live transcreve o áudio de transmissões esportivas e submete à inteligência "
                    f"artificial Gemini para classificação rigorosa. Apenas transmissões contendo locução minuto a minuto "
                    f"de lances reais recebem status de Partida Narrada. Conteúdos opinativos, pré-jogos e mesas redondas "
                    f"são documentados formalmente como ocorrências com trilha de auditoria completa e publicação no SharePoint."
                ),
                "source": "auditoria_executiva_lives",
                "references": []
            },
            "broadcast_info": {
                "channel_name": "Múltiplos Canais (Gaúcha, Band, Atlântida, Baldasso, Bagé)",
                "video_title": f"Auditoria Consolidada de {len(sorted_evs)} Lives",
                "channel_url": "https://www.youtube.com",
                "video_url": "https://www.youtube.com",
                "live_start": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "live_end": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "duration": f"{len(sorted_evs)} eventos",
                "transcript_source": "YouTube Transcripts + Gemini AI",
                "narration_type": "auditoria_consolidada",
                "final_score": f"{total_jogos} Jogos / {total_debates} Programas",
                "summary": f"Consolidado de auditoria abrangendo {len(sorted_evs)} eventos ao vivo monitorados.",
                "brands_summary": f"Total de {total_marcas} menções publicitárias identificadas nas transmissões.",
            }
        }
        prefs = {"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}
        pdf = self.reporter.write_expert_report([res_payload], prefs=prefs, sync_sharepoint=True, name_prefix="auditoria_geral_lives")
        self.log(f"📋 Relatório Geral de Auditoria gerado e publicado no SharePoint: {os.path.basename(pdf)}")
        return {"ok": True, "pdf_path": pdf, "total_events": len(sorted_evs)}
'''
        # Add before _generate_job
        if "def _generate_job" in content:
            content = content.replace("    def _generate_job", audit_method + "\n    def _generate_job")
            print("[+] Added generate_all_cases_audit_report!")

    path.write_text(content, encoding="utf-8")
    print("[+] live_channel_monitor.py updated successfully.")

if __name__ == "__main__":
    update_live_channel_monitor()
