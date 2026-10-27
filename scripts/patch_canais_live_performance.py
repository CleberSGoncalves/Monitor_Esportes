# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def patch_live_channel_monitor():
    path = Path("modules/live_channel_monitor.py")
    content = path.read_text(encoding="utf-8")

    # 1. Update apply_auto_detect_all to avoid queueing ancient ended videos
    old_apply_pattern = r"def apply_auto_detect_all\(self,\s*silent:\s*bool\s*=\s*False\)\s*->\s*int:.*?(?=\s+if added and not silent:)"
    new_apply = """def apply_auto_detect_all(self, silent: bool = False) -> int:
        \"\"\"Enfileira automaticamente apenas eventos ativos, futuros e recém-encerrados (últimas 24h).\"\"\"
        added = 0
        now = time.time()
        with self.lock:
            if not self.get_setting("auto_detect_match", True):
                return 0
            for vid, ev in self.state["events"].items():
                if ev.get("selected") or ev.get("user_unselected"):
                    continue
                if _is_24h_or_continuous_stream(ev.get("title", ""), ev):
                    continue
                st = ev.get("status")
                # Apenas enfileirar se for ao vivo, futuro ou se encerrou nas últimas 24h
                is_recent_ended = False
                if st == "ended":
                    ref_time = ev.get("ended_detected_at") or ev.get("actual_start_epoch") or 0
                    if ref_time and (now - ref_time) <= 86400:
                        is_recent_ended = True
                
                if st in ("upcoming", "live") or is_recent_ended:
                    ev["selected"] = True
                    ev["auto_queued"] = True
                    if ev.get("pipeline") in (None, "", "idle"):
                        ev["pipeline"] = "live" if st == "live" else ("ended" if st == "ended" else "waiting")
                        ev["next_attempt"] = 0
                        ev["last_check"] = 0
                    added += 1"""

    new_content, count = re.subn(old_apply_pattern, new_apply, content, count=1, flags=re.DOTALL)
    if count:
        content = new_content
        print("[+] apply_auto_detect_all optimized for recent events only!")

    # 2. Add clean_queue_keep_active method
    if "def clean_queue_keep_active" not in content:
        clean_method = """
    def clean_queue_keep_active(self) -> int:
        \"\"\"Remove da fila eventos encerrados antigos que não possuem PDF gerado nem narração ativa.\"\"\"
        with self.lock:
            removed = 0
            for vid, ev in list(self.state["events"].items()):
                if ev.get("selected"):
                    is_active = ev.get("pipeline") in ("live", "transcribing", "analyzing", "generating") or ev.get("status") in ("live", "upcoming")
                    has_result = bool(ev.get("pdf_path") or ev.get("narration_path"))
                    if not is_active and not has_result:
                        ev["selected"] = False
                        removed += 1
            if removed:
                self._changed()
                self.log(f"🧹 [Fila] Limpeza concluída: {removed} eventos antigos removidos da fila de análise.")
            return removed
"""
        if "def unapply_auto_detect_waiting" in content:
            content = content.replace("    def unapply_auto_detect_waiting", clean_method + "\n    def unapply_auto_detect_waiting")
            print("[+] Added clean_queue_keep_active method!")

    # 3. Add progress throttling to update_event
    old_update = """    def update_event(self, vid: str, **fields) -> None:
        with self.lock:
            ev = self.state["events"].get(vid)
            if ev is None:
                return
            ev.update(fields)
            ev["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._changed()"""

    new_update = """    def update_event(self, vid: str, notify: bool = True, **fields) -> None:
        with self.lock:
            ev = self.state["events"].get(vid)
            if ev is None:
                return
            pipe_changed = "pipeline" in fields and fields["pipeline"] != ev.get("pipeline")
            pdf_changed = "pdf_path" in fields and fields["pdf_path"] != ev.get("pdf_path")
            sel_changed = "selected" in fields and fields["selected"] != ev.get("selected")
            err_changed = "error" in fields and fields["error"] != ev.get("error")
            ev.update(fields)
            ev["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Só notifica a interface e salva o disco imediatamente se houver mudança de estado estrutural
        is_structural = pipe_changed or pdf_changed or sel_changed or err_changed
        if notify and is_structural:
            self._changed()
        elif notify and "progress" in fields:
            # Progresso simples: salva com throttle e avisa suavemente
            now = time.time()
            if now - getattr(self, "_last_prog_notify", 0) > 1.0:
                self._last_prog_notify = now
                if self.on_change:
                    try:
                        self.on_change()
                    except Exception:
                        pass"""

    if old_update in content:
        content = content.replace(old_update, new_update)
        print("[+] update_event throttled to prevent UI redraw storms!")

    path.write_text(content, encoding="utf-8")
    print("[+] live_channel_monitor.py patched successfully.")

if __name__ == "__main__":
    patch_live_channel_monitor()
