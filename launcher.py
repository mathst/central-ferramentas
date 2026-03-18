"""
launcher.py — Entry point do bundle PyInstaller para Central de Ferramentas.

Design: processo único, sem threads de retry, sem loops de spawn.
Se algo falhar → mostra erro via MessageBox Win32 e sai com os._exit.
"""
import os
import sys
import socket
import time
import subprocess
import atexit
from pathlib import Path

# ── Processo servidor (único) ─────────────────────────────────────────────────
_proc: subprocess.Popen | None = None


def _kill() -> None:
    if _proc and _proc.poll() is None:
        try:
            _proc.kill()
            _proc.wait(timeout=3)
        except Exception:
            pass


atexit.register(_kill)


# ── Helpers ───────────────────────────────────────────────────────────────────

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
    raise OSError("Nenhuma porta disponível em 8000-8009.")


def _wait_server(port: int, timeout: int = 60) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _proc and _proc.poll() is not None:
            return False          # processo morreu — para imediatamente
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/ping", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _msgbox(title: str, msg: str, error: bool = True) -> None:
    """MessageBox Win32 nativo — zero dependências."""
    try:
        import ctypes
        MB_OK = 0x0
        ICON  = 0x10 if error else 0x40   # MB_ICONERROR / MB_ICONINFORMATION
        ctypes.windll.user32.MessageBoxW(0, msg, title, MB_OK | ICON)
    except Exception:
        print(f"{'ERRO' if error else 'INFO'}: {title}\n{msg}", file=sys.stderr)


def _odbc_ok() -> bool:
    try:
        import pyodbc
        return any("SQL Server" in d for d in pyodbc.drivers())
    except Exception:
        return False


def _install_odbc(bundle_dir: Path) -> bool:
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


# ── Main (linear, sem threads, sem retry) ────────────────────────────────────

def main() -> None:
    global _proc

    bundle_dir = _get_bundle_dir()
    os.chdir(bundle_dir)

    # 1. ODBC
    if not _odbc_ok():
        _msgbox("Instalando componente", "Instalando ODBC Driver 18...\nAguarde.", error=False)
        if not _install_odbc(bundle_dir):
            _msgbox(
                "Erro — ODBC Driver",
                "Não foi possível instalar o ODBC Driver automaticamente.\n\n"
                "Execute o programa como Administrador e tente novamente.\n"
                "Ou instale manualmente: aka.ms/odbc18",
            )
            os._exit(1)

    # 2. Porta
    try:
        port = _free_port()
    except OSError as e:
        _msgbox("Erro — Porta", str(e))
        os._exit(1)

    # 3. Uvicorn — UM único Popen
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    _proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(bundle_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )

    # Drena pipe em background para evitar deadlock
    import threading
    threading.Thread(
        target=lambda: [_ for _ in _proc.stdout],
        daemon=True,
    ).start()

    # 4. Aguarda servidor (para se o processo morrer)
    if not _wait_server(port, timeout=60):
        rc = _proc.poll()
        _msgbox(
            "Erro — Servidor não iniciou",
            f"O servidor interno falhou (código {rc}).\n\n"
            "Possíveis causas:\n"
            "• Driver ODBC não compatível (execute como Administrador)\n"
            "• SQL Server inacessível (verifique rede / VPN)\n"
            "• Antivírus bloqueando o processo",
        )
        _kill()
        os._exit(1)

    # 5. Abre WebView (janela nativa)
    try:
        import webview
        window = webview.create_window(
            title="Central de Ferramentas",
            url=f"http://127.0.0.1:{port}",
            width=1280, height=820,
            min_size=(900, 600),
            confirm_close=False,
        )
        window.events.closed += _kill
        webview.start(debug=False)
    except Exception:
        # Fallback: abre no browser padrão
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{port}")
        try:
            _proc.wait()
        except KeyboardInterrupt:
            pass

    _kill()
    os._exit(0)


if __name__ == "__main__":
    main()
