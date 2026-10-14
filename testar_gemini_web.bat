@echo off
title Testar Gemini Web - Monitor de Esportes
cd /d "%~dp0"
echo ==========================================================
echo       TESTE DE CONSULTA HEADLESS NO GEMINI WEB
echo ==========================================================
echo.
echo Consultando o Gemini Web em segundo plano...
echo Aguarde a janela de confirmacao na tela...
echo.
if exist "Monitor_Esportes.exe" (
    start /wait "" "Monitor_Esportes.exe" --test-gemini
) else if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "import ctypes; from modules.web_verdict_collector import get_web_verdict; r=get_web_verdict('Coritiba', 'Botafogo', '12/10/2026', 'Brasileirão Série A'); txt=r.get('verdict_text') or 'Sessao Google nao esta logada.'; ctypes.windll.user32.MessageBoxW(0, txt[:400], 'Monitor de Esportes - Teste Gemini Web', 0x40 if r else 0x30)"
) else (
    python -c "import ctypes; from modules.web_verdict_collector import get_web_verdict; r=get_web_verdict('Coritiba', 'Botafogo', '12/10/2026', 'Brasileirão Série A'); txt=r.get('verdict_text') or 'Sessao Google nao esta logada.'; ctypes.windll.user32.MessageBoxW(0, txt[:400], 'Monitor de Esportes - Teste Gemini Web', 0x40 if r else 0x30)"
)
echo.
echo ==========================================================
echo Teste concluido! Pressione qualquer tecla para encerrar...
pause >nul
