# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

a = Analysis(
    ['gui/main_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('modules', 'modules'),
        ('config', 'config'),
        ('data', 'data'),
        ('version.json', '.'),
    ],
    hiddenimports=[
        'modules',
        'modules.perf_logger',
        'modules.auto_updater',
        'modules.expert_assistant',
        'modules.report_generator',
        'modules.sharepoint_reporter',
        'modules.audited_games_manager',
        'customtkinter',
        'PIL',
        'cv2',
        'numpy',
        'requests',
    ],
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

