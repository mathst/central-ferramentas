"""
launcher.py — Entry point do bundle PyInstaller para Central de Ferramentas.

Fluxo:
  1. Abre tela de splash (tkinter) com progresso
  2. Verifica/instala ODBC Driver 18 silenciosamente
  3. Inicia uvicorn em subprocess sem janela de console
  4. Aguarda o servidor responder em /ping
  5. Fecha splash, abre janela PyWebView
  6. Ao fechar a janela, encerra o processo uvicorn
"""
import os
import sys
import socket
import time
import threading
import subprocess
from pathlib import Path


# ── Utilitários de path ───────────────────────────────────────────────────────

def _get_bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).parent


def _find_free_port(start: int = 8000, attempts: int = 10) -> int:
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


def _wait_for_server(port: int, timeout: int = 60) -> bool:
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
        time.sleep(0.5)
    return False


def _odbc_driver_installed() -> bool:
    try:
        import pyodbc
        return any("SQL Server" in d for d in pyodbc.drivers())
    except Exception:
        return False


def _install_odbc_driver(bundle_dir: Path) -> bool:
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
        )
        return result.returncode == 0
    except Exception:
        return False


# ── Splash screen ─────────────────────────────────────────────────────────────

class SplashScreen:
    """Tela de carregamento nativa com tkinter. Thread-safe via after()."""

    def __init__(self) -> None:
        import tkinter as tk

        self._tk = tk
        self._root = tk.Tk()
        self._root.title("Central de Ferramentas")
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close_request)

        # Centralizar na tela
        w, h = 440, 220
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self._root.configure(bg="#1a1a2e")

        # Título
        tk.Label(
            self._root, text="Central de Ferramentas",
            font=("Segoe UI", 16, "bold"),
            bg="#1a1a2e", fg="#e2e8f0",
        ).pack(pady=(28, 4))

        # Status
        self._status_var = tk.StringVar(value="Iniciando...")
        tk.Label(
            self._root, textvariable=self._status_var,
            font=("Segoe UI", 10),
            bg="#1a1a2e", fg="#94a3b8",
        ).pack(pady=(0, 12))

        # Barra de progresso manual (canvas)
        self._canvas = tk.Canvas(
            self._root, width=360, height=8,
            bg="#2d3748", highlightthickness=0,
        )
        self._canvas.pack()
        self._bar = self._canvas.create_rectangle(
            0, 0, 0, 8, fill="#6366f1", outline=""
        )
        self._progress = 0.0

        # Mensagem de erro (oculta por padrão)
        self._error_var = tk.StringVar(value="")
        self._error_label = tk.Label(
            self._root, textvariable=self._error_var,
            font=("Segoe UI", 9),
            bg="#1a1a2e", fg="#f87171", wraplength=400, justify="center",
        )
        self._error_label.pack(pady=(10, 0))

        # Botão fechar (oculto por padrão)
        self._btn = tk.Button(
            self._root, text="Fechar",
            font=("Segoe UI", 9, "bold"),
            bg="#ef4444", fg="white", relief="flat",
            padx=20, pady=4,
            command=self._force_exit,
        )

        self._closed = False
        self._allow_close = False

    # ── API pública (thread-safe) ─────────────────────────────────────────────

    def set_status(self, text: str, progress: float | None = None) -> None:
        """Atualiza texto e barra de progresso (0.0–1.0)."""
        def _update():
            self._status_var.set(text)
            if progress is not None:
                self._progress = max(0.0, min(1.0, progress))
                self._canvas.coords(
                    self._bar, 0, 0, int(360 * self._progress), 8
                )
        self._root.after(0, _update)

    def show_error(self, message: str) -> None:
        """Mostra erro e botão Fechar — bloqueia fechamento acidental."""
        def _update():
            self._allow_close = True
            self._error_var.set(message)
            self._error_label.pack(pady=(10, 0))
            self._btn.pack(pady=(8, 0))
            self._canvas.coords(self._bar, 0, 0, 0, 8)  # zera barra
        self._root.after(0, _update)

    def close(self) -> None:
        """Fecha o splash normalmente."""
        def _close():
            self._allow_close = True
            self._closed = True
            self._root.destroy()
        self._root.after(0, _close)

    def run(self) -> None:
        """Inicia o loop principal do tkinter (bloqueante)."""
        self._root.mainloop()

    # ── Internos ──────────────────────────────────────────────────────────────

    def _on_close_request(self) -> None:
        if self._allow_close:
            self._force_exit()

    def _force_exit(self) -> None:
        self._closed = True
        self._root.destroy()
        os._exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def _startup(splash: SplashScreen, bundle_dir: Path) -> None:
    """Roda em thread separada; atualiza splash; inicia webview ao terminar."""

    def fail(msg: str) -> None:
        splash.show_error(msg)
        # Não chama sys.exit() — deixa o usuário ver o erro e clicar Fechar

    # 1. ODBC Driver
    if not _odbc_driver_installed():
        splash.set_status("Instalando ODBC Driver 18...", 0.1)
        ok = _install_odbc_driver(bundle_dir)
        if not ok:
            fail(
                "Não foi possível instalar o ODBC Driver 18 automaticamente.\n\n"
                "Execute o programa como Administrador e tente novamente.\n"
                "Se o problema persistir, instale manualmente:\n"
                "aka.ms/odbc18"
            )
            return

    # 2. Porta livre
    splash.set_status("Alocando porta...", 0.25)
    try:
        port = _find_free_port()
    except RuntimeError as exc:
        fail(str(exc))
        return

    # 3. Iniciar uvicorn
    splash.set_status("Iniciando servidor...", 0.45)
    env = os.environ.copy()
    try:
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
    except Exception as exc:
        fail(f"Erro ao iniciar servidor:\n{exc}")
        return

    # Drena pipe para evitar bloqueio
    threading.Thread(
        target=lambda: [_ for _ in proc.stdout],
        daemon=True,
    ).start()

    # 4. Aguardar servidor
    splash.set_status("Aguardando servidor responder...", 0.65)
    if not _wait_for_server(port):
        proc.kill()
        # Captura últimas linhas de log para diagnóstico
        fail(
            "O servidor não respondeu no tempo esperado.\n\n"
            "Verifique:\n"
            "• ODBC Driver 18 for SQL Server instalado\n"
            "• Rede da empresa disponível (VPN ativa?)\n"
            "• Antivírus não está bloqueando o processo"
        )
        return

    # 5. Tudo OK — fechar splash e abrir webview
    splash.set_status("Abrindo aplicação...", 1.0)
    time.sleep(0.3)
    splash.close()

    # Aguarda o tkinter fechar de fato antes de abrir webview
    time.sleep(0.4)

    try:
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
    except Exception as exc:
        # Webview falhou — abrir no browser padrão como fallback
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{port}")
        # Mantém o processo vivo até ser fechado manualmente
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()

    sys.exit(0)


def main() -> None:
    bundle_dir = _get_bundle_dir()
    os.chdir(bundle_dir)

    splash = SplashScreen()

    # Startup roda em thread separada; splash.run() bloqueia na thread principal
    thread = threading.Thread(
        target=_startup, args=(splash, bundle_dir), daemon=True
    )
    thread.start()

    splash.run()  # bloqueia até splash.close() ou _force_exit()


if __name__ == "__main__":
    main()
