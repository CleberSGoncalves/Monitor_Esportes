@echo off
echo [LIMPEZA] Encerrando instancias antigas...
powershell "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*headless_server.py*'} | Stop-Process -Force" 2>nul
timeout /t 2 >nul
echo [INICIO] Iniciando Monitor Esportes Dashboard (Modo Headless)...
cd /d "E:\desenvolvimento\Monitor_Esportes"
C:\Python312\python.exe headless_server.py
pause
