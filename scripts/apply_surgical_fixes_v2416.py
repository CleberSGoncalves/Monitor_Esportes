# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def patch_narration_chronology():
    p = Path("modules/narration_chronology.py")
    content = p.read_text(encoding="utf-8")

    # 1. Add strict non-match pattern detection
    non_match_code = '''
NON_MATCH_PATTERNS = [
    r"\\b(debate|elei[çc][õo]es?|lula|bolsonaro|sabatina|governador|prefeito|senado)\\b",
    r"\\b(night\\s*show|resenha|bate[- ]bola|radar\\s*de\\s*bagre|bom\\s*dia|boa\\s*noite)\\b",
    r"\\b(resenha\\s*fora\\s*da\\s*sala|mesa\\s*redonda|coletiva|entrevista\\s*coletiva)\\b",
    r"\\b(p[óo]s[- ]jogo|pre[- ]jogo|pr[ée][- ]jogo|bastidores|treino|boletim|not[íi]cias?)\\b",
    r"\\b(react|opini[ãa]o|coment[áa]rios?|pos\\s*jogo|pre\\s*jogo|an[áa]lise)\\b",
]

def is_definitely_non_match(title: str, text: str = "") -> tuple[bool, str]:
    \"\"\"Identifica cirurgicamente se o título ou conteúdo NÃO é uma partida narrada ao vivo.\"\"\"
    t_lower = (title or "").lower()
    for pat in NON_MATCH_PATTERNS:
        m = re.search(pat, t_lower, re.IGNORECASE)
        if m:
            matched = m.group(0).upper()
            return True, f"Identificado como programa/debate/conteúdo não-jogo ({matched})"
    return False, ""
'''

    if "NON_MATCH_PATTERNS =" not in content:
        content = content.replace("MAX_NARRATION_CHARS = 600_000", "MAX_NARRATION_CHARS = 600_000\n" + non_match_code)
        print("[+] Added NON_MATCH_PATTERNS and is_definitely_non_match!")

    # 2. Update guess_match_from_title to abort on non-match
    old_guess = """def guess_match_from_title(title: str) -> Dict[str, str]:
    \"\"\"Extrai 'Time A x Time B' e competição de títulos como 'AO VIVO: ATHLETICO X VASCO | BRASILEIRÃO 2026'.\"\"\""""

    new_guess = """def guess_match_from_title(title: str) -> Dict[str, str]:
    \"\"\"Extrai 'Time A x Time B' e competição de títulos como 'AO VIVO: ATHLETICO X VASCO | BRASILEIRÃO 2026'.\"\"\"
    is_non, _ = is_definitely_non_match(title)
    if is_non:
        return {"team1": "", "team2": "", "competition": ""}"""

    if old_guess in content:
        content = content.replace(old_guess, new_guess)
        print("[+] guess_match_from_title updated with non-match guard!")

    # 3. Update analyze_narration_transcript with surgical prompt and safe fallback
    old_fallback_pattern = r"except Exception as ex:\s*log\(f\"[^\"]*Falha na análise inteligente[^\"]*\"\)\s*# Fallback por título caso a API oscile.*?brand_mentions\": \[\],\s*\}"
    new_fallback = """except Exception as ex:
        log(f"⚠️ Falha na análise inteligente da transcrição: {ex}")
        # FALLBACK 100% SEGURO: NUNCA presuma que é partida em caso de erro!
        return {
            "ok": True,
            "is_match_narration": False,
            "event_category": "Pendente de Classificação (Erro de API)",
            "classification_summary": f"Falha na consulta ao Gemini ({ex}). Não classificado como jogo para evitar falsos positivos.",
            "team1": "",
            "team2": "",
            "competition": "",
            "date": live_date,
            "detected_score": "",
            "narrator_info": "",
            "brands_summary": "",
            "brand_mentions": [],
        }"""

    new_content, count = re.subn(old_fallback_pattern, new_fallback, content, count=1, flags=re.DOTALL)
    if count:
        content = new_content
        print("[+] analyze_narration_transcript safe fallback implemented!")

    # 4. Add pre-check inside analyze_narration_transcript before calling Gemini
    pre_check_needle = "log(\"?? Analisando transcri"
    # Search with regex
    pat_pre = r"(log\(\"[^\"]*Analisando transcri[^\"]*\"\))"
    repl_pre = """is_non, reason = is_definitely_non_match(event.get("title", ""))
    if is_non:
        log(f"🚫 [Classificação Cirúrgica] Evento descartado de partida ao vivo por formato: {reason}")
        return {
            "ok": True,
            "is_match_narration": False,
            "event_category": "Programa / Debate / Noticiário",
            "classification_summary": f"Descartado como partida ao vivo: {reason}.",
            "team1": "",
            "team2": "",
            "competition": "",
            "date": live_date,
            "detected_score": "",
            "narrator_info": "",
            "brands_summary": "",
            "brand_mentions": [],
        }
    \\1"""

    new_content, count = re.subn(pat_pre, repl_pre, content, count=1)
    if count:
        content = new_content
        print("[+] Added pre-check for non-match before calling Gemini!")

    p.write_text(content, encoding="utf-8")
    print("[+] narration_chronology.py patched!")

def patch_live_channel_monitor():
    p = Path("modules/live_channel_monitor.py")
    content = p.read_text(encoding="utf-8")

    # Add generate_posterior_match_report_async
    if "def generate_posterior_match_report_async" not in content:
        posterior_method = """
    def generate_posterior_match_report_async(self, vid: str, meta: Optional[Dict[str, str]] = None,
                                              progress_cb: Optional[Callable[[str], None]] = None,
                                              done_cb: Optional[Callable[[Dict[str, Any]], None]] = None) -> bool:
        \"\"\"Gera o relatório cronológico de partida para um evento já encerrado (posterior ao evento),
        transcrevendo o áudio se necessário e gerando o relatório oficial com SharePoint e E-mail.\"\"\"
        def _job():
            try:
                ev = self.get_event(vid)
                if not ev:
                    if done_cb: done_cb({"error": "Evento não encontrado na base de dados."})
                    return

                narr_path = ev.get("narration_path")
                if not narr_path or not os.path.exists(narr_path):
                    self.log(f"🎙️ [Posterior] Transcrevendo áudio do evento encerrado: {ev.get('title')[:45]}...")
                    if progress_cb: progress_cb("Extraindo áudio completo e gerando transcrição...")
                    cfg = self.config_provider() or {}
                    fname = f"narracao_{_safe(ev.get('channel_name'), 25)}_{_safe(ev.get('title'), 50)}_{vid}.txt"
                    out_path = os.path.join(self.narr_dir, fname)
                    from modules.narration_transcriber import transcribe_event
                    res = transcribe_event(ev, out_path, api_key=cfg.get("api_key"), model_id=cfg.get("model_id") or "gemini-2.5-flash",
                                           allow_audio=True, log=progress_cb or self.log)
                    if not res.get("ok"):
                        err = res.get("error", "Falha na transcrição de áudio.")
                        self.update_event(vid, error=err, pipeline="failed")
                        if done_cb: done_cb({"error": err})
                        return
                    self.update_event(vid, narration_path=res["path"], narration_lines=res.get("lines", 0),
                                      transcript_source="audio_gemini", transcript_source_label="Áudio transcrito (Sob Demanda)",
                                      pipeline="ready_match", is_match_narration=True, error="")

                final_meta = meta or self.default_meta(ev)
                self.log(f"📊 [Posterior] Gerando cronologia de jogo para {final_meta.get('team1', '')} x {final_meta.get('team2', '')}...")
                if progress_cb: progress_cb(f"Gerando cronologia oficial de {final_meta.get('team1', '')} x {final_meta.get('team2', '')}...")
                res_gen = self._generate_locked(vid, meta=final_meta, auto=False, progress_cb=progress_cb)
                if done_cb:
                    done_cb(res_gen)
            except Exception as ex:
                self.log(f"⚠️ [Posterior] Erro ao gerar relatório posterior: {ex}")
                if done_cb: done_cb({"error": str(ex)})

        threading.Thread(target=_job, daemon=True).start()
        return True
"""
        content = content.replace("    def _generate_locked", posterior_method + "\n    def _generate_locked")
        print("[+] Added generate_posterior_match_report_async to live_channel_monitor.py!")

    p.write_text(content, encoding="utf-8")

def patch_autonomous_auditor():
    p = Path("modules/autonomous_auditor.py")
    content = p.read_text(encoding="utf-8")

    old_init = """    def __init__(
        self,
        email_recipients: Optional[List[str]] = None,
        reports_dir: Optional[str] = None,
        status_callback: Optional[Callable[[str], None]] = None
    ):
        self.email_recipients = email_recipients or ["cleber.goncalves@gmail.com", "cleber.goncalves@ibope.com"]"""

    new_init = """    def __init__(
        self,
        email_recipients: Optional[List[str]] = None,
        reports_dir: Optional[str] = None,
        status_callback: Optional[Callable[[str], None]] = None
    ):
        if not email_recipients:
            for conf_p in (
                os.path.join(os.environ.get("APPDATA", ""), "Monitor_Esportes", "config", "saved_emails.json"),
                os.path.join(PROJECT_ROOT, "config", "saved_emails.json")
            ):
                if os.path.exists(conf_p):
                    try:
                        with open(conf_p, "r", encoding="utf-8") as f_em:
                            email_recipients = json.load(f_em)
                            if email_recipients:
                                break
                    except Exception:
                        pass
        self.email_recipients = email_recipients or ["cleber.goncalves@ibope.com", "arthur@mediadna.com.br"]"""

    if old_init in content:
        content = content.replace(old_init, new_init)
        p.write_text(content, encoding="utf-8")
        print("[+] autonomous_auditor.py patched with saved_emails.json auto-loading!")

def patch_main_gui_scheduler():
    p = Path("gui/main_gui.py")
    content = p.read_text(encoding="utf-8")

    # In check_sumula_thread: do not permanently fail on sumula delay; fallback to Gemini Grounding!
    old_attempt_check = """                                          elif passed_tolerance and attempts >= 2:
                                              _game["status"] = "failed"
                                              self._log(f"📋 [AGENDAMENTO AVISO] Súmula da CBF para {_game.get('team1')} x {_game.get('team2')} não encontrada após múltiplas tentativas. Auditoria suspensa para não travar a fila.")
                                              _save_scheduled_games(getattr(self, "_scheduled_games", []))
                                              self.after(0, self._update_schedule_panel_ui)"""

    new_attempt_check = """                                          elif passed_tolerance:
                                              _game["_sumula_attempts"] = attempts + 1
                                              self._log(f"📋 [AGENDAMENTO] Súmula da CBF ainda não postada no site. Ativando auditoria autônoma via Web/Gemini Grounding para {_game.get('team1')} x {_game.get('team2')}...")
                                              self.after(0, lambda: self._trigger_scheduled_audit(_game))"""

    if old_attempt_check in content:
        content = content.replace(old_attempt_check, new_attempt_check)
        p.write_text(content, encoding="utf-8")
        print("[+] main_gui.py check_sumula_thread patched to never permanently fail on CBF sumula delays!")

if __name__ == "__main__":
    patch_narration_chronology()
    patch_live_channel_monitor()
    patch_autonomous_auditor()
    patch_main_gui_scheduler()
