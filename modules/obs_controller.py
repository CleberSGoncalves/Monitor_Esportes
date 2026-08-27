from __future__ import annotations

import os
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from obsws_python import ReqClient


@dataclass
class ObsConn:
    host: str = "127.0.0.1"
    port: int = 4456
    password: str = ""


def normalize_transform(transform: dict, canvas_w: int, canvas_h: int) -> dict:
    t = dict(transform or {})

    bounds_type = t.get("boundsType", "OBS_BOUNDS_NONE")

    if bounds_type == "OBS_BOUNDS_NONE":
        t.pop("boundsWidth", None)
        t.pop("boundsHeight", None)
        t.pop("boundsAlignment", None)
    else:
        t["boundsWidth"] = max(float(t.get("boundsWidth", canvas_w)), 1.0)
        t["boundsHeight"] = max(float(t.get("boundsHeight", canvas_h)), 1.0)
        t["boundsAlignment"] = int(t.get("boundsAlignment", 5))

    t["alignment"] = int(t.get("alignment", 5))
    t["positionX"] = float(t.get("positionX", 0.0))
    t["positionY"] = float(t.get("positionY", 0.0))
    t["scaleX"] = float(t.get("scaleX", 1.0))
    t["scaleY"] = float(t.get("scaleY", 1.0))
    t["rotation"] = float(t.get("rotation", 0.0))
    return t


class ObsBootstrapper:
    def __init__(self, conn: ObsConn):
        self.conn = conn

    def clone_scene_only(
        self,
        ws: ReqClient,
        template_scene: str,
        template_source: str,
        slot_scene: str,
        slot_source: str,
        url: str = "",
        canvas_w: int = 1080,
        canvas_h: int = 720,
    ) -> None:
        scenes = {s["sceneName"] for s in ws.get_scene_list().scenes}
        if slot_scene not in scenes:
            try:
                ws.create_scene(slot_scene)
            except Exception as e:
                msg = str(e).lower()
                if "already exists" not in msg and "601" not in msg:
                    raise

        full_settings = {
            "url": url,
            "width": canvas_w,
            "height": canvas_h,
            "fps": 30,
            "shutdown": False,
            "restart_when_active": False,
            "reroute_audio": True,
            "webpage_control_level": 2,
            "css": "body { background-color: black; margin:0; overflow:hidden; } video { visibility: visible !important; width:100vw !important; height:100vh !important; object-fit:contain !important; }",
        }

        inputs = {i["inputName"] for i in ws.get_input_list().inputs}

        if slot_source not in inputs:
            ws.create_input(
                sceneName=slot_scene,
                inputName=slot_source,
                inputKind="browser_source",
                inputSettings=full_settings,
                sceneItemEnabled=True,
            )
        else:
            try:
                ws.get_scene_item_id(slot_scene, slot_source)
            except Exception:
                try:
                    ws.create_scene_item(slot_scene, slot_source, True)
                except Exception:
                    pass

            ws.set_input_settings(slot_source, full_settings, True)

        tpl_item_id = ws.get_scene_item_id(template_scene, template_source).scene_item_id
        tpl_transform = ws.get_scene_item_transform(
            template_scene,
            tpl_item_id
        ).scene_item_transform
        tpl_transform = normalize_transform(tpl_transform, canvas_w, canvas_h)

        slot_item_id = ws.get_scene_item_id(slot_scene, slot_source).scene_item_id
        ws.set_scene_item_transform(slot_scene, slot_item_id, tpl_transform)


class OBSController:
    def __init__(
        self,
        host: str,
        port: int,
        password: str,
        obs_exe_path: Optional[str] = None,
        obs_args: Optional[Sequence[str]] = None,
    ):
        self.conn = ObsConn(host=host, port=port, password=password)
        self.ws: Optional[ReqClient] = None
        self.bootstrap = ObsBootstrapper(self.conn)

        self.obs_exe_path = obs_exe_path
        self.obs_args = list(obs_args) if obs_args else []
        self._obs_proc: Optional[subprocess.Popen] = None

    def _find_obs_exe(self) -> Optional[str]:
        if self.obs_exe_path:
            p = Path(self.obs_exe_path)
            if p.exists():
                return str(p)

        hardcoded = Path(r"E:\OBS\obs-studio\bin\64bit\obs64.exe")
        if hardcoded.exists():
            return str(hardcoded)

        env = os.getenv("OBS_EXE_PATH")
        if env:
            p = Path(env)
            if p.exists():
                return str(p)

        candidates = [
            r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
            r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
            r"D:\Program Files\obs-studio\bin\64bit\obs64.exe",
            r"D:\OBS\obs-studio\bin\64bit\obs64.exe",
            r"E:\Program Files\obs-studio\bin\64bit\obs64.exe",
            r"E:\OBS\obs-studio\bin\64bit\obs64.exe",
            r"C:\Program Files\obs-studio\bin\32bit\obs32.exe",
        ]
        for c in candidates:
            if Path(c).exists():
                return c

        return None

    def _is_port_open(self, host: str, port: int, timeout_s: float = 0.5) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout_s):
                return True
        except OSError:
            return False

    def _kill_existing_obs(self) -> None:
        if os.name != "nt":
            return
        
        # v10.7: Limpar safe_mode/lock se existir para evitar popup de erro
        try:
            appdata = os.getenv("APPDATA")
            if appdata:
                obs_config = Path(appdata) / "obs-studio"
                for f_name in ["safe_mode", "obs_port"]: # Limpa locks conhecidos
                    f_path = obs_config / f_name
                    if f_path.exists():
                        f_path.unlink()
                        print(f"[INFO] Arquivo de lock '{f_name}' do OBS removido.")
        except Exception:
            pass

        try:
            subprocess.run(["taskkill", "/F", "/IM", "obs64.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            subprocess.run(["taskkill", "/F", "/IM", "obs32.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            time.sleep(2.0)
            print("[INFO] Instâncias antigas do OBS finalizadas agressivamente.")
        except Exception as e:
            print(f"[WARN] Falha ao finalizar OBS antigo: {e}")

    def _start_obs(self) -> None:
        exe = self._find_obs_exe()
        if not exe:
            raise RuntimeError(
                "Não consegui encontrar o executável do OBS. "
                "Defina OBS_EXE_PATH corretamente."
            )

        obs_dir = str(Path(exe).parent)

        cmd = [
            exe,
            "--launch-normal",
            "--disable-shutdown-check",
            "--skip-version-check",
            "--disable-browser-hw-acceleration",
            "--no-sandbox",
        ] + list(self.obs_args)

        startupinfo = None
        creationflags = 0

        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        self._obs_proc = subprocess.Popen(
            cmd,
            cwd=obs_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )

        print(f"[INFO] OBS iniciado: {exe}")
        time.sleep(12.0)

    def _connect_once(self, timeout: float = 10.0) -> ReqClient:
        ws = ReqClient(
            host=self.conn.host,
            port=self.conn.port,
            password=self.conn.password,
            timeout=timeout,
        )
        ws.get_version()
        return ws

    def _wait_ws_ready(self, timeout_s: float = 40.0, poll_s: float = 0.5) -> None:
        deadline = time.time() + timeout_s
        last_err: Optional[Exception] = None

        while time.time() < deadline:
            if not self._is_port_open(self.conn.host, self.conn.port, timeout_s=0.5):
                time.sleep(poll_s)
                continue

            try:
                ws = self._connect_once(timeout=10.0)
                ws.get_scene_list()
                self.ws = ws
                print(f"[OK] OBS conectado em {self.conn.host}:{self.conn.port}")
                return
            except Exception as e:
                last_err = e
                time.sleep(poll_s)

        raise RuntimeError(
            f"OBS abriu, mas o WebSocket não ficou pronto em "
            f"{self.conn.host}:{self.conn.port}. Último erro: {last_err}"
        )

    def connect(self, auto_start: bool = True, launch_timeout_s: float = 40.0) -> None:
        try:
            ws = self._connect_once(timeout=10.0)
            ws.get_scene_list()
            self.ws = ws
            print(f"[OK] OBS já estava conectado em {self.conn.host}:{self.conn.port}")
            return
        except Exception as e:
            self.ws = None
            print(f"[WARN] Não conectou no OBS WebSocket ({e}).")

        if not auto_start:
            raise RuntimeError("OBS não conectado e auto_start=False.")

        self._kill_existing_obs()
        self._start_obs()
        self._wait_ws_ready(timeout_s=launch_timeout_s)

    def disconnect(self) -> None:
        self.ws = None

    def set_program_scene(self, scene_name: str) -> None:
        if not self.ws:
            raise RuntimeError("OBS não conectado")
        self.ws.set_current_program_scene(scene_name)
        print(f"[OK] Cena de programa ajustada para: {scene_name}")

    def get_current_program_scene(self) -> Optional[str]:
        if not self.ws:
            return None
        try:
            data = self.ws.get_current_program_scene()
            return getattr(data, "current_program_scene_name", None)
        except Exception:
            return None

    def _virtual_cam_status(self):
        if not self.ws:
            raise RuntimeError("OBS não conectado")
        for name in ("get_virtual_cam_status", "get_virtualcam_status"):
            fn = getattr(self.ws, name, None)
            if fn:
                return fn()
        raise RuntimeError("Método de status da câmera virtual não disponível nessa versão do obsws-python")

    def is_virtual_camera_active(self) -> bool:
        try:
            status = self._virtual_cam_status()
            return bool(getattr(status, "output_active", False))
        except Exception:
            return False

    def start_virtual_camera(self, wait_s: float = 1.0) -> bool:
        if not self.ws:
            raise RuntimeError("OBS não conectado")
        if self.is_virtual_camera_active():
            print("[INFO] Virtual Camera já estava ativa.")
            return True

        for name in ("start_virtual_cam", "start_virtualcam"):
            fn = getattr(self.ws, name, None)
            if fn:
                try:
                    fn()
                    time.sleep(wait_s)
                    active = self.is_virtual_camera_active()
                    print(f"[OK] Virtual Camera start enviado | ativa={active}")
                    return active
                except Exception:
                    pass
        raise RuntimeError("Não foi possível iniciar a Virtual Camera via WebSocket")

    def stop_virtual_camera(self) -> bool:
        if not self.ws:
            return False
        if not self.is_virtual_camera_active():
            return True

        for name in ("stop_virtual_cam", "stop_virtualcam"):
            fn = getattr(self.ws, name, None)
            if fn:
                try:
                    fn()
                    time.sleep(0.3)
                    active = self.is_virtual_camera_active()
                    print(f"[OK] Virtual Camera stop enviado | ativa={active}")
                    return not active
                except Exception:
                    pass
        return False

    def ensure_virtual_camera_active(self, scene_name: Optional[str] = None, wait_s: float = 1.0) -> bool:
        if scene_name:
            self.set_program_scene(scene_name)
        if self.is_virtual_camera_active():
            return True
        return self.start_virtual_camera(wait_s=wait_s)

    def prepare_monitoring(
        self,
        watch_url: str,
        monitor_scene: str,
        browser_source: str,
        template_scene: str = "MONITOR",
        template_source: str = "YT_BROWSER",
        canvas_w: int = 1080,
        canvas_h: int = 720,
        ensure_virtual_cam: bool = True,
    ) -> None:
        if not self.ws:
            raise RuntimeError("OBS não conectado")

        self.bootstrap.clone_scene_only(
            ws=self.ws,
            template_scene=template_scene,
            template_source=template_source,
            slot_scene=monitor_scene,
            slot_source=browser_source,
            url=watch_url,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
        )

        self.set_program_scene(monitor_scene)
        self.force_browser_fullscreen(browser_source) # v10.4: Limpa chat/comentários e dá fullscreen
        if ensure_virtual_cam:
            self.ensure_virtual_camera_active(scene_name=monitor_scene, wait_s=1.0)
        print(f"[OK] OBS preparado: cena={monitor_scene} fonte={browser_source}")

    def start_streaming(self) -> None:
        if not self.ws:
            raise RuntimeError("OBS não conectado")

        try:
            status = self.ws.get_stream_status()
            if getattr(status, "output_active", False):
                print("[INFO] Stream já estava ativo.")
                return
        except Exception:
            pass

        try:
            self.ws.start_stream()
            print("[OK] Streaming iniciado.")
        except Exception as e:
            raise RuntimeError(f"Falha ao iniciar streaming no OBS: {e}") from e

    def stop_streaming(self) -> None:
        if not self.ws:
            return

        try:
            status = self.ws.get_stream_status()
            if not getattr(status, "output_active", False):
                return
        except Exception:
            pass

        try:
            self.ws.stop_stream()
            print("[OK] Streaming parado.")
        except Exception as e:
            print(f"[WARN] Falha ao parar streaming: {e}")

    def force_browser_fullscreen(self, source_name: str) -> None:
        """Injeta CSS para forçar o player de vídeo a ocupar 100% da fonte browser."""
        if not self.ws:
            return
        
        css = (
            "body { background-color: black; margin:0; overflow:hidden !important; } "
            "#chat, #chat-messages, ytd-live-chat-frame, #comments, #secondary { display: none !important; } "
            "video { visibility: visible !important; width:100vw !important; height:100vh !important; "
            "position: fixed !important; top:0 !important; left:0 !important; z-index: 999999 !important; "
            "object-fit: contain !important; }"
        )
        try:
            self.ws.set_input_settings(source_name, {"css": css}, True)
            print(f"[OK] Fullscreen forcado via CSS na fonte: {source_name}")
        except Exception as e:
            print(f"[WARN] Erro ao forcar fullscreen: {e}")

    def send_browser_hotkey(self, source_name: str, key_id: str) -> None:
        """Envia um atalho de teclado para uma fonte específica no OBS."""
        if not self.ws:
            return
        try:
            # OBS WebSocket 5.x usa PressInputKeyCombination
            self.ws.press_input_key_combination(source_name, key_id)
            print(f"[OK] Hotkey {key_id} enviada para {source_name}")
        except Exception as e:
            print(f"[WARN] Erro ao enviar hotkey {key_id} para {source_name}: {e}")

    def start_recording(self) -> None:
        if not self.ws: return
        try: self.ws.start_record()
        except Exception: pass

    def stop_recording(self) -> None:
        if not self.ws: return
        try: self.ws.stop_record()
        except Exception: pass

    def start_replay_buffer(self) -> None:
        if not self.ws: return
        try: self.ws.start_replay_buffer()
        except Exception: pass

    def save_replay_buffer(self) -> None:
        if not self.ws: return
        try: self.ws.save_replay_buffer()
        except Exception: pass
