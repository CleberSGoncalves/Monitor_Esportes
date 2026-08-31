@echo off
setlocal
echo ======================================================
echo   MODO INDEPENDENTE: MONITOR + REACT (HEADLESS)
echo ======================================================
echo.

echo [0/3] Liberando portas (limpeza de segurança)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 2^>nul') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000 2^>nul') do taskkill /F /PID %%a 2>nul

echo [1/3] Iniciando MOTOR Python em background...
start "MDNA_CORE" cmd /k "python headless_server.py"

echo [2/3] Preparando Dashboard React...
cd /d "%~dp0monitor-frontend"
start "MDNA_REACT" cmd /k "npm run dev"

echo [3/3] Aguardando inicializacao (12s)...
timeout /t 12 /nobreak

echo Abrindo Dashboard no navegador...
start http://localhost:5173

echo.
echo ------------------------------------------------------
echo TUDO PRONTO! O React agora e independente.
echo.
echo DICA: Se aparecer "AGUARDANDO SINAL", va na aba 
echo YouTube do Dashboard, selecione uma live e clique
echo em INICIAR (no topo da tela).
echo ------------------------------------------------------
echo.
pause
