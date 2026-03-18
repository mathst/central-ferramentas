"""
launcher.py — Entry point do bundle PyInstaller (--onefile).

IMPORTANTE: Em --onefile, sys.executable É o próprio .exe.
Chamar Popen([sys.executable, ...]) re-executa o launcher = loop infinito.

Solução: uvicorn roda em thread dentro do MESMO processo.
Zero subprocessos. Zero risco de loop.
"""
import os
import sys
import socket
import time
import threading
from pathlib import Path


def _get_bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).parent


def _free_port(start: int = 8000) -> int:
    for port in range(start, start + 10):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise OSError("Nenhuma porta livre em 8000-8009.")


def _wait_server(port: int, timeout: int = 30) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/ping", timeout=2
            ) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def _msgbox(title: str, msg: str, error: bool = True) -> None:
    try:
        import ctypes
        icon = 0x10 if error else 0x40
        ctypes.windll.user32.MessageBoxW(0, msg, title, 0x0 | icon)
    except Exception:
        print(f"{title}: {msg}", file=sys.stderr)


def _odbc_ok() -> bool:
    try:
        import pyodbc
        return any("SQL Server" in d for d in pyodbc.drivers())
    except Exception:
        return False


def _install_odbc(bundle_dir: Path) -> bool:
    import subprocess
    msi = bundle_dir / "assets" / "msodbcsql.msi"
    if not msi.exists():
        return False
    try:
        r = subprocess.run(
            ["msiexec", "/i", str(msi), "/quiet", "/norestart",
             "IACCEPTMSODBCSQLLICENSETERMS=YES"],
            timeout=120,
        )
        return r.returncode == 0
    except Exception:
        return False


_uvicorn_error: str = ""


def _start_uvicorn(port: int, bundle_dir: Path) -> None:
    """Roda uvicorn na thread atual (chamado em thread daemon)."""
    global _uvicorn_error
    if str(bundle_dir) not in sys.path:
        sys.path.insert(0, str(bundle_dir))
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=port,
            log_level="warning",
            loop="asyncio",
        )
    except Exception as e:
        import traceback
        _uvicorn_error = traceback.format_exc()


def main() -> None:
    bundle_dir = _get_bundle_dir()
    os.chdir(bundle_dir)

    # Adiciona bundle_dir ao path para imports funcionarem
    if str(bundle_dir) not in sys.path:
        sys.path.insert(0, str(bundle_dir))

    # 1. ODBC
    if not _odbc_ok():
        _msgbox("Instalando componente",
                "Instalando ODBC Driver...\nAguarde.", error=False)
        if not _install_odbc(bundle_dir):
            _msgbox(
                "Erro — ODBC Driver",
                "Não foi possível instalar o ODBC Driver.\n\n"
                "Execute como Administrador ou instale manualmente:\n"
                "aka.ms/odbc18",
            )
            os._exit(1)

    # 2. Porta
    try:
        port = _free_port()
    except OSError as e:
        _msgbox("Erro — Porta", str(e))
        os._exit(1)

    # 3. Uvicorn em thread (mesmo processo — sem subprocesso)
    t = threading.Thread(
        target=_start_uvicorn,
        args=(port, bundle_dir),
        daemon=True,
    )
    t.start()

    # 4. Aguarda servidor
    if not _wait_server(port, timeout=30):
        detail = _uvicorn_error or "Sem detalhes — thread falhou silenciosamente."
        _msgbox(
            "Erro — Servidor",
            f"O servidor não iniciou.\n\n{detail[:800]}",
        )
        os._exit(1)

    # 5. WebView
    try:
        import webview
        window = webview.create_window(
            title="Central de Ferramentas",
            url=f"http://127.0.0.1:{port}",
            width=1280, height=820,
            min_size=(900, 600),
            confirm_close=False,
        )
        webview.start(debug=False)
    except Exception:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{port}")
        t.join()

    os._exit(0)


if __name__ == "__main__":
    main()
