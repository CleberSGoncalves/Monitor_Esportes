@echo off
cd /d "%~dp0"
echo [LIMPEZA] Encerrando instancias antigas do GUI...
powershell "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*main_gui.py*'} | Stop-Process -Force" 2>nul
echo Iniciando Monitor de Esportes...
call .venv\Scripts\activate
python gui/main_gui.py
echo.
echo Aplicacao encerrada.
pause
