import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd):
    print(f"Executando: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Erro ao executar comando (código {result.returncode})")
        sys.exit(result.returncode)

def main():
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)

    print(f"Diretório raiz do projeto: {project_root}")

    # Verificar se o venv está ativo ou usar o caminho do venv
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        print("Erro: .venv não encontrado.")
        sys.exit(1)

    # Obter caminho do customtkinter diretamente do ambiente .venv
    output = subprocess.check_output(
        [str(venv_python), "-c", "import customtkinter; print(customtkinter.__path__[0])"],
        text=True
    ).strip()
    ctk_path = Path(output)

    print(f"CustomTkinter encontrado em: {ctk_path}")

    # Definir argumentos do PyInstaller
    entry_point = "gui/main_gui.py"
    app_name = "Monitor_Esportes"
    
    # Montar o comando
    # --onefile: cria um único executável (mais lento no boot, mas mais limpo)
    # --noconsole: não abre janela de terminal
    # --add-data: inclui pastas e arquivos necessários
    
    # Coletar apenas arquivos de configuração essenciais de config/ (ignorando TempProfile e caches)
    config_datas = []
    config_dir = project_root / "config"
    for item in config_dir.iterdir():
        if item.is_file() and not item.name.endswith(".part"):
            config_datas.append(f"--add-data=\"config/{item.name};config\"")

    cmd = [
        str(project_root / ".venv" / "Scripts" / "pyinstaller"),
        "--noconsole",
        "--onefile",
        f"--name={app_name}",
        f"--paths={project_root}",
        f"--paths={project_root / 'gui'}",
        f"--add-data=\"{ctk_path};customtkinter/\"",
    ] + config_datas + [
        f"--add-data=\"modules;modules\"",
        f"--add-data=\"core;core\"",
        f"--add-data=\"gui;gui\"",
        f"--add-data=\"templates;templates\"",
        f"--add-data=\"data.csv;.\"",
        f"--add-data=\"Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx;.\"",
        f"--add-data=\"version.json;.\"",
        # Hidden imports and submodules
        "--hidden-import=gui",
        "--hidden-import=gui.canais_live_mixin",
        "--hidden-import=gui.nba_events_mixin",
        "--hidden-import=gui.reporte_eventos_mixin",
        "--hidden-import=gui.sharepoint_auth_modal",
        "--hidden-import=canais_live_mixin",
        "--hidden-import=nba_events_mixin",
        "--hidden-import=reporte_eventos_mixin",
        "--hidden-import=sharepoint_auth_modal",
        "--hidden-import=obsws_python",
        "--hidden-import=websocket",
        "--hidden-import=pdfplumber",
        "--hidden-import=pymupdf",
        "--hidden-import=fitz",
        "--hidden-import=pypdfium2",
        "--hidden-import=openpyxl",
        "--hidden-import=selenium",
        "--hidden-import=webdriver_manager",
        "--hidden-import=pygetwindow",
        "--hidden-import=amazoncaptcha",
        "--hidden-import=tkcalendar",
        "--hidden-import=modules.nba_autonomous_auditor",
        "--hidden-import=modules.nba_visual_proof_service",
        "--hidden-import=modules.nba_report_generator",
        "--hidden-import=modules.sharepoint_youtube_reporter",
        "--hidden-import=modules.reporte_eventos",
        "--collect-submodules=selenium",
        "--collect-submodules=webdriver_manager",
        "--collect-submodules=pygetwindow",
        "--collect-submodules=amazoncaptcha",
        "--collect-all=numpy",
        "--collect-all=pdfplumber",
        "--collect-all=fitz",
        "--collect-all=pypdfium2",
        "--collect-all=openpyxl",
        "--collect-all=tkcalendar",
        "--collect-submodules=obsws_python",
        "--collect-submodules=yt_dlp",
        "--collect-submodules=reportlab",
        "--collect-submodules=google.genai",
        "--collect-submodules=paddleocr",
        "--collect-all=cryptography",
        "--exclude-module=google.genai.tests",
        "--exclude-module=pytest",
        "--exclude-module=tests",
        entry_point
    ]

    print("\nIniciando build...")
    run_command(" ".join(cmd))
    print("\nBuild concluído com sucesso! Verifique a pasta 'dist'.")

if __name__ == "__main__":
    main()
