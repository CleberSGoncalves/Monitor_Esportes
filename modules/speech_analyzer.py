from __future__ import annotations

import os
import subprocess
from typing import Optional


class SpeechAnalyzer:
    """
    Um único FFmpeg conectado ao SRT que pode:
    - salvar frames JPG em frames_dir
    - opcionalmente salvar áudio WAV segmentado em audio_dir

    Isso evita abrir 2 conexões SRT.
    """

    def __init__(
        self,
        input_url: str,
        audio_dir: str,
        frames_dir: str,
        segment_seconds: int = 60,
        sample_fps: int = 1,
        ffmpeg_path: str = "ffmpeg",
        loglevel: str = "info",
        force_caller_if_listener: bool = True,
        jpg_qv: int = 4,            # 2 melhor / 4 ok / 6 menor
        scale_width: int = 1280,    # ajuste se quiser aliviar CPU
        scale_height: int = 720,
    ):
        self.input_url = input_url
        self.audio_dir = audio_dir
        self.frames_dir = frames_dir
        self.segment_seconds = max(0, int(segment_seconds))
        self.sample_fps = max(1, int(sample_fps))
        self.ffmpeg_path = ffmpeg_path
        self.loglevel = loglevel
        self.force_caller_if_listener = bool(force_caller_if_listener)
        self.jpg_qv = int(jpg_qv)
        self.scale_width = int(scale_width)
        self.scale_height = int(scale_height)

        self.proc: Optional[subprocess.Popen] = None

    def _normalize_url(self) -> str:
        url = self.input_url.strip()
        if self.force_caller_if_listener and "srt://" in url and "mode=listener" in url:
            url = url.replace("mode=listener", "mode=caller")
        return url

    def start(self, event_id: str) -> None:
        os.makedirs(self.frames_dir, exist_ok=True)

        if self.segment_seconds > 0:
            os.makedirs(self.audio_dir, exist_ok=True)

        self.stop()

        input_url = self._normalize_url()

        audio_pattern = os.path.join(self.audio_dir, f"{event_id}_%04d.wav")
        frame_pattern = os.path.join(self.frames_dir, f"{event_id}_%Y%m%d_%H%M%S.jpg")

        vf_parts = [f"fps={self.sample_fps}"]
        if self.scale_width > 0 and self.scale_height > 0:
            vf_parts.append(f"scale={self.scale_width}:{self.scale_height}")
        vf = ",".join(vf_parts)

        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-loglevel", self.loglevel,
            "-y",
            "-i", input_url,

            # --- SAÍDA 1: FRAMES (sempre ativa) ---
            "-map", "0:v:0",
            "-an",
            "-vf", vf,
            "-q:v", str(self.jpg_qv),
            "-strftime", "1",
            frame_pattern,
        ]

        # --- SAÍDA 2: ÁUDIO (opcional) ---
        if self.segment_seconds > 0:
            cmd += [
                "-map", "0:a:0",
                "-vn",
                "-ac", "1",
                "-ar", "16000",
                "-f", "segment",
                "-segment_time", str(self.segment_seconds),
                "-reset_timestamps", "1",
                audio_pattern,
            ]
            print("[INFO] SpeechAnalyzer (ffmpeg) iniciando captura de FRAMES + ÁUDIO…")
        else:
            print("[INFO] SpeechAnalyzer (ffmpeg) iniciando captura de FRAMES apenas…")

        print("[DEBUG] ffmpeg cmd:", " ".join(cmd))

        self.proc = subprocess.Popen(cmd)

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        self.proc = None
        print("[OK] SpeechAnalyzer parado.")