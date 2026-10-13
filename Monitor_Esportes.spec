# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import glob
import site
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Coleta completa do numpy (datas, binaries e hiddenimports)
np_datas, np_binaries, np_hidden = collect_all('numpy')

# Localizar e incluir explicitamente as bibliotecas dinâmicas do numpy e openblas
extra_binaries = list(np_binaries)
for sp in site.getsitepackages():
    for lib_dir in ['numpy.libs', 'scipy.libs']:
        full_dir = os.path.join(sp, lib_dir)
        if os.path.exists(full_dir):
            for dll_path in glob.glob(os.path.join(full_dir, '*.dll')):
                extra_binaries.append((dll_path, lib_dir))
                extra_binaries.append((dll_path, '.'))

# Playwright (coletor de horários via navegador): inclui driver node e pacotes
pw_datas, pw_binaries, pw_hidden = collect_all('playwright')
extra_binaries += list(pw_binaries)

a = Analysis(
    ['gui/main_gui.py'],
    pathex=['.'],
    binaries=extra_binaries,
    datas=[
        ('modules', 'modules'),
        ('config', 'config'),
        ('data', 'data'),
        ('version.json', '.'),
    ] + np_datas + pw_datas,
    hiddenimports=[
        'modules',
        'modules.web_verdict_collector',
        'modules.perf_logger',
        'modules.auto_updater',
        'modules.expert_assistant',
        'modules.report_generator',
        'modules.sharepoint_reporter',
        'modules.audited_games_manager',
        'modules.autonomous_auditor',
        'modules.cbf_schedule_fetcher',
        'customtkinter',
        'PIL',
        'cv2',
        'numpy',
        'requests',
        'fitz',
        'pymupdf',
    ] + np_hidden + pw_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',
        'torchvision',
        'scipy',
        'matplotlib',
        'botocore',
        'boto3',
        'openpyxl',
        'sklearn',
        'skimage',
        'sqlalchemy',
        'IPython',
        'notebook',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Monitor_Esportes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
