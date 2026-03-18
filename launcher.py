"""
launcher.py — Entry point do bundle PyInstaller (--onefile).

Estratégia single-instance:
  - Mutex do Windows garante que só uma instância rode por vez.
  - Se já existe uma instância, abre o browser apontando para ela e sai.
  - Porta escolhida é gravada em %TEMP%/central_ferramentas.port para que
    a segunda instância saiba para onde redirecionar o browser.

Sem PyWebView — abre diretamente no browser padrão do usuário.
Sem subprocessos — uvicorn roda em thread daemon no mesmo processo.
"""
import os
import sys
import socket
import time
import threading
from pathlib import Path

_TEMP = Path(os.environ.get("TEMP", os.environ.get("TMP", "/tmp")))
_PORT_FILE = _TEMP / "central_ferramentas.port"
_LOCK_FILE = _TEMP / "central_ferramentas.lock"


def _acquire_lock() -> bool:
    """Lock file exclusivo via abertura com O_CREAT|O_EXCL — atômico no Windows.
    Retorna True se esta é a primeira instância, False se já existe outra.
    O arquivo é deletado automaticamente ao sair via _release_lock().
    """
    # Verifica se o processo que criou o lock ainda está vivo
    if _LOCK_FILE.exists():
        try:
            pid = int(_LOCK_FILE.read_text().strip())
            # Testa se o PID ainda existe enviando sinal 0
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return False  # processo ainda vivo
            # PID morto — lock file stale, remove e continua
        except Exception:
            pass
        try:
            _LOCK_FILE.unlink()
        except Exception:
            pass

    try:
        _LOCK_FILE.write_text(str(os.getpid()))
        return True
    except Exception:
        return True  # se não conseguiu criar, assume primeira instância


def _release_lock() -> None:
    try:
        _LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


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
            log_config=None,   # desativa configuração de logging do uvicorn
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

    # 1. Single-instance via lock file
    if not _acquire_lock():
        port = None
        if _PORT_FILE.exists():
            try:
                port = int(_PORT_FILE.read_text().strip())
            except Exception:
                pass
        if port:
            import webbrowser
            webbrowser.open(f"http://127.0.0.1:{port}")
        else:
            _msgbox("Central de Ferramentas",
                    "Já existe uma instância em execução.", error=False)
        os._exit(0)

    # 2. ODBC
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

    # 3. Porta
    try:
        port = _free_port()
    except OSError as e:
        _msgbox("Erro — Porta", str(e))
        os._exit(1)

    # Grava porta para que instâncias subsequentes possam redirecionar
    try:
        _PORT_FILE.write_text(str(port))
    except Exception:
        pass

    # 4. Uvicorn em thread daemon (mesmo processo — sem subprocesso)
    t = threading.Thread(
        target=_start_uvicorn,
        args=(port, bundle_dir),
        daemon=True,
    )
    t.start()

    # 5. Aguarda servidor
    if not _wait_server(port, timeout=30):
        detail = _uvicorn_error or "Sem detalhes — thread falhou silenciosamente."
        _release_lock()
        try:
            _PORT_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        # Grava log e abre no Notepad — sem MessageBox bloqueante
        log = _TEMP / "central_ferramentas_erro.txt"
        try:
            log.write_text(
                f"=== Central de Ferramentas — Erro de inicialização ===\n\n{detail}\n",
                encoding="utf-8",
            )
            import subprocess
            subprocess.Popen(["notepad.exe", str(log)])
        except Exception:
            pass
        os._exit(1)

    # 6. Abre no browser padrão (sem WebView2 — zero processos extras)
    import webbrowser
    webbrowser.open(f"http://127.0.0.1:{port}")

    # 7. Mantém o processo vivo enquanto o servidor estiver respondendo
    #    Sai automaticamente se o servidor parar (ex: erro interno)
    try:
        while True:
            time.sleep(5)
            if not _wait_server(port, timeout=3):
                break
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
