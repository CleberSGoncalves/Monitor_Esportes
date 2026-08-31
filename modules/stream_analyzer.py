from __future__ import annotations

import os
import queue
import subprocess
import threading
import time
from typing import Callable, Optional

import cv2
import numpy as np


class StreamAnalyzer:
    """
    Captura frames de duas formas, mantendo a mesma interface pública:
    - SRT/FFmpeg (legado)
    - OBS Virtual Camera / webcam via OpenCV

    Compatibilidade:
    - Continua aceitando o parâmetro `srt_url`.
    - Se `source_mode="auto"`, escolhe câmera virtual quando:
        * srt_url começa com "camera://", "device://", "obsvcam://", "virtualcam://"
        * OU a env STREAM_SOURCE_MODE = "virtual_camera"
    - Caso contrário usa o fluxo SRT legado.

    Exemplos:
        StreamAnalyzer("camera://5", width=1920, height=1080, sample_fps=1)
        StreamAnalyzer("obsvcam://5", width=1920, height=1080, sample_fps=1)
        StreamAnalyzer(SRT_INPUT_URL, width=1280, height=720, sample_fps=1)

    Variáveis de ambiente úteis:
        STREAM_SOURCE_MODE=virtual_camera
        OBS_VCAM_INDEX=5
        OBS_VCAM_BACKEND=CAP_DSHOW
        OBS_VCAM_WIDTH=1920
        OBS_VCAM_HEIGHT=1080
    """

    def __init__(
        self,
        srt_url: str,
        width: int = 1280,
        height: int = 720,
        sample_fps: int = 1,
        ffmpeg_path: str = "ffmpeg",
        force_caller_if_listener: bool = True,
        loglevel: str = "warning",
        max_queue_size: int = 2,
        stderr_callback: Optional[Callable[[str], None]] = None,
        source_mode: str = "auto",
        camera_index: Optional[int] = None,
        camera_backend: str = "CAP_DSHOW",
        reconnect_delay_s: float = 1.0,
        camera_probe_max_index: int = 10,
        camera_fail_threshold: int = 20,
    ):
        self.srt_url = srt_url
        self.width = int(width)
        self.height = int(height)
        self.sample_fps = max(1, int(sample_fps))
        self.ffmpeg_path = ffmpeg_path
        self.force_caller_if_listener = bool(force_caller_if_listener)
        self.loglevel = str(loglevel or "warning")
        self.max_queue_size = max(1, int(max_queue_size))
        self.stderr_callback = stderr_callback

        self.source_mode = str(source_mode or "auto").strip().lower()
        self.reconnect_delay_s = max(0.2, float(reconnect_delay_s))
        self.camera_probe_max_index = max(0, int(camera_probe_max_index))
        self.camera_fail_threshold = max(3, int(camera_fail_threshold))

        self.camera_backend_name = self._resolve_backend_name(camera_backend)
        self.camera_backend = self._resolve_backend_value(self.camera_backend_name)

        env_camera_index = os.getenv("OBS_VCAM_INDEX", "").strip()
        if camera_index is None and env_camera_index:
            try:
                camera_index = int(env_camera_index)
            except Exception:
                pass
        self.camera_index = camera_index

        self.proc: Optional[subprocess.Popen] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False

        self.callback: Optional[Callable] = None

        self.frame_queue: "queue.Queue[tuple[np.ndarray, float]]" = queue.Queue(maxsize=self.max_queue_size)

        self.reader_thread: Optional[threading.Thread] = None
        self.dispatch_thread: Optional[threading.Thread] = None
        self.stderr_thread: Optional[threading.Thread] = None

        self.frames_received = 0
        self.frames_dispatched = 0
        self.frames_dropped = 0
        self.frames_failed = 0
        self.reconnects = 0

        self._last_camera_frame_t = 0.0
        self._selected_mode = "srt"
        self._camera_opened_width = 0
        self._camera_opened_height = 0

    # =========================================================
    # Modo / parsing
    # =========================================================

    def _resolve_backend_name(self, value: str) -> str:
        raw = str(value or os.getenv("OBS_VCAM_BACKEND", "CAP_DSHOW")).strip().upper()
        if not raw.startswith("CAP_"):
            raw = f"CAP_{raw}"
        return raw

    def _resolve_backend_value(self, name: str) -> int:
        return int(getattr(cv2, name, getattr(cv2, "CAP_DSHOW", 700)))

    def _camera_width(self) -> int:
        env = os.getenv("OBS_VCAM_WIDTH", "").strip()
        if env:
            try:
                return int(env)
            except Exception:
                pass
        return self.width

    def _camera_height(self) -> int:
        env = os.getenv("OBS_VCAM_HEIGHT", "").strip()
        if env:
            try:
                return int(env)
            except Exception:
                pass
        return self.height

    def _normalize_url(self) -> str:
        url = (self.srt_url or "").strip()

        if (
            self.force_caller_if_listener
            and "srt://" in url
            and "mode=listener" in url
        ):
            url = url.replace("mode=listener", "mode=caller")

        return url

    def _choose_mode(self) -> str:
        env_mode = os.getenv("STREAM_SOURCE_MODE", "").strip().lower()
        if env_mode in {"virtual_camera", "camera", "opencv"}:
            return "virtual_camera"
        if self.source_mode in {"virtual_camera", "camera", "opencv"}:
            return "virtual_camera"
        if self.source_mode in {"srt", "ffmpeg"}:
            return "srt"

        url = (self.srt_url or "").strip().lower()
        if url.startswith(("camera://", "device://", "obsvcam://", "virtualcam://")):
            return "virtual_camera"
        return "srt"

    def _extract_camera_index_from_url(self) -> Optional[int]:
        raw = (self.srt_url or "").strip()
        prefixes = ("camera://", "device://", "obsvcam://", "virtualcam://")
        for prefix in prefixes:
            if raw.lower().startswith(prefix):
                tail = raw[len(prefix):].strip()
                try:
                    return int(tail)
                except Exception:
                    return None
        return None

    # =========================================================
    # Start/stop
    # =========================================================

    def start(self, frame_callback: Callable) -> None:
        self.stop()

        self.callback = frame_callback
        self.frames_received = 0
        self.frames_dispatched = 0
        self.frames_dropped = 0
        self.frames_failed = 0
        self.reconnects = 0
        self._last_camera_frame_t = 0.0
        self._camera_opened_width = 0
        self._camera_opened_height = 0

        self._selected_mode = self._choose_mode()

        if self._selected_mode == "virtual_camera":
            self._start_camera_mode()
        else:
            self._start_srt_mode()

    def stop(self) -> None:
        self.running = False

        try:
            while not self.frame_queue.empty():
                self.frame_queue.get_nowait()
        except Exception:
            pass

        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass

        self.proc = None

        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        self.cap = None

        self.reader_thread = None
        self.dispatch_thread = None
        self.stderr_thread = None

    def _start_srt_mode(self) -> None:
        input_url = self._normalize_url()

        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-loglevel", self.loglevel,
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-analyzeduration", "1000000",
            "-probesize", "1000000",
            "-i", input_url,
            "-an",
            "-sn",
            "-dn",
            "-vf", f"fps={self.sample_fps},scale={self.width}:{self.height}",
            "-pix_fmt", "bgr24",
            "-f", "rawvideo",
            "-",
        ]

        print("[STREAM] modo=srt | ffmpeg cmd:", " ".join(cmd))

        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8,
        )

        self.running = True

        self.reader_thread = threading.Thread(target=self._reader_loop_ffmpeg, daemon=True, name="ffmpeg_reader")
        self.dispatch_thread = threading.Thread(target=self._dispatch_loop, daemon=True, name="ffmpeg_dispatch")
        self.stderr_thread = threading.Thread(target=self._stderr_loop, daemon=True, name="ffmpeg_stderr")

        self.reader_thread.start()
        self.dispatch_thread.start()
        self.stderr_thread.start()

    def _start_camera_mode(self) -> None:
        chosen_index = self.camera_index
        url_index = self._extract_camera_index_from_url()
        if chosen_index is None and url_index is not None:
            chosen_index = url_index

        if chosen_index is None:
            chosen_index = self._probe_camera_index()
            self.camera_index = chosen_index

        if chosen_index is None:
            raise RuntimeError(
                "Não foi possível encontrar a OBS Virtual Camera. "
                "Defina camera_index explicitamente (ex: camera://5 ou OBS_VCAM_INDEX=5)."
            )

        print(
            f"[STREAM] modo=virtual_camera | index={chosen_index} "
            f"backend={self.camera_backend_name} requested={self._camera_width()}x{self._camera_height()} "
            f"fps_sample={self.sample_fps}"
        )

        self.cap = self._open_camera_capture(chosen_index)
        self.running = True

        self.reader_thread = threading.Thread(target=self._reader_loop_camera, daemon=True, name="camera_reader")
        self.dispatch_thread = threading.Thread(target=self._dispatch_loop, daemon=True, name="camera_dispatch")

        self.reader_thread.start()
        self.dispatch_thread.start()

    # =========================================================
    # Camera helpers
    # =========================================================

    def _open_camera_capture(self, camera_index: int) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(int(camera_index), self.camera_backend)
        if not cap.isOpened():
            raise RuntimeError(
                f"Falha ao abrir câmera idx={camera_index} backend={self.camera_backend_name}"
            )

        requested_w = self._camera_width()
        requested_h = self._camera_height()

        if requested_w > 0:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(requested_w))
        if requested_h > 0:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(requested_h))
        cap.set(cv2.CAP_PROP_FPS, 30.0)

        time.sleep(0.4)

        self._camera_opened_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        self._camera_opened_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        print(
            f"[STREAM] câmera aberta | idx={camera_index} backend={self.camera_backend_name} "
            f"real={self._camera_opened_width}x{self._camera_opened_height}"
        )
        return cap

    def _probe_camera_index(self) -> Optional[int]:
        print("[STREAM] sondando índice da câmera virtual...")
        best_score = None
        best_index = None

        for idx in range(self.camera_probe_max_index + 1):
            cap = None
            try:
                cap = cv2.VideoCapture(idx, self.camera_backend)
                if not cap.isOpened():
                    continue

                time.sleep(0.4)

                brightness_vals = []
                diff_vals = []
                prev_gray = None
                frames_ok = 0

                for _ in range(12):
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        time.sleep(0.03)
                        continue

                    frames_ok += 1
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    brightness_vals.append(float(gray.mean()))

                    if prev_gray is not None:
                        diff_vals.append(float(np.mean(cv2.absdiff(prev_gray, gray))))
                    prev_gray = gray
                    time.sleep(0.03)

                if frames_ok == 0:
                    continue

                avg_brightness = float(np.mean(brightness_vals)) if brightness_vals else 0.0
                avg_diff = float(np.mean(diff_vals)) if diff_vals else 0.0
                non_black_ratio = float(np.mean(prev_gray > 10)) if prev_gray is not None else 0.0

                score = (
                    round(non_black_ratio, 4),
                    round(avg_brightness, 2),
                    round(avg_diff, 3),
                    frames_ok,
                )
                print(
                    f"[STREAM][PROBE] idx={idx} score={score} "
                    f"bright={avg_brightness:.2f} diff={avg_diff:.3f} non_black={non_black_ratio:.4f}"
                )

                if best_score is None or score > best_score:
                    best_score = score
                    best_index = idx

            except Exception as e:
                print(f"[STREAM][WARN] probe idx={idx}: {e}")
            finally:
                if cap is not None:
                    cap.release()

        if best_index is not None:
            print(f"[STREAM] índice escolhido automaticamente: {best_index}")
        return best_index

    # =========================================================
    # Loops
    # =========================================================

    def _reader_loop_ffmpeg(self) -> None:
        frame_size = self.width * self.height * 3

        while self.running and self.proc and self.proc.stdout:
            try:
                raw = self.proc.stdout.read(frame_size)

                if not raw or len(raw) != frame_size:
                    if self.proc.poll() is not None:
                        break
                    time.sleep(0.01)
                    continue

                frame = np.frombuffer(raw, np.uint8).reshape(
                    (self.height, self.width, 3)
                ).copy()

                self.frames_received += 1
                item = (frame, time.time())

                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                        self.frames_dropped += 1
                    except queue.Empty:
                        pass

                self.frame_queue.put_nowait(item)

            except Exception as e:
                print(f"[STREAM][ERRO] reader_loop_ffmpeg: {e}")
                time.sleep(0.05)

    def _reader_loop_camera(self) -> None:
        assert self.cap is not None
        frame_interval = 1.0 / max(1, self.sample_fps)
        last_emit_t = 0.0
        consecutive_failures = 0

        while self.running:
            cap = self.cap
            if cap is None:
                time.sleep(self.reconnect_delay_s)
                self._reopen_camera()
                continue

            try:
                t_read_0 = time.perf_counter()
                ok, frame = cap.read()
                read_ms = (time.perf_counter() - t_read_0) * 1000.0
                
                if not ok or frame is None:
                    self.frames_failed += 1
                    consecutive_failures += 1
                    if consecutive_failures >= self.camera_fail_threshold:
                        print(
                            f"[STREAM][WARN] câmera sem frames por {consecutive_failures} leituras; "
                            f"tentando reabrir..."
                        )
                        self._reopen_camera()
                        consecutive_failures = 0
                    else:
                        time.sleep(0.02)
                    continue

                consecutive_failures = 0
                now = time.time()
                self._last_camera_frame_t = now

                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_AREA)

                if (now - last_emit_t) < frame_interval:
                    continue

                # Diagnóstico periódico (a cada 30 frames)
                if self.frames_received % 30 == 0:
                    print(f"[STREAM][DIAG] read_ms={read_ms:.1f} | interval={(now-last_emit_t)*1000.0:.1f}ms")

                last_emit_t = now
                self.frames_received += 1
                item = (frame.copy(), now)

                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                        self.frames_dropped += 1
                    except queue.Empty:
                        pass

                self.frame_queue.put_nowait(item)

            except Exception as e:
                print(f"[STREAM][ERRO] reader_loop_camera: {e}")
                time.sleep(0.05)

    def _reopen_camera(self) -> None:
        if not self.running:
            return

        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        self.cap = None

        self.reconnects += 1
        time.sleep(self.reconnect_delay_s)

        try:
            if self.camera_index is None:
                self.camera_index = self._probe_camera_index()
            if self.camera_index is None:
                raise RuntimeError("camera_index indefinido")
            self.cap = self._open_camera_capture(self.camera_index)
        except Exception as e:
            print(f"[STREAM][WARN] falha ao reabrir câmera: {e}")
            time.sleep(self.reconnect_delay_s)

    def _dispatch_loop(self) -> None:
        while self.running:
            try:
                frame, ts = self.frame_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                if self.callback:
                    self.callback(frame, ts)
                    self.frames_dispatched += 1
            except Exception as e:
                print(f"[STREAM][ERRO] dispatch_loop: {e}")

    def _stderr_loop(self) -> None:
        if not self.proc or not self.proc.stderr:
            return

        while self.running and self.proc and self.proc.stderr:
            try:
                line = self.proc.stderr.readline()
                if not line:
                    if self.proc.poll() is not None:
                        break
                    time.sleep(0.05)
                    continue

                msg = line.decode("utf-8", errors="ignore").strip()
                if not msg:
                    continue

                print(f"[FFMPEG] {msg}")
                if self.stderr_callback:
                    try:
                        self.stderr_callback(msg)
                    except Exception:
                        pass

            except Exception:
                time.sleep(0.05)
