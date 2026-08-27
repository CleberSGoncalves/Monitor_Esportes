import sys
import os
import ssl
from pathlib import Path
try:
    ssl._create_default_https_context = ssl._create_unverified_context
    orig_create_default_context = ssl.create_default_context
    def unverified_create_default_context(*args, **kwargs):
        context = orig_create_default_context(*args, **kwargs)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    ssl.create_default_context = unverified_create_default_context
except Exception:
    pass

# Bootstrap paths
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import threading
import time
import logging
import gc
from typing import Dict, Any, Optional, List

from config.settings import (
    CHANNEL_STREAMS_URL,
    AUTO_MONITOR_WHEN_LIVE,
    OBS_HOST,
    OBS_PORT,
    OBS_PASSWORD,
    OBS_EXE_PATH,
    OBS_ARGS,
)
from core.monitor_core import MonitorCoreMixin
from core.models import DebugSnapshot, MonitorRuntime
from modules.obs_controller import OBSController
from modules.event_detector import EventDetector
from modules.report_generator import ReportGenerator
from modules.api_provider import start_api_thread

# Mock do Tkinter/CustomTkinter para rodar Headless
class MockVar:
    def __init__(self, value=None):
        self._value = value
    def get(self):
        return self._value
    def set(self, val):
        self._value = val
    def trace_add(self, *args, **kwargs): pass

class HeadlessApp(MonitorCoreMixin):
    def __init__(self):
        print("[HEADLESS] Inicializando motor de monitoramento (Sem GUI)...")
        
        # 1. Variáveis de Estado (Simuladas)
        self.runtime = MonitorRuntime()
        self.debug_snapshot = DebugSnapshot()
        self._stop_flag = threading.Event()
        self._preview_lock = threading.Lock()
        
        # Variáveis que a API consome
        self.channel_url_var = MockVar(value=CHANNEL_STREAMS_URL)
        self.cloud_enabled_var = MockVar(value=True)
        self.cloud_interval_var = MockVar(value=2)
        self.banner_ocr_interval_var = MockVar(value=1.0)
        self.send_report_email_var = MockVar(value=False)
        self.email_recipients_var = MockVar(value="")
        self.auto_stop_pos_mins_var = MockVar(value=5)
        self.detector_stage_var = MockVar(value="Headless: Pronto")
        self.status_var = MockVar(value="🔴 Parado")
        self.channel_var = MockVar(value="CazéTV")
        self.sample_fps_var = MockVar(value=3)
        self.partial_report_var = MockVar(value=600)
        self.cleanup_days_var = MockVar(value=7)
        
        self._last_expert_results = []
        self._last_ad_results = []
        
        self.match_var = MockVar(value="—")
        self.comp_var = MockVar(value="—")
        
        # Mock de logs (apenas print)
        self._ia_logs = []
        
        # 2. Componentes
        self.obs = OBSController(
            host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD,
            obs_exe_path=OBS_EXE_PATH, obs_args=OBS_ARGS
        )
        self.detector = EventDetector()
        self.detector.set_logger(self._log)
        self.reporter = ReportGenerator(reports_dir=os.path.join(PROJECT_ROOT, "data", "reports"))
        
        # 3. Threads de controle herdadas do Mixin
        self._analysis_lock = threading.Lock()
        self._analysis_cv = threading.Condition(self._analysis_lock)
        self._last_frame_loop_ts = 0.0
        self._last_meta_update_t = 0.0
        self._pipeline_stats = {"queued": 0, "processed": 0, "dropped": 0}
        self._last_pipeline_processed_t = 0.0
        self._last_report_cloud_t = 0.0
        
        self.stream = None
        self._latest_raw_frame = None
        
        print("[HEADLESS] Componentes prontos.")

    def _log(self, msg: str):
        # Em modo headless, logamos no console com timestamp
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] [HEADLESS] {msg}")

    def _log_from_pipeline_component(self, msg: str):
        self._log(msg)

    def after(self, ms, func):
        # Simula o loop do Tkinter
        if ms == 0:
            func()
        else:
            threading.Timer(ms/1000.0, func).start()

    def _set_status(self, state_key: str, msg: str):
        self.status_var.set(msg)
        self._log(f"STATUS: {msg}")

    def _update_preview_widget(self):
        pass # Sem UI, sem preview real aqui

    def run(self):
        # Inicia a API e mantém o processo vivo
        print("[HEADLESS] Iniciando API Bridge...")
        start_api_thread(self, port=5000)
        
        print("\n" + "="*50)
        print("  SISTEMA RODANDO EM MODO HEADLESS")
        print("  Acesse: http://localhost:5000")
        print("  (Pressione Ctrl+C para encerrar)")
        print("="*50 + "\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[HEADLESS] Encerrando...")
            self._stop_flag.set()

    def _run_expert_batch_analysis(self, events: List[Dict[str, Any]]) -> None:
        """Versão Headless da análise em lote Expert."""
        import modules.expert_assistant
        from modules.expert_assistant import ExpertAssistant
        import traceback
        import json
        from datetime import datetime

        total = len(events)
        self._log(f"[EXPERT] Iniciando análise de lote para {total} evento(s).")
        self.status_var.set(f"⏳ Analisando 1/{total}...")

        def worker():
            try:
                cfg_path = os.path.join(PROJECT_ROOT, "config", "google_ai.json")
                if not os.path.exists(cfg_path):
                    self._log("[EXPERT] Erro: google_ai.json não encontrado.")
                    return
                
                with open(cfg_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    api_key = config_data.get("gemini_api_key") or config_data.get("api_key")
                    yt_key = config_data.get("youtube_api_key")
                    model_id = config_data.get("model", "gemini-2.0-flash")
                
                assistant = ExpertAssistant(api_key=api_key, model_id=model_id, yt_api_key=yt_key)
                all_results = []
                
                for idx, ev in enumerate(events):
                    title = ev.get("title", "Evento")
                    self._log(f"[EXPERT] Analisando {idx+1}/{total}: {title}")
                    self.status_var.set(f"⏳ Analisando {idx+1}/{total}: {title}")
                    
                    # Simulação de extração de meta (simplificada para headless)
                    team1, team2 = "Time 1", "Time 2"
                    if " x " in title:
                        parts = title.split(" x ")
                        team1 = parts[0].strip()
                        team2 = parts[1].split("(")[0].strip() if "(" in parts[1] else parts[1].strip()

                    # Extracao de data confiavel do YouTube
                    event_date_raw = ev.get("scheduled_start") or ""
                    event_date = datetime.now().strftime("%d/%m/%Y")
                    if event_date_raw:
                        date_part = event_date_raw.split(" ")[0]
                        parts = date_part.split("-")
                        if len(parts) == 3:
                            event_date = f"{parts[2]}/{parts[1]}/{parts[0]}"

                    payload = {
                        "team1": team1,
                        "team2": team2,
                        "competition": "Geral",
                        "platform": self.channel_var.get(),
                        "date": event_date,
                        "start_timestamp": ev.get("timestamp") or ev.get("release_timestamp") or ev.get("actual_start_time"),
                        "video_url": ev.get("url")
                    }
                    
                    time.sleep(2.0) # Rate limit protection
                    
                    try:
                        result = assistant.get_match_chronology(**payload)
                        if "error" not in result:
                            all_results.append(result)
                            self._log(f"[EXPERT] OK: {title}")
                    except Exception as e:
                        self._log(f"[EXPERT] Erro no evento {title}: {e}")

                # Finalização
                if all_results:
                    pdf_path = self.reporter.write_expert_report(all_results)
                    self._log(f"[EXPERT] Relatório gerado: {pdf_path}")
                if all_results:
                    self._last_expert_results.append(all_results)
                
                self.status_var.set("🟢 Análise Expert concluída")
            except Exception as e:
                self._log(f"[EXPERT] Erro fatal no worker: {e}")
                self._log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _run_expert_analysis(self, data: Dict[str, Any]) -> None:
        """Análise Expert individual (Manual)."""
        self._run_expert_batch_analysis([{"title": f"{data.get('team1')} x {data.get('team2')}", "url": data.get("video_url")}])

    def _run_ad_analysis(self, files: List[str] = None) -> None:
        """Versão Headless da análise de Ads em lote."""
        from modules.ad_analyzer import AdAnalyzer
        import json
        
        # Se não vierem arquivos, podemos pegar de algum estado ou ignorar
        if not files:
            self._log("[ADS] Nenhum arquivo fornecido para análise.")
            return

        def worker():
            try:
                cfg_path = os.path.join(PROJECT_ROOT, "config", "google_ai.json")
                with open(cfg_path, "r") as f:
                    data = json.load(f)
                    key = data.get("gemini_api_key") or data.get("api_key")
                    model_id = data.get("model", "gemini-2.0-flash")
                    analyzer = AdAnalyzer(key, model_id=model_id)

                self._log(f"[ADS] Iniciando análise de {len(files)} vídeos...")
                cumulative_offset = 0
                all_results = []

                for idx, f_path in enumerate(files):
                    f_name = os.path.basename(f_path)
                    self._log(f"[ADS] Analisando {idx+1}/{len(files)}: {f_name}")
                    
                    # Callback de progresso (log)
                    def prog_cb(msg): self._log(f"[ADS] [{f_name}] {msg}")
                    
                    results = analyzer.analyze_video(
                        f_path,
                        progress_callback=prog_cb,
                        extra_offset_sec=cumulative_offset
                    )
                    all_results.extend(results)
                    
                    duration = analyzer.get_video_duration(f_path)
                    cumulative_offset += int(duration)

                if all_results:
                    pdf_path = self.reporter.write_ad_report(files[0], all_results)
                    self._log(f"[ADS] Relatório gerado: {pdf_path}")
                
                self.status_var.set("🟢 Análise de Ads concluída")
            except Exception as e:
                self._log(f"[ADS] Erro na análise: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _run_cleanup_now(self) -> None:
        """Versão Headless do Cleanup."""
        import shutil
        try:
            days = int(self.cleanup_days_var.get() or 7)
            base_events = os.path.join(PROJECT_ROOT, "data", "events")
            cutoff = time.time() - (days * 86400)
            removed = 0
            if os.path.exists(base_events):
                for name in os.listdir(base_events):
                    p = os.path.join(base_events, name)
                    if os.path.isdir(p) and os.path.getmtime(p) < cutoff:
                        shutil.rmtree(p, ignore_errors=True)
                        removed += 1
            self._log(f"[CLEANUP] Removidos {removed} eventos antigos.")
        except Exception as e:
            self._log(f"[CLEANUP] Erro: {e}")

if __name__ == "__main__":
    app = HeadlessApp()
    app.run()
