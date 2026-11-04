import subprocess
import os

channels = {
    'Band_RS': ('HmBc2WuFkrI', 8833),    # 18:26
    'Bage_TV': ('5XQVywFfpuU', 22831),   # 18:26
    'Gaucha': ('hHoSwXKrkZw', 23324)     # 18:26
}

out_dir = 'reports/test_frames_channels'
os.makedirs(out_dir, exist_ok=True)

for name, (vid, offset) in channels.items():
    print(f"Obtendo URL do stream para {name} ({vid})...")
    res = subprocess.run(
        ['yt-dlp', '-f', 'bestvideo[height<=720]/best[height<=720]/best', '-g', f'https://www.youtube.com/watch?v={vid}'],
        capture_output=True, text=True
    )
    stream_url = res.stdout.strip().split('\n')[0]
    if not stream_url:
        print(f"Erro ao obter URL para {name}: {res.stderr}")
        continue
    
    out_file = os.path.join(out_dir, f"{name}_1826.jpg")
    print(f"Extraindo frame no offset {offset}s para {out_file}...")
    ff_cmd = [
        'ffmpeg', '-ss', str(offset), '-i', stream_url,
        '-vframes', '1', '-q:v', '2', '-y', out_file
    ]
    subprocess.run(ff_cmd, capture_output=True)
    if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
        print(f"OK! Frame salvo: {out_file} ({os.path.getsize(out_file)} bytes)")
    else:
        print(f"Falha ao extrair frame de {name}")
