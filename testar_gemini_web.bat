@echo off
title Testar Gemini Web - Monitor de Esportes
cd /d "%~dp0"
echo ==========================================================
echo       TESTE DE CONSULTA HEADLESS NO GEMINI WEB
echo ==========================================================
echo.
if exist "Monitor_Esportes.exe" (
    "Monitor_Esportes.exe" --test-gemini
) else if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "from modules.web_verdict_collector import get_web_verdict; print(get_web_verdict('Vasco', 'Remo', '10/10/2026', 'Brasileirão Série A'))"
    pause
) else (
    python -c "from modules.web_verdict_collector import get_web_verdict; print(get_web_verdict('Vasco', 'Remo', '10/10/2026', 'Brasileirão Série A'))"
    pause
)
