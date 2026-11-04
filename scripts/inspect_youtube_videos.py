import yt_dlp

videos = {
    'Bage TV': '5XQVywFfpuU',
    'Esporte Band RS': 'HmBc2WuFkrI',
    'Gaucha': 'hHoSwXKrkZw',
    'Gaucha Esportes': 'sHOiHrtkFm0'
}

ydl_opts = {'quiet': True, 'no_warnings': True}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    for name, vid in videos.items():
        try:
            info = ydl.extract_info(f'https://www.youtube.com/watch?v={vid}', download=False)
            dur = info.get('duration') or 0
            print(f'{name} ({vid}): Title="{info.get("title")}", Duration={dur}s ({dur/3600:.2f}h)')
        except Exception as e:
            print(f'Error for {name}: {e}')
