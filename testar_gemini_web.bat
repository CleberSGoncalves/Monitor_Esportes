@echo off
title Testar Gemini Web - Monitor de Esportes
cd /d "%~dp0"
echo ==========================================================
echo       TESTE DE CONSULTA HEADLESS NO GEMINI WEB
echo ==========================================================
echo.
echo [1/2] Iniciando consulta ao Gemini Web em segundo plano...
echo       Aguarde a resposta (pode levar alguns segundos)...
echo.
if exist "Monitor_Esportes.exe" (
    "Monitor_Esportes.exe" --test-gemini
) else if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "from modules.web_verdict_collector import get_web_verdict; res=get_web_verdict('Vasco', 'Remo', '10/10/2026', 'Brasileirão Série A'); print('\nRESPOSTA:\n', res.get('verdict_text') or 'Sessao nao logada')"
) else (
    python -c "from modules.web_verdict_collector import get_web_verdict; res=get_web_verdict('Vasco', 'Remo', '10/10/2026', 'Brasileirão Série A'); print('\nRESPOSTA:\n', res.get('verdict_text') or 'Sessao nao logada')"
)
echo.
echo ==========================================================
echo Pressione qualquer tecla para encerrar...
pause >nul
