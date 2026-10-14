@echo off
title Conectar Gemini Web - Monitor de Esportes
cd /d "%~dp0"
echo ==========================================================
echo   CONECTAR SESSAO GOOGLE NO GEMINI WEB (PLAYWRIGHT)
echo ==========================================================
echo.
echo Uma janela do navegador sera aberta agora.
echo Faca login com seu e-mail e senha da Conta Google.
echo.
echo Apos logar com sucesso, feche a janela do navegador.
echo.
echo Pressione qualquer tecla para abrir o navegador...
pause >nul
if exist "Monitor_Esportes.exe" (
    start /wait "" "Monitor_Esportes.exe" --login-gemini
) else if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m modules.web_verdict_collector --login
) else (
    python -m modules.web_verdict_collector --login
)
echo.
echo ==========================================================
echo Sessao salva! Pressione qualquer tecla para encerrar...
pause >nul
