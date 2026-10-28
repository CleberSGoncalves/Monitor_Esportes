# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['obsws_python', 'websocket']
hiddenimports += collect_submodules('obsws_python')
hiddenimports += collect_submodules('yt_dlp')
hiddenimports += collect_submodules('reportlab')
hiddenimports += collect_submodules('google.genai')
hiddenimports += collect_submodules('paddleocr')


a = Analysis(
    ['gui\\main_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Python312\\Lib\\site-packages\\customtkinter', 'customtkinter/'), ('config', 'config'), ('modules', 'modules'), ('core', 'core'), ('templates', 'templates')],
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
