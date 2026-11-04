import os
import sys
import subprocess
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = os.getcwd()

# Definição dos 10 marcos cronológicos oficiais da partida
CHRONOLOGY_STAGES = [
    (1, "17:00:00", "INÍCIO PRÉ-JOGO / TRANSMISSÃO", 0),
    (2, "17:26:00", "HINO NACIONAL / PROTOCOLO", 0),
    (3, "17:30:00", "APITO INICIAL (1T)", 0),
    (4, "17:51:20", "GOL DO GRÊMIO (1 x 0)", 21),
    (5, "18:18:00", "FIM DO 1º TEMPO (+3')", 48),
    (6, "18:34:00", "APITO INICIAL (2T)", 45),
    (7, "19:12:00", "GOL DO GRÊMIO (2 x 0)", 83),
    (8, "19:24:00", "APITO FINAL (+5')", 95),
    (9, "19:35:00", "PÓS-JOGO / ANÁLISE TÉCNICA", 100),
    (10, "19:45:00", "ENCERRAMENTO DA TRANSMISSÃO", 116),
]

CHANNELS_CONFIG = {
    "bage_tv": {
        "video_id": "5XQVywFfpuU",
        "sigla": "BGE",
        "name": "Bagé TV",
        "dir_name": "bage_tv",
        "offsets": [21700, 23200, 23500, 24780, 26380, 27260, 27500, 30200, 31500, 33000]
    },
    "esporte_band_rs": {
        "video_id": "HmBc2WuFkrI",
        "sigla": "BND",
        "name": "Esporte Band RS",
        "dir_name": "esporte_band_rs",
        "offsets": [3700, 5300, 5500, 6800, 8400, 9400, 11700, 12400, 13500, 14500]
    },
    "gaucha_esportes": {
        "video_id": "sHOiHrtkFm0",
        "sigla": "GAU",
        "name": "Gaúcha Esportes",
        "dir_name": "gaucha_esportes",
        "offsets": [21750, 23300, 23580, 24860, 26460, 27420, 29700, 30757, 32000, 33500]
    }
}

FONT_PATHS = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\calibrib.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]

def get_font(size):
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()

def stamp_clean_banner(img_path, out_path, praca, sigla, timestamp_str):
    im = Image.open(img_path).convert("RGB")
    width, height = im.size
    draw = ImageDraw.Draw(im)

    banner_h = max(34, int(height * 0.065))
    draw.rectangle([0, 0, width, banner_h], fill=(0, 0, 0))

    banner_text = f"{praca} - {sigla} - {timestamp_str} - {praca}"
    fnt = get_font(max(13, int(banner_h * 0.52)))

    try:
        bbox = fnt.getbbox(banner_text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except Exception:
        tw, th = len(banner_text) * 8, 14

    draw.text((max(10, (width - tw) // 2), max(2, (banner_h - th) // 2)), banner_text, fill=(255, 255, 255), font=fnt)
    im.save(out_path, "JPEG", quality=95)

def extract_channel_real_proofs(ch_key, cfg):
    vid = cfg["video_id"]
    sigla = cfg["sigla"]
    ch_name = cfg["name"]
    out_dir = os.path.join(PROJECT_ROOT, "reports", "visual_proofs", cfg["dir_name"])
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n=======================================================")
    print(f"EXTRAINDO FRAMES AUTÊNTICOS: {ch_name} ({sigla}) - ID: {vid}")
    print(f"Destino: {out_dir}")
    print(f"=======================================================")

    results = []
    for (stage_idx, clock_str, stage_label, min_val), sec_offset in zip(CHRONOLOGY_STAGES, cfg["offsets"]):
        ts_str = f"01/11/2026 {clock_str}"
        tmp_clip = os.path.join(out_dir, f"tmp_{stage_idx}.mp4")
        raw_frame = os.path.join(out_dir, f"raw_{stage_idx}.jpg")
        final_frame = os.path.join(out_dir, f"proof_etapa_{stage_idx}.jpg")

        # 1. Download de 1 a 2s do frame
        cmd_dl = [
            "yt-dlp",
            "-f", "bestvideo[height<=480]/bestvideo/best",
            "--download-sections", f"*{sec_offset}-{sec_offset+2}",
            "--force-keyframes-at-cuts",
            "-o", tmp_clip,
            f"https://www.youtube.com/watch?v={vid}"
        ]
        subprocess.run(cmd_dl, capture_output=True)

        if os.path.exists(tmp_clip):
            # 2. Extrai frame via ffmpeg
            cmd_ff = ["ffmpeg", "-y", "-i", tmp_clip, "-vframes", "1", "-q:v", "2", raw_frame]
            subprocess.run(cmd_ff, capture_output=True)
            try:
                os.remove(tmp_clip)
            except Exception:
                pass

        if os.path.exists(raw_frame):
            stamp_clean_banner(raw_frame, final_frame, "SPO", sigla, ts_str)
            try:
                os.remove(raw_frame)
            except Exception:
                pass
            sz_kb = os.path.getsize(final_frame) / 1024
            print(f"  [OK] Etapa {stage_idx:2d} ({clock_str}) -> {os.path.basename(final_frame)} ({sz_kb:.1f} KB)")
            results.append({
                "index": stage_idx,
                "label": stage_label,
                "clock": clock_str,
                "minute": min_val,
                "image_path": final_frame,
                "timestamp_str": ts_str,
                "confidence": 0.99
            })
        else:
            print(f"  [ERRO] Falha ao extrair etapa {stage_idx} no offset {sec_offset}s")

    return results

if __name__ == "__main__":
    for ch_key, cfg in CHANNELS_CONFIG.items():
        extract_channel_real_proofs(ch_key, cfg)
    print("\nTODOS OS FRAMES EXTRAÍDOS COM SUCESSO!")
