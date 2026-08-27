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
    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)

    print(f"Diretório raiz do projeto: {project_root}")

    # Verificar se o venv está ativo ou usar o caminho do venv
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        print("Erro: .venv não encontrado.")
        sys.exit(1)

    # Pegar o caminho do customtkinter
    try:
        import customtkinter
        ctk_path = Path(customtkinter.__path__[0])
    except ImportError:
        # Tentar via subprocess se não estiver no env atual
        output = subprocess.check_output([str(venv_python), "-c", "import customtkinter; print(customtkinter.__path__[0])"], text=True).strip()
        ctk_path = Path(output)

    print(f"CustomTkinter encontrado em: {ctk_path}")

    # Definir argumentos do PyInstaller
    entry_point = "gui/main_gui.py"
    app_name = "Monitor_Esportes"
    
    # Montar o comando
    # --onefile: cria um único executável (mais lento no boot, mas mais limpo)
    # --noconsole: não abre janela de terminal
    # --add-data: inclui pastas e arquivos necessários
    
    cmd = [
        str(project_root / ".venv" / "Scripts" / "pyinstaller"),
        "--noconsole",
        "--onefile",
        f"--name={app_name}",
        f"--add-data=\"{ctk_path};customtkinter/\"",
        f"--add-data=\"config;config\"",
        f"--add-data=\"modules;modules\"",
        f"--add-data=\"core;core\"",
        f"--add-data=\"templates;templates\"",
        # Hidden imports and submodules
        "--hidden-import=obsws_python",
        "--hidden-import=websocket",
        "--collect-submodules=obsws_python",
        "--collect-submodules=yt_dlp",
        "--collect-submodules=reportlab",
        "--collect-submodules=google.genai",
        "--collect-submodules=paddleocr",
        entry_point
    ]

    print("\nIniciando build...")
    run_command(" ".join(cmd))
    print("\nBuild concluído com sucesso! Verifique a pasta 'dist'.")

if __name__ == "__main__":
    main()
