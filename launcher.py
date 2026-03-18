"""
launcher.py — Entry point do bundle PyInstaller para Central de Ferramentas.

Fluxo:
  1. Resolve o diretório do bundle
  2. Encontra uma porta livre a partir de 8000
  3. Configura env vars do Reflex para modo prod sem recompilação
  4. Inicia uvicorn em subprocess (sem janela de console)
  5. Aguarda o servidor responder em /ping
  6. Abre janela PyWebView
  7. Ao fechar a janela, encerra o processo uvicorn
"""
import os
import sys
import socket
import time
import threading
import subprocess
from pathlib import Path


def _get_bundle_dir() -> Path:
    """Retorna o diretório raiz do bundle ou o CWD em dev.

    --onefile: sys._MEIPASS aponta para a pasta temporária onde tudo foi extraído.
    --onedir:  sys.executable aponta para o .exe, pai é a pasta do bundle.
    dev:       diretório do launcher.py.
    """
    if getattr(sys, "frozen", False):
        # _MEIPASS existe em onefile; em onedir também existe e aponta para _internal/
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).parent


def _find_free_port(start: int = 8000, attempts: int = 10) -> int:
    """Encontra uma porta TCP livre a partir de 'start'."""
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"Portas {start}–{start + attempts - 1} em uso.\n"
        "Feche outros programas e tente novamente."
    )


def _wait_for_server(port: int, timeout: int = 45) -> bool:
    """Aguarda o servidor responder em /ping."""
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/ping", timeout=2
            ) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


def _show_error(title: str, message: str) -> None:
    """Exibe caixa de erro usando tkinter."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        print(f"ERRO: {title}\n{message}", file=sys.stderr)


def _show_info(title: str, message: str) -> None:
    """Exibe caixa informativa usando tkinter."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(title, message)
        root.destroy()
    except Exception:
        print(f"INFO: {title}\n{message}")


def _odbc_driver_installed() -> bool:
    """Verifica se o ODBC Driver 17 ou 18 for SQL Server está instalado."""
    try:
        import pyodbc
        drivers = pyodbc.drivers()
        return any("SQL Server" in d for d in drivers)
    except Exception:
        return False


def _install_odbc_driver(bundle_dir: Path) -> bool:
    """Instala o ODBC Driver 18 silenciosamente. Retorna True se bem-sucedido."""
    msi = bundle_dir / "assets" / "msodbcsql.msi"
    if not msi.exists():
        return False

    try:
        result = subprocess.run(
            [
                "msiexec", "/i", str(msi),
                "/quiet", "/norestart",
                "IACCEPTMSODBCSQLLICENSETERMS=YES",
            ],
            timeout=120,
            check=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def main() -> None:
    bundle_dir = _get_bundle_dir()
    os.chdir(bundle_dir)  # rxconfig.py precisa estar no CWD

    # Instala ODBC Driver automaticamente se necessário
    if not _odbc_driver_installed():
        _show_info(
            "Configuração Inicial",
            "Instalando componente necessário (ODBC Driver).\nAguarde...",
        )
        if not _install_odbc_driver(bundle_dir):
            _show_error(
                "Erro de Instalação",
                "Não foi possível instalar o ODBC Driver 18.\n\n"
                "Execute o programa como Administrador e tente novamente.",
            )
            sys.exit(1)

    try:
        port = _find_free_port()
    except RuntimeError as exc:
        _show_error("Erro de Inicialização", str(exc))
        sys.exit(1)

    env = os.environ.copy()

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m", "uvicorn",
            "app.main:app",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--log-level", "warning",
        ],
        cwd=str(bundle_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    # Drena o pipe continuamente para evitar bloqueio por buffer cheio
    threading.Thread(
        target=lambda: [_ for _ in proc.stdout],
        daemon=True,
    ).start()

    if not _wait_for_server(port):
        proc.kill()
        _show_error(
            "Erro de Inicialização",
            "O servidor não iniciou.\n\n"
            "Verifique:\n"
            "• ODBC Driver 18 for SQL Server instalado\n"
            "• Conexão com a rede da empresa disponível",
        )
        sys.exit(1)

    import webview

    window = webview.create_window(
        title="Central de Ferramentas",
        url=f"http://127.0.0.1:{port}",
        width=1280,
        height=820,
        min_size=(900, 600),
        confirm_close=False,
    )

    def _on_closed() -> None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    window.events.closed += _on_closed
    webview.start(debug=False)
    sys.exit(0)


if __name__ == "__main__":
    main()
