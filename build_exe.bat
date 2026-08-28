@echo off
echo [BUILD] Iniciando geracao do executavel Monitor_Esportes...

if exist .venv\Scripts\activate.bat (
    echo [BUILD] Ativando ambiente virtual venv...
    call .venv\Scripts\activate.bat
) else (
    echo [BUILD] Aviso: Ambiente virtual venv nao localizado. Usando Python global.
)

set PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

call pyinstaller --noconfirm --distpath dist Monitor_Esportes.spec

if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha ao gerar o executavel.
    pause
    exit /b %ERRORLEVEL%
)

echo [COPY] Copiando pastas de recursos necessarios para 'dist'...
xcopy /E /I /Y config dist\config
xcopy /E /I /Y templates dist\templates
if exist templates_auto xcopy /E /I /Y templates_auto dist\templates_auto

echo.
echo [OK] Executavel gerado com sucesso na pasta 'dist'.
pause
