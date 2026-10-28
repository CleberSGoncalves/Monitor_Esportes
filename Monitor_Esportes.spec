# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('E:\\desenvolvimento\\Monitor_Esportes\\.venv\\Lib\\site-packages\\customtkinter', 'customtkinter/'), ('config', 'config'), ('modules', 'modules'), ('core', 'core'), ('gui', 'gui'), ('templates', 'templates'), ('version.json', '.')]
binaries = []
hiddenimports = ['gui', 'gui.canais_live_mixin', 'gui.nba_events_mixin', 'canais_live_mixin', 'nba_events_mixin', 'obsws_python', 'websocket']
hiddenimports += collect_submodules('obsws_python')
hiddenimports += collect_submodules('yt_dlp')
hiddenimports += collect_submodules('reportlab')
hiddenimports += collect_submodules('google.genai')
hiddenimports += collect_submodules('paddleocr')
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['gui\\main_gui.py'],
    pathex=['E:\\desenvolvimento\\Monitor_Esportes', 'E:\\desenvolvimento\\Monitor_Esportes\\gui'],
    binaries=binaries,
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
