# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('E:\\desenvolvimento\\Monitor_Esportes\\.venv\\Lib\\site-packages\\customtkinter', 'customtkinter/'), ('config/audit_state.json', 'config'), ('config/auth.xml', 'config'), ('config/campeonatos_config.json', 'config'), ('config/cbf_broadcaster_rules.json', 'config'), ('config/cbf_fixtures_cache.json', 'config'), ('config/cbf_game_urls.json', 'config'), ('config/config.xml', 'config'), ('config/general_settings.json', 'config'), ('config/google_ai.json', 'config'), ('config/nba_audited_games.json', 'config'), ('config/nba_batch_uploaded.json', 'config'), ('config/nba_reprocess_list.json', 'config'), ('config/nba_visual_sync_done.json', 'config'), ('config/nba_visual_sync_v2_done.json', 'config'), ('config/relatorio_palmeiras_santos.pdf', 'config'), ('config/roi_cazetv.json', 'config'), ('config/roi_enabled_cazetv.json', 'config'), ('config/saved_emails.json', 'config'), ('config/scheduled_games.json', 'config'), ('config/secret.key', 'config'), ('config/settings.py', 'config'), ('config/sharepoint_events_cache.json', 'config'), ('config/sp_token_cache.json', 'config'), ('config/streaming_data.csv', 'config'), ('config/Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx', 'config'), ('config/temp_Brasileirão_Série_A.pdf', 'config'), ('config/temp_Copa_do_Brasil.pdf', 'config'), ('config/test_copa.pdf', 'config'), ('config/test_dummy.pdf', 'config'), ('config/youtube_channels.json', 'config'), ('modules', 'modules'), ('core', 'core'), ('gui', 'gui'), ('templates', 'templates'), ('data.csv', '.'), ('Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx', '.'), ('version.json', '.')]
binaries = []
hiddenimports = ['gui', 'gui.canais_live_mixin', 'gui.nba_events_mixin', 'gui.reporte_eventos_mixin', 'gui.sharepoint_auth_modal', 'canais_live_mixin', 'nba_events_mixin', 'reporte_eventos_mixin', 'sharepoint_auth_modal', 'obsws_python', 'websocket', 'pdfplumber', 'pymupdf', 'fitz', 'pypdfium2', 'openpyxl', 'selenium', 'webdriver_manager', 'pygetwindow', 'amazoncaptcha', 'tkcalendar', 'modules.nba_autonomous_auditor', 'modules.nba_visual_proof_service', 'modules.nba_report_generator', 'modules.sharepoint_youtube_reporter', 'modules.reporte_eventos']
hiddenimports += collect_submodules('selenium')
hiddenimports += collect_submodules('webdriver_manager')
hiddenimports += collect_submodules('pygetwindow')
hiddenimports += collect_submodules('amazoncaptcha')
hiddenimports += collect_submodules('obsws_python')
hiddenimports += collect_submodules('yt_dlp')
hiddenimports += collect_submodules('reportlab')
hiddenimports += collect_submodules('google.genai')
hiddenimports += collect_submodules('paddleocr')
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pdfplumber')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('fitz')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pypdfium2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('tkcalendar')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('cryptography')
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
    excludes=['google.genai.tests', 'pytest', 'tests'],
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
