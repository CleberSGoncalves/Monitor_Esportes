from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import time
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from vision_test import read_hud_fast, read_banner_fast, read_countdown_fast

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

import cv2


ROI_NAMES = ["top_hud_unificado", "banner", "countdown_center"]
READ_MODES = [
    "roi_only",
    "hud_only",
    "banner_only",
    "countdown_only",
    "full_pipeline",
    "hud_countdown_debug",
    "hud_direct_only",
]


class RoiHudTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ROI HUD Test GUI v9 - vision_test isolado")
        self.root.geometry("1760x1000")

        self.image_bgr = None
        self.tk_img = None
        self.crop_tk = None
        self.detector = None
        self.rois = {}
        self.scale = 1.0
        self.dragging = False
        self.drag_start = None
        self.drag_end = None
        self.read_lock = threading.Lock()

        self.current_roi_name = tk.StringVar(value="top_hud_unificado")
        self.show_all_var = tk.BooleanVar(value=True)
        self.auto_read_var = tk.BooleanVar(value=False)
        self.read_mode_var = tk.StringVar(value="full_pipeline")
        self.status_var = tk.StringVar(value="Pronto.")
        self.clear_log_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)

        tk.Button(top, text="Abrir imagem", command=self.open_image).pack(side=tk.LEFT)
        tk.Button(top, text="Abrir detector (opcional)", command=self.open_detector).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(top, text="Rodar leitura", command=self.run_read_async).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(top, text="Salvar ROI JSON", command=self.save_roi_json).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(top, text="Carregar ROI JSON", command=self.load_roi_json).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(top, text="Reset ROI atual", command=self.reset_current_roi).pack(side=tk.LEFT, padx=(6, 0))

        tk.Label(top, text="ROI:").pack(side=tk.LEFT, padx=(16, 4))
        self.roi_combo = ttk.Combobox(top, textvariable=self.current_roi_name, values=ROI_NAMES, width=22, state="readonly")
        self.roi_combo.pack(side=tk.LEFT)
        self.roi_combo.bind("<<ComboboxSelected>>", lambda e: self.redraw())

        tk.Label(top, text="Modo:").pack(side=tk.LEFT, padx=(12, 4))
        self.mode_combo = ttk.Combobox(top, textvariable=self.read_mode_var, values=READ_MODES, width=22, state="readonly")
        self.mode_combo.pack(side=tk.LEFT)

        tk.Checkbutton(top, text="Mostrar 3 ROIs", variable=self.show_all_var, command=self.redraw).pack(side=tk.LEFT, padx=(10, 0))
        tk.Checkbutton(top, text="Auto leitura", variable=self.auto_read_var).pack(side=tk.LEFT, padx=(10, 0))
        tk.Checkbutton(top, text="Limpar log", variable=self.clear_log_var).pack(side=tk.LEFT, padx=(10, 0))

        status = tk.Label(self.root, textvariable=self.status_var, anchor="w", relief="sunken")
        status.pack(side=tk.BOTTOM, fill=tk.X)

        main = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        left = tk.Frame(main)
        right = tk.Frame(main)
        main.add(left, stretch="always")
        main.add(right)

        self.canvas = tk.Canvas(left, bg="black", width=1040, height=820)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        tk.Label(right, text="Detector:").pack(anchor="w")
        self.detector_entry = tk.Entry(right, width=92)
        self.detector_entry.pack(fill=tk.X, pady=(0, 8))

        tk.Label(right, text="Imagem:").pack(anchor="w")
        self.image_entry = tk.Entry(right, width=92)
        self.image_entry.pack(fill=tk.X, pady=(0, 8))

        tk.Label(right, text="Fases / tempos do processo").pack(anchor="w")
        self.stage_text = tk.Text(right, width=88, height=18)
        self.stage_text.pack(fill=tk.BOTH, expand=False)

        tk.Label(right, text="Resultado final").pack(anchor="w", pady=(10, 0))
        self.result_text = tk.Text(right, width=88, height=24)
        self.result_text.pack(fill=tk.BOTH, expand=False)

        tk.Label(right, text="Crop do ROI atual").pack(anchor="w", pady=(12, 0))
        self.crop_label = tk.Label(right, bg="#222", width=84, height=14)
        self.crop_label.pack(fill=tk.BOTH, expand=False)

    def _set_status(self, text):
        self.status_var.set(text)
        self.root.update_idletasks()

    def _set_result(self, text):
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)

    def _set_stage_log(self, text):
        self.stage_text.delete("1.0", tk.END)
        self.stage_text.insert(tk.END, text)
        self.stage_text.see(tk.END)

    def _append_stage_log(self, text):
        self.stage_text.insert(tk.END, text + "\n")
        self.stage_text.see(tk.END)

    def _publish_stage(self, text):
        self.root.after(0, lambda t=text: self._append_stage_log(t))

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("Todos", "*.*")])
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Erro", f"Não foi possível abrir a imagem:\n{path}")
            return
        self.image_bgr = img
        self.image_entry.delete(0, tk.END)
        self.image_entry.insert(0, path)
        self._ensure_default_rois()
        self._set_status(f"Imagem carregada: {os.path.basename(path)} | {img.shape[1]}x{img.shape[0]}")
        self.redraw()

    def open_detector(self):
        path = filedialog.askopenfilename(filetypes=[("Python", "*.py")])
        if not path:
            return
        self.load_detector(path)

    def load_detector(self, module_path):
        try:
            module_path = os.path.abspath(module_path)
            module_name = f"vision_detectors_dynamic_{abs(hash(module_path))}"
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise ImportError("Não foi possível criar spec do módulo")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            module.__file__ = module_path
            module.__package__ = ""
            spec.loader.exec_module(module)

            detector_cls = getattr(module, "VisionDetectors", None)
            if detector_cls is None:
                raise AttributeError("Classe VisionDetectors não encontrada no módulo")

            self.detector = detector_cls()
            self.detector_entry.delete(0, tk.END)
            self.detector_entry.insert(0, module_path)

            extracted = self._extract_rois_from_detector(self.detector)
            self.rois = {name: extracted[name] for name in ROI_NAMES if name in extracted}
            self._ensure_default_rois()
            self._apply_rois_to_detector()

            self._set_result("Detector carregado com sucesso (opcional).")
            self._set_stage_log("Detector carregado com sucesso.\nLeitura interna isolada em vision_test.py.")
            self._set_status("Detector carregado.")
            self.redraw()
        except Exception:
            err = traceback.format_exc()
            self._set_result(err)
            self._set_stage_log(err)
            self._set_status("Erro ao carregar detector.")
            messagebox.showerror("Erro ao carregar detector", err)

    def _extract_rois_from_detector(self, detector):
        rois = {}
        for attr_name in ("rois", "ROIS", "default_rois", "scoreboard_rois", "roi_overrides"):
            value = getattr(detector, attr_name, None)
            if isinstance(value, dict):
                for k, v in value.items():
                    if k in ROI_NAMES and isinstance(v, dict) and all(key in v for key in ("x", "y", "w", "h")):
                        rois[k] = {
                            "x": float(v["x"]),
                            "y": float(v["y"]),
                            "w": float(v["w"]),
                            "h": float(v["h"]),
                        }
        return rois

    def _ensure_default_rois(self):
        defaults = {
            "top_hud_unificado": {"x": 0.02, "y": 0.015, "w": 0.285, "h": 0.095},
            "banner": {"x": 0.02, "y": 0.77, "w": 0.96, "h": 0.16},
            "countdown_center": {"x": 0.38, "y": 0.06, "w": 0.22, "h": 0.08},
        }
        for name in ROI_NAMES:
            roi = self.rois.get(name)
            if not isinstance(roi, dict):
                self.rois[name] = dict(defaults[name])
                continue
            try:
                x = float(roi.get("x", 0))
                y = float(roi.get("y", 0))
                w = float(roi.get("w", 0))
                h = float(roi.get("h", 0))
            except Exception:
                self.rois[name] = dict(defaults[name])
                continue
            if not (0.0 <= x <= 0.999 and 0.0 <= y <= 0.999 and 0.001 <= w <= 1.0 and 0.001 <= h <= 1.0):
                self.rois[name] = dict(defaults[name])

    def _roi_pct_to_pixels(self, roi):
        if self.image_bgr is None:
            return None
        img_h, img_w = self.image_bgr.shape[:2]
        x = int(round(float(roi["x"]) * img_w))
        y = int(round(float(roi["y"]) * img_h))
        w = int(round(float(roi["w"]) * img_w))
        h = int(round(float(roi["h"]) * img_h))
        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        w = max(1, min(w, img_w - x))
        h = max(1, min(h, img_h - y))
        return x, y, w, h

    def redraw(self):
        if self.image_bgr is None or Image is None:
            self.canvas.delete("all")
            return

        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        h, w = self.image_bgr.shape[:2]
        self.scale = min(canvas_w / w, canvas_h / h)
        disp_w = max(1, int(w * self.scale))
        disp_h = max(1, int(h * self.scale))
        disp = cv2.resize(self.image_bgr, (disp_w, disp_h), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
        self.tk_img = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        colors = {
            "top_hud_unificado": "#00ff88",
            "banner": "#44bbff",
            "countdown_center": "#ffcc00",
        }

        if self.show_all_var.get():
            for name in ROI_NAMES:
                roi = self.rois.get(name)
                if roi:
                    self._draw_roi(name, roi, colors.get(name, "#00ff88"))
        else:
            roi = self.rois.get(self.current_roi_name.get())
            if roi:
                self._draw_roi(self.current_roi_name.get(), roi, colors.get(self.current_roi_name.get(), "#ffcc00"))

        if self.dragging and self.drag_start and self.drag_end:
            x1, y1 = self.drag_start
            x2, y2 = self.drag_end
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="#ff4444", width=2)

        self.update_crop_preview()

    def _draw_roi(self, name, roi, color):
        px = self._roi_pct_to_pixels(roi)
        if px is None:
            return
        x, y, w, h = px
        sx = int(x * self.scale)
        sy = int(y * self.scale)
        sw = int(w * self.scale)
        sh = int(h * self.scale)
        self.canvas.create_rectangle(sx, sy, sx + sw, sy + sh, outline=color, width=2)
        self.canvas.create_text(sx + 4, max(10, sy - 12), anchor="nw", text=name, fill=color)

    def on_mouse_down(self, event):
        if self.image_bgr is None:
            return
        self.dragging = True
        self.drag_start = (event.x, event.y)
        self.drag_end = (event.x, event.y)
        self.redraw()

    def on_mouse_drag(self, event):
        if not self.dragging:
            return
        self.drag_end = (event.x, event.y)
        self.redraw()

    def on_mouse_up(self, event):
        if not self.dragging or self.image_bgr is None:
            return
        self.dragging = False
        self.drag_end = (event.x, event.y)

        x1, y1 = self.drag_start
        x2, y2 = self.drag_end
        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])

        if abs(x2 - x1) < 3 or abs(y2 - y1) < 3:
            self.redraw()
            return

        img_h, img_w = self.image_bgr.shape[:2]
        px = int(x1 / self.scale)
        py = int(y1 / self.scale)
        pw = int((x2 - x1) / self.scale)
        ph = int((y2 - y1) / self.scale)

        self.rois[self.current_roi_name.get()] = {
            "x": max(0.0, min(px / img_w, 0.999)),
            "y": max(0.0, min(py / img_h, 0.999)),
            "w": max(0.001, min(pw / img_w, 1.0)),
            "h": max(0.001, min(ph / img_h, 1.0)),
        }

        self._apply_rois_to_detector()
        self.redraw()
        if self.auto_read_var.get():
            self.run_read_async()

    def _apply_rois_to_detector(self):
        if self.detector is None:
            return
        payload = {name: dict(self.rois[name]) for name in ROI_NAMES if name in self.rois}
        if hasattr(self.detector, "roi_overrides") and isinstance(self.detector.roi_overrides, dict):
            self.detector.roi_overrides.update(payload)
        for attr_name in ("rois", "ROIS", "default_rois", "scoreboard_rois"):
            value = getattr(self.detector, attr_name, None)
            if isinstance(value, dict):
                value.update(payload)

    def update_crop_preview(self):
        if self.image_bgr is None or Image is None:
            return
        roi = self.rois.get(self.current_roi_name.get())
        if not roi:
            self.crop_label.configure(image="", text="")
            return
        px = self._roi_pct_to_pixels(roi)
        if px is None:
            self.crop_label.configure(image="", text="")
            return
        x, y, w, h = px
        crop = self.image_bgr[y:y + h, x:x + w]
        if crop.size == 0:
            self.crop_label.configure(image="", text="")
            return
        max_w, max_h = 640, 240
        ch, cw = crop.shape[:2]
        scale = min(max_w / max(1, cw), max_h / max(1, ch))
        crop = cv2.resize(crop, (max(1, int(cw * scale)), max(1, int(ch * scale))), interpolation=cv2.INTER_AREA)
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        self.crop_tk = ImageTk.PhotoImage(Image.fromarray(crop_rgb))
        self.crop_label.configure(image=self.crop_tk, text="")

    def _crop_named_roi(self, frame, name):
        roi = self.rois.get(name)
        if not roi:
            return None, None
        img_h, img_w = frame.shape[:2]
        x = int(round(float(roi["x"]) * img_w))
        y = int(round(float(roi["y"]) * img_h))
        w = int(round(float(roi["w"]) * img_w))
        h = int(round(float(roi["h"]) * img_h))
        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        w = max(1, min(w, img_w - x))
        h = max(1, min(h, img_h - y))
        crop = frame[y:y + h, x:x + w]
        return {"x": x, "y": y, "w": w, "h": h}, crop

    def run_read_async(self):
        if self.image_bgr is None:
            messagebox.showwarning("Aviso", "Abra uma imagem primeiro.")
            return
        if self.read_lock.locked():
            return
        if self.clear_log_var.get():
            self._set_stage_log("")
            self._set_result("")
        self._set_status("Executando leitura...")
        self._publish_stage("▶ Iniciando análise assíncrona...")
        threading.Thread(target=self._run_read_worker, daemon=True).start()

    def _time_call(self, label, fn, *args, **kwargs):
        self._publish_stage(f"• {label}: iniciando")
        t0 = time.perf_counter()
        try:
            value = fn(*args, **kwargs)
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            self._publish_stage(f"✓ {label}: {elapsed_ms} ms")
            return {"ok": True, "value": value, "elapsed_ms": elapsed_ms, "error": None}
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            tb = traceback.format_exc()
            self._publish_stage(f"✗ {label}: erro em {elapsed_ms} ms -> {exc}")
            return {"ok": False, "value": None, "elapsed_ms": elapsed_ms, "error": tb}

    def _extract_countdown_value(self, value):
        if value is None:
            return None
        if isinstance(value, dict):
            for key in ("countdown", "value", "text", "best", "result"):
                v = value.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            return None
        if isinstance(value, str):
            text = value.strip()
            return text or None
        return str(value)

    def _merge_hud_with_countdown(self, hud, cd_value, cd_meta=None):
        hud = dict(hud or {})
        countdown = None
        for key in ("countdown", "countdown_text", "timer_text"):
            v = hud.get(key)
            if isinstance(v, str) and v.strip():
                countdown = v.strip()
                break
        source = "hud"
        if not countdown and cd_value:
            countdown = cd_value
            source = "countdown_center"
        hud["countdown"] = countdown
        hud["countdown_source"] = source if countdown else None
        if cd_meta is not None:
            hud["countdown_fallback_meta"] = cd_meta
        return hud

    def _internal_read_screen_context(self, frame, include_banner=True, include_countdown_fallback=True):
        hud_roi, _ = self._crop_named_roi(frame, "top_hud_unificado")
        banner_roi, _ = self._crop_named_roi(frame, "banner")
        countdown_roi, _ = self._crop_named_roi(frame, "countdown_center")

        timeline = []

        t0 = time.perf_counter()
        hud = read_hud_fast(frame, (hud_roi["x"], hud_roi["y"], hud_roi["w"], hud_roi["h"])) if hud_roi else {}
        timeline.append({"stage": "read_hud_fast", "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1), "ok": True})

        countdown_meta = {"used": False, "source": None, "raw": None}
        countdown_value = None

        if include_countdown_fallback and countdown_roi:
            hud_countdown = None
            for key in ("countdown", "countdown_text", "timer_text"):
                v = (hud or {}).get(key)
                if isinstance(v, str) and v.strip():
                    hud_countdown = v.strip()
                    break

            if hud_countdown:
                countdown_value = hud_countdown
                countdown_meta.update({"used": True, "source": "hud", "raw": hud_countdown})
                timeline.append({"stage": "read_countdown_fast", "elapsed_ms": 0.0, "ok": True, "skipped": "countdown já veio do hud"})
            else:
                t1 = time.perf_counter()
                cd = read_countdown_fast(frame, (countdown_roi["x"], countdown_roi["y"], countdown_roi["w"], countdown_roi["h"]))
                cd_elapsed = round((time.perf_counter() - t1) * 1000.0, 1)
                cd_value = self._extract_countdown_value(cd)
                if cd_value:
                    countdown_value = cd_value
                    countdown_meta.update({"used": True, "source": "countdown_center", "raw": cd})
                else:
                    countdown_meta.update({"used": False, "source": "countdown_center", "raw": cd})
                timeline.append({"stage": "read_countdown_fast", "elapsed_ms": cd_elapsed, "ok": True})

        t2 = time.perf_counter()
        hud = self._merge_hud_with_countdown(hud, countdown_value, countdown_meta)
        timeline.append({"stage": "merge_hud_with_countdown", "elapsed_ms": round((time.perf_counter() - t2) * 1000.0, 1), "ok": True})

        if include_banner and banner_roi:
            t3 = time.perf_counter()
            banner = read_banner_fast(frame, (banner_roi["x"], banner_roi["y"], banner_roi["w"], banner_roi["h"]))
            timeline.append({"stage": "read_banner_fast", "elapsed_ms": round((time.perf_counter() - t3) * 1000.0, 1), "ok": True})
        else:
            banner = {"banner_text": "", "context_summary": "", "engine": "skipped", "lines": [], "ocr_ms": 0.0}
            timeline.append({"stage": "read_banner_fast", "elapsed_ms": 0.0, "ok": True, "skipped": True})

        return {
            "scoreboard": {
                "score": hud.get("score"),
                "clock": hud.get("clock"),
                "countdown": hud.get("countdown"),
                "phase_text": hud.get("phase_text"),
                "visible": bool(hud.get("score") or hud.get("clock") or hud.get("phase_text") or hud.get("countdown")),
                "competition_text": "",
                "teams": [None, None],
            },
            "top_hud": hud,
            "banner_text": banner.get("banner_text"),
            "context_summary": banner.get("context_summary") or hud.get("context_text") or hud.get("phase_text") or "",
            "phase": hud.get("phase_text"),
            "banner_meta": banner,
            "countdown_meta": countdown_meta,
            "internal_timeline": timeline,
        }

    def _debug_read_hud_direct(self, frame):
        roi, _ = self._crop_named_roi(frame, "top_hud_unificado")
        if not roi:
            return {}
        return read_hud_fast(frame, (roi["x"], roi["y"], roi["w"], roi["h"]))

    def _debug_read_countdown_direct(self, frame):
        roi, _ = self._crop_named_roi(frame, "countdown_center")
        if not roi:
            return None
        return read_countdown_fast(frame, (roi["x"], roi["y"], roi["w"], roi["h"]))

    def _run_read_worker(self):
        overall_start = time.perf_counter()
        with self.read_lock:
            try:
                frame = self.image_bgr.copy()
                self._publish_stage("• frame.copy: iniciando")
                copy_elapsed = round((time.perf_counter() - overall_start) * 1000.0, 1)
                self._publish_stage(f"✓ frame.copy: {copy_elapsed} ms")

                self._publish_stage("• apply_rois: iniciando")
                t_apply = time.perf_counter()
                self._apply_rois_to_detector()
                apply_elapsed = round((time.perf_counter() - t_apply) * 1000.0, 1)
                self._publish_stage(f"✓ apply_rois: {apply_elapsed} ms")

                mode = self.read_mode_var.get()
                result = {
                    "mode": mode,
                    "roi_name": self.current_roi_name.get(),
                    "timeline": [
                        {"stage": "frame.copy", "elapsed_ms": copy_elapsed},
                        {"stage": "apply_rois", "elapsed_ms": apply_elapsed},
                    ],
                    "active_rois_pct": {name: self.rois.get(name) for name in ROI_NAMES},
                }

                if mode == "roi_only":
                    roi, crop = self._crop_named_roi(frame, self.current_roi_name.get())
                    t0 = time.perf_counter()
                    if crop is None or crop.size == 0:
                        result["error"] = "ROI atual vazio ou inválido."
                    else:
                        result["roi_px"] = roi
                        result["crop_shape"] = list(crop.shape)
                        result["hint"] = "Modo rápido: só valida o recorte."
                    elapsed = round((time.perf_counter() - t0) * 1000.0, 1)
                    result["timeline"].append({"stage": "roi_only", "elapsed_ms": elapsed})
                    self._publish_stage(f"✓ roi_only: {elapsed} ms")

                elif mode == "hud_direct_only":
                    step_hud = self._time_call("read_hud_fast", self._debug_read_hud_direct, frame)
                    result["timeline"].append({"stage": "read_hud_fast", "elapsed_ms": step_hud["elapsed_ms"], "ok": step_hud["ok"]})
                    result["hud_direct_only"] = step_hud["value"] if step_hud["ok"] else None
                    if not step_hud["ok"]:
                        result["error"] = step_hud["error"]

                elif mode == "hud_only":
                    step = self._time_call("read_screen_context_internal", self._internal_read_screen_context, frame, False, True)
                    result["timeline"].append({"stage": "read_screen_context_internal", "elapsed_ms": step["elapsed_ms"], "ok": step["ok"]})
                    if step["ok"]:
                        ctx = step["value"]
                        result["hud_only"] = {
                            "scoreboard": ctx.get("scoreboard"),
                            "top_hud": ctx.get("top_hud"),
                            "countdown_meta": ctx.get("countdown_meta"),
                            "banner_text": "",
                            "context_summary": ctx.get("top_hud", {}).get("context_text", ""),
                            "phase": ctx.get("phase"),
                            "internal_timeline": ctx.get("internal_timeline", []),
                        }
                    else:
                        result["error"] = step["error"]

                elif mode == "banner_only":
                    roi, _ = self._crop_named_roi(frame, "banner")
                    step = self._time_call("read_banner_fast", read_banner_fast, frame, (roi["x"], roi["y"], roi["w"], roi["h"]) if roi else (0, 0, 0, 0))
                    result["timeline"].append({"stage": "read_banner_fast", "elapsed_ms": step["elapsed_ms"], "ok": step["ok"]})
                    if step["ok"]:
                        result["banner_only"] = step["value"]
                    else:
                        result["error"] = step["error"]

                elif mode == "countdown_only":
                    roi, _ = self._crop_named_roi(frame, "countdown_center")
                    step = self._time_call("read_countdown_fast", read_countdown_fast, frame, (roi["x"], roi["y"], roi["w"], roi["h"]) if roi else (0, 0, 0, 0))
                    result["timeline"].append({"stage": "read_countdown_fast", "elapsed_ms": step["elapsed_ms"], "ok": step["ok"]})
                    result["countdown_only"] = {
                        "raw_result": step["value"] if step["ok"] else None,
                        "countdown": self._extract_countdown_value(step["value"]) if step["ok"] else None,
                        "phase_text": None,
                        "phase": None,
                    }
                    if not step["ok"]:
                        result["error"] = step["error"]

                elif mode == "hud_countdown_debug":
                    step_hud = self._time_call("read_hud_fast", self._debug_read_hud_direct, frame)
                    result["timeline"].append({"stage": "read_hud_fast", "elapsed_ms": step_hud["elapsed_ms"], "ok": step_hud["ok"]})

                    step_cd = self._time_call("read_countdown_fast", self._debug_read_countdown_direct, frame)
                    result["timeline"].append({"stage": "read_countdown_fast", "elapsed_ms": step_cd["elapsed_ms"], "ok": step_cd["ok"]})

                    hud_value = step_hud["value"] if step_hud["ok"] else {}
                    cd_raw = step_cd["value"] if step_cd["ok"] else None
                    cd_value = self._extract_countdown_value(cd_raw)
                    merged = self._merge_hud_with_countdown(hud_value, cd_value, {
                        "used": bool(cd_value),
                        "source": "countdown_center" if cd_value else None,
                        "raw": cd_raw,
                    })

                    result["hud_countdown_debug"] = {
                        "hud_raw": hud_value,
                        "countdown_raw": cd_raw,
                        "countdown_extracted": cd_value,
                        "merged": merged,
                    }

                    if not step_hud["ok"]:
                        result["error_hud"] = step_hud["error"]
                    if not step_cd["ok"]:
                        result["error_countdown"] = step_cd["error"]

                elif mode == "full_pipeline":
                    pipeline = {}
                    step_ctx = self._time_call("read_screen_context_internal", self._internal_read_screen_context, frame, True, True)
                    result["timeline"].append({"stage": "read_screen_context_internal", "elapsed_ms": step_ctx["elapsed_ms"], "ok": step_ctx["ok"]})
                    if step_ctx["ok"]:
                        ctx_value = step_ctx["value"]
                        pipeline["read_screen_context"] = {
                            "scoreboard": ctx_value.get("scoreboard"),
                            "top_hud": ctx_value.get("top_hud"),
                            "banner_text": ctx_value.get("banner_text"),
                            "context_summary": ctx_value.get("context_summary"),
                            "phase": ctx_value.get("phase"),
                            "banner_meta": ctx_value.get("banner_meta"),
                            "countdown_meta": ctx_value.get("countdown_meta"),
                            "internal_timeline": ctx_value.get("internal_timeline", []),
                        }
                    else:
                        pipeline["read_screen_context"] = {"error": step_ctx["error"]}
                    result["full_pipeline"] = pipeline

                else:
                    result["error"] = f"Modo inválido: {mode}"
                    self._publish_stage(f"✗ modo inválido: {mode}")

                total_elapsed = round((time.perf_counter() - overall_start) * 1000.0, 1)
                result["elapsed_ms"] = total_elapsed
                self._publish_stage(f"🏁 Total: {total_elapsed} ms")
                text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
                status = f"Leitura concluída em {total_elapsed} ms."
            except Exception:
                text = traceback.format_exc()
                status = "Erro durante leitura."
                self._publish_stage("✗ Falha geral durante a leitura.")
            self.root.after(0, lambda t=text, s=status: self._finish_read(t, s))

    def _finish_read(self, text, status):
        self._set_result(text)
        self._set_status(status)

    def save_roi_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        payload = {name: self.rois.get(name) for name in ROI_NAMES if name in self.rois}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        self._set_status(f"ROI salvo em {os.path.basename(path)}.")

    def load_roi_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            messagebox.showerror("Erro", "JSON inválido.")
            return
        for name in ROI_NAMES:
            if name in data and isinstance(data[name], dict):
                self.rois[name] = {
                    "x": float(data[name].get("x", 0)),
                    "y": float(data[name].get("y", 0)),
                    "w": float(data[name].get("w", 0)),
                    "h": float(data[name].get("h", 0)),
                }
        self._ensure_default_rois()
        self._apply_rois_to_detector()
        self.redraw()
        self._set_status(f"ROI carregado de {os.path.basename(path)}.")

    def reset_current_roi(self):
        defaults = {
            "top_hud_unificado": {"x": 0.02, "y": 0.015, "w": 0.285, "h": 0.095},
            "banner": {"x": 0.02, "y": 0.77, "w": 0.96, "h": 0.16},
            "countdown_center": {"x": 0.38, "y": 0.06, "w": 0.22, "h": 0.08},
        }
        self.rois[self.current_roi_name.get()] = dict(defaults[self.current_roi_name.get()])
        self._apply_rois_to_detector()
        self.redraw()
        self._set_status("ROI atual resetado para o padrão.")


def main():
    root = tk.Tk()
    RoiHudTestApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
