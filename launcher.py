"""
launcher.py — Entry point do bundle PyInstaller (--onefile).

Single-instance via lock file em %TEMP% (mais robusto que mutex Win32
para processos que encerram abruptamente).

Sem PyWebView — abre no browser padrão (zero processos extras).
Sem subprocessos — uvicorn roda em thread daemon no mesmo processo.
Erros: gravados em %TEMP%/central_ferramentas_erro.txt e abertos no Notepad.
"""
import os
import sys
import socket
import time
import threading
from pathlib import Path

_TEMP      = Path(os.environ.get("TEMP", os.environ.get("TMP", "/tmp")))
_PORT_FILE = _TEMP / "central_ferramentas.port"
_LOCK_FILE = _TEMP / "central_ferramentas.lock"
_LOG_FILE  = _TEMP / "central_ferramentas_erro.txt"

_lock_handle = None  # mantido aberto enquanto somos a instância primária


def _acquire_lock() -> bool:
    """
    Abre o lock file em modo exclusivo via msvcrt.locking (Windows).
    Retorna True se esta é a 1ª instância, False se já existe outra.
    """
    global _lock_handle
    try:
        import msvcrt
        # Abre (ou cria) o arquivo; outro processo que já o abriu com lock impede
        fh = open(str(_LOCK_FILE), "w")
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            _lock_handle = fh
            return True
        except OSError:
            fh.close()
            return False
    except Exception:
        return True  # fallback: assume 1ª instância


def _release_lock() -> None:
    global _lock_handle
    if _lock_handle:
        try:
            import msvcrt
            msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
            _lock_handle.close()
        except Exception:
            pass
        _lock_handle = None
    try:
        _LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _get_bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).parent


def _free_port(start: int = 8000) -> int:
    for port in range(start, start + 20):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise OSError("Nenhuma porta livre em 8000-8019.")


def _ping(port: int) -> bool:
    """Verifica se o servidor está respondendo (sem urllib — só socket TCP)."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def _wait_server(port: int, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _ping(port):
            return True
        time.sleep(0.4)
    return False


def _write_log(content: str) -> None:
    """Grava log de erro e abre no Notepad (sem janela bloqueante)."""
    try:
        _LOG_FILE.write_text(content, encoding="utf-8")
        import subprocess
        subprocess.Popen(["notepad.exe", str(_LOG_FILE)])
    except Exception:
        pass


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
    """Roda uvicorn na thread atual (chamada em thread daemon)."""
    global _uvicorn_error

    if str(bundle_dir) not in sys.path:
        sys.path.insert(0, str(bundle_dir))

    # console=False no PyInstaller zera sys.stdout/stderr → uvicorn logging quebra
    import io as _io
    if sys.stdout is None:
        sys.stdout = _io.StringIO()
    if sys.stderr is None:
        sys.stderr = _io.StringIO()

    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=port,
            log_config=None,    # desativa configuração de logging do uvicorn
            log_level="warning",
            loop="asyncio",
        )
    except Exception:
        import traceback
        _uvicorn_error = traceback.format_exc()


def main() -> None:
    bundle_dir = _get_bundle_dir()
    os.chdir(bundle_dir)

    if str(bundle_dir) not in sys.path:
        sys.path.insert(0, str(bundle_dir))

    # ── 1. Single-instance via lock file ──────────────────────────
    if not _acquire_lock():
        # Já existe outra instância — foca no browser e sai silenciosamente
        port = None
        if _PORT_FILE.exists():
            try:
                port = int(_PORT_FILE.read_text().strip())
            except Exception:
                pass
        if port and _ping(port):
            import webbrowser
            webbrowser.open(f"http://127.0.0.1:{port}")
        os._exit(0)

    # ── 2. ODBC ────────────────────────────────────────────────────
    if not _odbc_ok():
        if not _install_odbc(bundle_dir):
            _write_log(
                "=== Central de Ferramentas — Erro ODBC ===\n\n"
                "Nenhum driver ODBC para SQL Server foi encontrado e a instalação\n"
                "automática falhou.\n\n"
                "Solução:\n"
                "  1. Execute o aplicativo como Administrador, ou\n"
                "  2. Instale manualmente: https://aka.ms/odbc18\n"
            )
            _release_lock()
            os._exit(1)

    # ── 3. Porta livre ─────────────────────────────────────────────
    try:
        port = _free_port()
    except OSError as e:
        _write_log(f"=== Central de Ferramentas — Erro de Porta ===\n\n{e}\n")
        _release_lock()
        os._exit(1)

    try:
        _PORT_FILE.write_text(str(port))
    except Exception:
        pass

    # ── 4. Uvicorn em thread daemon ────────────────────────────────
    t = threading.Thread(
        target=_start_uvicorn,
        args=(port, bundle_dir),
        daemon=True,
    )
    t.start()

    # ── 5. Aguarda servidor responder ─────────────────────────────
    if not _wait_server(port, timeout=30):
        detail = _uvicorn_error or "Thread do uvicorn falhou silenciosamente."
        _write_log(
            "=== Central de Ferramentas — Servidor não iniciou ===\n\n"
            f"{detail}\n"
        )
        _release_lock()
        try:
            _PORT_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        os._exit(1)

    # ── 6. Abre no browser ─────────────────────────────────────────
    import webbrowser
    webbrowser.open(f"http://127.0.0.1:{port}")

    # ── 7. Mantém o processo vivo — keepalive simples ──────────────
    # Não usa _ping() nem urllib aqui para não competir com conexões SSE.
    # Dorme até a thread uvicorn morrer (daemon=True), o que só ocorre
    # se o processo principal encerrar.
    try:
        t.join()  # bloqueia até uvicorn parar (process killed ou ctrl+c)
    except KeyboardInterrupt:
        pass
    finally:
        _release_lock()
        try:
            _PORT_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        os._exit(0)


if __name__ == "__main__":
    main()
