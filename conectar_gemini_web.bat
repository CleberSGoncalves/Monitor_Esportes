@echo off
title Conectar Gemini Web - Monitor de Esportes
cd /d "%~dp0"
echo ==========================================================
echo   CONECTAR SESSAO GOOGLE NO GEMINI WEB (PLAYWRIGHT)
echo ==========================================================
echo.
echo Uma janela do navegador sera aberta para voce fazer login
echo na sua Conta Google no Gemini (gemini.google.com).
echo.
echo O login precisa ser feito apenas UMA VEZ.
echo A sessao ficara salva no perfil dedicado para coletas headless.
echo.
echo Pressione qualquer tecla para abrir o navegador...
pause >nul
if exist "Monitor_Esportes.exe" (
    "Monitor_Esportes.exe" --login-gemini
) else if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m modules.web_verdict_collector --login
) else (
    python -m modules.web_verdict_collector --login
)
echo.
echo Pressione qualquer tecla para encerrar...
pause >nul
