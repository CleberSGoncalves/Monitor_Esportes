# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = [
    'obsws_python', 'websocket', 'email', 'email.mime', 'email.mime.multipart', 
    'email.mime.text', 'email.mime.base', 'email.encoders', 'flask', 'flask_cors', 
    'requests', 'paddleocr', 'paddlex', 'paddle', 'youtube_transcript_api', 'tkcalendar'
]
hiddenimports += collect_submodules('obsws_python')
hiddenimports += collect_submodules('yt_dlp')
hiddenimports += collect_submodules('reportlab')
hiddenimports += collect_submodules('google.genai')
hiddenimports += collect_submodules('email')
hiddenimports += collect_submodules('flask')
hiddenimports += collect_submodules('paddleocr')
hiddenimports += collect_submodules('youtube_transcript_api')
hiddenimports += collect_submodules('tkcalendar')

datas = [('config', 'config'), ('modules', 'modules'), ('core', 'core'), ('templates', 'templates')]
datas += collect_data_files('customtkinter')

a = Analysis(
    ['gui\\main_gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Monitor_Esportes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
