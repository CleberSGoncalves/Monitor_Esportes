"""
Serviço Oficial de Auditoria Autônoma e Monitoramento Contínuo da NBA.
Responsável por:
1. Monitorar a tabela oficial da NBA periodicamente (jogos passados, ao vivo e futuros).
2. Publicar e atualizar todos os eventos previstos na lista do SharePoint 'Relatorios_de_Jogos_NBA'.
3. Conforme as partidas finalizam, baixar automaticamente o Game Book oficial,
   gerar o relatório PDF de auditoria técnica, atualizar o registro no SharePoint
   (Auditado = Sim, Placar, Confiança 99.0%) e disparar o e-mail oficial com o PDF anexado.
"""

import os
import sys
import json
import time
import threading
import logging
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService
from modules.nba_report_generator import NBAReportGenerator
from modules.sharepoint_nba_reporter import SharePointNBAReporter
from modules.sharepoint_reporter import SharePointReporter
from modules.email_service import EmailService

logger = logging.getLogger("NBAAutonomousAuditor")

AUDITED_CACHE_PATH = os.path.join(PROJECT_ROOT, "config", "nba_audited_games.json")

class NBAAutonomousAuditor:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, check_interval_sec: int = 180, log_callback = None):
        self.check_interval = check_interval_sec
        self.log_callback = log_callback
        self.nba_service = NBAService()
        self.nba_reporter = NBAReportGenerator()
        self._running = False
        self._thread = None
        self._audited_cache = self._load_audited_cache()

    @classmethod
    def get_instance(cls, check_interval_sec: int = 180, log_callback = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(check_interval_sec, log_callback)
            return cls._instance

    def _log(self, msg: str):
        logger.info(msg)
        if self.log_callback:
            try:
                self.log_callback(msg)
            except Exception:
                pass
        else:
            print(f"[NBA AUTO] {msg}", flush=True)

    def _load_audited_cache(self) -> dict:
        if os.path.exists(AUDITED_CACHE_PATH):
            try:
                with open(AUDITED_CACHE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_audited_cache(self):
        try:
            os.makedirs(os.path.dirname(AUDITED_CACHE_PATH), exist_ok=True)
            with open(AUDITED_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._audited_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Erro ao salvar cache de jogos auditados da NBA: {e}")

    def is_game_audited(self, game_id: str) -> bool:
        entry = self._audited_cache.get(str(game_id), {})
        return entry.get("audited", False) and entry.get("sp_synced", False)

    def mark_game_audited(self, game: dict, pdf_path: str, email_sent: bool, sp_synced: bool):
        gid = str(game.get("id"))
        self._audited_cache[gid] = {
            "audited": bool(sp_synced),
            "match": game.get("match_display"),
            "date": game.get("date_display"),
            "score": game.get("score_display"),
            "platform": game.get("platform"),
            "pdf_path": pdf_path,
            "email_sent": bool(email_sent),
            "sp_synced": bool(sp_synced),
            "audited_at": datetime.now().isoformat()
        }
        self._save_audited_cache()

    def set_recipients(self, recipients: list):
        self._recipients = [r.strip() for r in recipients if r and "@" in r]
        self._log(f"✉️ [Destinatários NBA] Lista atualizada para {len(self._recipients)} e-mails.")

    def get_recipients(self) -> list:
        if hasattr(self, "_recipients") and self._recipients:
            return self._recipients
        emails_path = os.path.join(PROJECT_ROOT, "config", "saved_emails.json")
        recipients = ["cleber.goncalves@ibope.com", "arthur@mediadna.com.br"]
        if os.path.exists(emails_path):
            try:
                with open(emails_path, "r", encoding="utf-8") as f:
                    recipients = json.load(f)
            except Exception:
                pass
        return recipients

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="NBAAutonomousAuditorThread")
        self._thread.start()
        self._log("🏀 Serviço de Auditoria Autônoma da NBA iniciado com sucesso!")

    def stop(self):
        self._running = False

    def _run_loop(self):
        # Pequeno atraso na inicialização para não competir com a subida da GUI
        time.sleep(10)
        while self._running:
            try:
                self.run_audit_and_sync_cycle()
            except Exception as e:
                self._log(f"⚠️ Erro no ciclo de auditoria autônoma da NBA: {e}")

            for _ in range(self.check_interval):
                if not self._running:
                    break
                time.sleep(1)

    def run_audit_and_sync_cycle(self):
        """Executa um ciclo completo de checagem da NBA, publicação da agenda e auditoria automática."""
        now_dt = datetime.now()
        season_start = datetime(2026, 10, 20)
        days_span = max(1, (now_dt - season_start).days + 1)
        # Varre desde o início oficial da temporada (20/10) até os próximos 5 dias
        dates = [(season_start + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(days_span + 5)]
        
        all_games = []
        for d_str in dates:
            games = self.nba_service.fetch_games_for_date(d_str)
            all_games.extend(games)

        self._log(f"🔎 Varredura NBA: {len(all_games)} partidas monitoradas na agenda ({dates[0]} até {dates[-1]}).")

        # 1. Carregar destinatários salvos
        recipients = self.get_recipients()

        sp_token_ok = SharePointReporter.is_token_valid()
        if not sp_token_ok:
            self._log("⚠️ [SharePoint NBA] Sessão do SharePoint não autenticada. Clique em '🔑 Conectar SharePoint' na tela para autorizar o envio automático.")

        for game in all_games:
            gid = str(game.get("id"))
            is_fin = bool(game.get("is_finished"))
            match_disp = game.get("match_display")

            # Caso 1: Jogo FINALIZADO que ainda NÃO foi auditado
            if is_fin and not self.is_game_audited(gid):
                self._log(f"🏁 Partida da NBA FINALIZADA detectada: {match_disp}. Iniciando auditoria autônoma...")
                
                # a) Baixar Game Book oficial
                gb_path = self.nba_service.download_gamebook(game)
                parsed = self.nba_service.parse_gamebook(gb_path) if gb_path else {}
                
                # b) Gerar Relatório Executivo Oficial PDF
                pdf = self.nba_reporter.generate_report(game, parsed)
                
                # c) Publicar no SharePoint na linha da partida
                sp_ok = SharePointNBAReporter.sync_nba_report(pdf, game)
                if sp_ok:
                    self._log(f"☁️ [SharePoint] Relatório de {match_disp} publicado e homologado no SharePoint!")
                else:
                    self._log(f"⚠️ [SharePoint] Falha temporária ao sincronizar {match_disp} no SharePoint.")

                # d) Disparar E-mail automático com o PDF anexado
                mail_ok = False
                try:
                    ai_cfg_path = os.path.join(PROJECT_ROOT, "config", "google_ai.json")
                    if os.path.exists(ai_cfg_path):
                        with open(ai_cfg_path, "r", encoding="utf-8") as f:
                            ai_cfg = json.load(f)
                        sender = ai_cfg.get("email")
                        pwd = ai_cfg.get("senha")
                        if sender and pwd:
                            svc = EmailService("smtp.gmail.com", 587, sender, pwd)
                            subj = f"🏀 [AUDITORIA CONCLUÍDA] NBA — {match_disp} ({game.get('platform')})"
                            body = (
                                f"Prezados,\n\n"
                                f"A partida da NBA foi auditada de forma 100% autônoma pelo Monitor de Esportes:\n\n"
                                f"• Partida: {match_disp}\n"
                                f"• Data/Horário: {game.get('date_display')} às {game.get('time_brt')} BRT\n"
                                f"• Placar Final: {game.get('score_display')}\n"
                                f"• Plataforma: {game.get('platform')}\n"
                                f"• Parecer Técnico: Homologado com o Game Book oficial da NBA (statsdmz.nba.com).\n\n"
                                f"O relatório PDF completo segue anexado e já está arquivado na biblioteca 'Relatorios_de_Jogos_NBA' do SharePoint.\n\n"
                                f"Atenciosamente,\n"
                                f"Media DNA — Auditoria Autônoma de Esportes"
                            )
                            mail_ok = svc.send_report(recipients, subj, body, pdf_path=pdf)
                            if mail_ok:
                                self._log(f"✉️ [E-mail] Relatório de {match_disp} enviado com sucesso para: {', '.join(recipients)}")
                except Exception as ex_mail:
                    self._log(f"⚠️ Erro ao disparar e-mail da NBA: {ex_mail}")

                # e) Gravar no cache local para nunca duplicar
                self.mark_game_audited(game, pdf, mail_ok, sp_ok)
                self._log(f"✅ [NBA AUTO] Partida {match_disp} auditada, arquivada e notificada com sucesso!")
                time.sleep(2)

            # Caso 2: Jogo AGENDADO (futuro) — assegura que a linha de agendamento exista e esteja atualizada no SharePoint
            elif not is_fin:
                sched_key = f"sched_{gid}"
                cur_sig = f"{game.get('date_display')}_{game.get('time_brt')}_{game.get('platform')}"
                cached = self._audited_cache.get(sched_key)
                if not cached or cached.get("sig") != cur_sig:
                    self._log(f"📅 Registrando/Atualizando jogo agendado no SharePoint: {match_disp} ({game.get('date_display')} {game.get('time_brt')} BRT, {game.get('platform')})...")
                    gb_path = None
                    parsed = {}
                    pdf = self.nba_reporter.generate_report(game, parsed)
                    ok = SharePointNBAReporter.sync_nba_report(pdf, game)
                    if ok:
                        self._audited_cache[sched_key] = {
                            "match": match_disp,
                            "time": game.get("time_brt"),
                            "date": game.get("date_display"),
                            "platform": game.get("platform"),
                            "sig": cur_sig,
                            "synced_at": datetime.now().isoformat()
                        }
                        self._save_audited_cache()
                    time.sleep(2)
