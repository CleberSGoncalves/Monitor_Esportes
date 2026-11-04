import yt_dlp
import json

channels = {
    'Bage TV': '5XQVywFfpuU',
    'Esporte Band RS': 'HmBc2WuFkrI',
    'Gaucha': 'hHoSwXKrkZw',
    'Gaucha Esportes': 'sHOiHrtkFm0'
}

ydl_opts = {'quiet': True, 'no_warnings': True}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    for name, vid in channels.items():
        info = ydl.extract_info(f'https://www.youtube.com/watch?v={vid}', download=False)
        print(f"=== {name} ({vid}) ===")
        print("duration:", info.get('duration'))
        print("release_timestamp:", info.get('release_timestamp'))
        print("upload_date:", info.get('upload_date'))
        print("live_status:", info.get('live_status'))
        print("description length:", len(info.get('description', '')))
        # Print first 200 chars of description
        desc_lines = [l for l in (info.get('description') or '').split('\n') if l.strip()]
        for l in desc_lines[:5]:
            safe_l = l.encode('ascii', 'replace').decode('ascii')
            print("  desc:", safe_l)
