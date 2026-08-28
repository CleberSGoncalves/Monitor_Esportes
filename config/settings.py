# config/settings.py
import os

CHANNEL_STREAMS_URL = "https://www.youtube.com/@CazeTV/streams"

POLL_SECONDS = 30
PREPARE_MINUTES_BEFORE = 10

# =========================
# Email / Relatorios (PDF)
# =========================
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
# Credenciais serao carregadas do google_ai.json se disponiveis ou via GUI
OPEN_OBS_MINUTES_BEFORE = 3
AUTO_MONITOR_WHEN_LIVE = True

# =========================
# SRT (OBS -> App)
# =========================
SRT_PORT = 6001
SRT_INPUT_URL = f"srt://127.0.0.1:{SRT_PORT}?mode=listener&latency=200000"


# =========================
# OBS WebSocket (Windows local)
# =========================
OBS_HOST = "127.0.0.1"
OBS_PORT = 4456
OBS_PASSWORD = "mdna1234"

OBS_SCENE_MONITOR = "MONITOR"
OBS_BROWSER_SOURCE = "YT_BROWSER"
# =========================
# Captura
# =========================
FRAME_SAMPLE_FPS = 3
AUDIO_SEGMENT_SECONDS = 20
ENABLE_AUDIO_ANALYSIS = False

# =========================
# Pastas (ABSOLUTAS p/ não salvar em lugar errado)
# =========================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR    = os.path.join(PROJECT_ROOT, "data")
LOGS_DIR    = os.path.join(DATA_DIR, "logs")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
FRAMES_DIR  = os.path.join(DATA_DIR, "frames")
DEBUG_TEMPLATES_DIR = os.path.join(DATA_DIR, "debug_templates")
AUDIO_DIR   = os.path.join(DATA_DIR, "audio")

# =========================
# Auto-start OBS
# =========================
OBS_AUTO_START = True
OBS_EXE_PATH = r"E:\OBS\obs-studio\bin\64bit\obs64.exe"
OBS_ARGS = []

# (RTMP não será usado nessa opção)
RTMP_INPUT_URL = ""
VIDEO_SOURCE = ""

PREPARE_MINUTES_BEFORE = 10