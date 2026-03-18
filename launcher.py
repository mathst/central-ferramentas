"""
launcher.py — Entry point do bundle PyInstaller para Central de Ferramentas.

Fluxo:
  1. Abre splash (tkinter) com barra animada indeterminada
  2. Verifica/instala ODBC Driver 18 silenciosamente
  3. Inicia uvicorn em subprocess sem janela de console
  4. Aguarda servidor responder em /ping (timeout 60s)
  5. Fecha splash, abre janela PyWebView
  6. Ao fechar a janela, encerra o processo uvicorn
"""
import os
import sys
import socket
import time
import threading
import subprocess
import atexit
from pathlib import Path

# Processo global — garantia de kill mesmo em crash
_server_proc: subprocess.Popen | None = None


def _kill_server() -> None:
    global _server_proc
    if _server_proc and _server_proc.poll() is None:
        try:
            _server_proc.kill()
        except Exception:
            pass


atexit.register(_kill_server)


# ── Utilitários ───────────────────────────────────────────────────────────────

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
        f"Portas {start}–{start + attempts - 1} estão em uso.\n"
        "Feche outros programas e tente novamente."
    )


def _wait_for_server(port: int, timeout: int = 60) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        # Se o processo filho morreu, não adianta esperar
        if _server_proc and _server_proc.poll() is not None:
            return False
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
    """Janela de carregamento com barra animada indeterminada.

    - X sempre fecha (mata tudo via os._exit)
    - Em erro: mostra mensagem + botão Fechar
    - Barra indeterminada: não mente sobre o progresso real
    """

    BAR_W = 360
    CHUNK = 80   # largura do bloco animado
    STEP  = 6    # pixels por frame
    FPS   = 30   # frames por segundo

    def __init__(self) -> None:
        import tkinter as tk
        self._tk = tk
        self._root = tk.Tk()
        self._root.title("Central de Ferramentas")
        self._root.resizable(False, False)
        # X sempre encerra tudo imediatamente
        self._root.protocol("WM_DELETE_WINDOW", self._force_exit)

        w, h = 440, 230
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self._root.configure(bg="#1a1a2e")

        tk.Label(
            self._root, text="Central de Ferramentas",
            font=("Segoe UI", 16, "bold"),
            bg="#1a1a2e", fg="#e2e8f0",
        ).pack(pady=(28, 4))

        self._status_var = tk.StringVar(value="Iniciando...")
        tk.Label(
            self._root, textvariable=self._status_var,
            font=("Segoe UI", 10),
            bg="#1a1a2e", fg="#94a3b8",
        ).pack(pady=(0, 14))

        # Canvas para barra indeterminada
        self._canvas = tk.Canvas(
            self._root, width=self.BAR_W, height=10,
            bg="#2d3748", highlightthickness=0,
        )
        self._canvas.pack()
        self._block = self._canvas.create_rectangle(
            0, 0, self.CHUNK, 10, fill="#6366f1", outline=""
        )
        self._block_x = 0
        self._direction = 1
        self._animating = True
        self._animate()

        # Área de erro (oculta)
        self._error_var = tk.StringVar(value="")
        self._error_label = tk.Label(
            self._root, textvariable=self._error_var,
            font=("Segoe UI", 9),
            bg="#1a1a2e", fg="#f87171",
            wraplength=410, justify="center",
        )

        self._btn_close = tk.Button(
            self._root, text="  Fechar  ",
            font=("Segoe UI", 9, "bold"),
            bg="#ef4444", fg="white", relief="flat",
            padx=16, pady=5,
            command=self._force_exit,
        )

    # ── Animação ──────────────────────────────────────────────────────────────

    def _animate(self) -> None:
        if not self._animating:
            return
        self._block_x += self.STEP * self._direction
        # Inverte direção nas bordas
        if self._block_x + self.CHUNK >= self.BAR_W:
            self._block_x = self.BAR_W - self.CHUNK
            self._direction = -1
        elif self._block_x <= 0:
            self._block_x = 0
            self._direction = 1
        self._canvas.coords(
            self._block,
            self._block_x, 0,
            self._block_x + self.CHUNK, 10,
        )
        self._root.after(1000 // self.FPS, self._animate)

    # ── API pública (thread-safe) ─────────────────────────────────────────────

    def set_status(self, text: str) -> None:
        self._root.after(0, lambda: self._status_var.set(text))

    def show_error(self, message: str) -> None:
        def _update():
            self._animating = False
            self._canvas.coords(self._block, 0, 0, 0, 0)  # esconde bloco
            self._error_var.set(message)
            self._error_label.pack(pady=(12, 0))
            self._btn_close.pack(pady=(10, 0))
        self._root.after(0, _update)

    def close(self) -> None:
        def _close():
            self._animating = False
            self._root.destroy()
        self._root.after(0, _close)

    def run(self) -> None:
        self._root.mainloop()

    # ── Internos ──────────────────────────────────────────────────────────────

    def _force_exit(self) -> None:
        """Mata tudo imediatamente — sem perguntas."""
        _kill_server()
        os._exit(0)


# ── Startup (roda em thread separada) ────────────────────────────────────────

def _startup(splash: SplashScreen, bundle_dir: Path) -> None:
    global _server_proc

    def fail(msg: str) -> None:
        """Mostra erro no splash e encerra a thread (usuário clica Fechar)."""
        splash.show_error(msg)
        # Não chama sys.exit — deixa o splash visível para o usuário ler

    # 1. ODBC Driver
    if not _odbc_driver_installed():
        splash.set_status("Instalando ODBC Driver 18 (aguarde)...")
        if not _install_odbc_driver(bundle_dir):
            fail(
                "Não foi possível instalar o ODBC Driver automaticamente.\n\n"
                "Solução: execute o programa como Administrador.\n"
                "Se persistir, instale manualmente: aka.ms/odbc18"
            )
            return

    # 2. Porta livre
    splash.set_status("Alocando porta...")
    try:
        port = _find_free_port()
    except RuntimeError as exc:
        fail(str(exc))
        return

    # 3. Iniciar uvicorn (uma única vez)
    splash.set_status("Iniciando servidor...")
    env = os.environ.copy()
    try:
        _server_proc = subprocess.Popen(
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
        fail(f"Erro ao iniciar servidor interno:\n{exc}")
        return

    # Drena pipe para evitar deadlock por buffer cheio
    threading.Thread(
        target=lambda: [_ for _ in _server_proc.stdout],
        daemon=True,
    ).start()

    # 4. Aguardar resposta
    splash.set_status("Aguardando servidor responder...")
    if not _wait_for_server(port, timeout=60):
        rc = _server_proc.poll()
        fail(
            f"O servidor não respondeu (código de saída: {rc}).\n\n"
            "Possíveis causas:\n"
            "• ODBC Driver não instalado (rode como Administrador)\n"
            "• SQL Server inacessível (verifique a rede/VPN)\n"
            "• Antivírus bloqueando o processo"
        )
        return

    # 5. Sucesso — fecha splash e abre webview
    splash.set_status("Abrindo aplicação...")
    time.sleep(0.2)
    splash.close()
    time.sleep(0.3)  # aguarda tkinter fechar antes de criar webview

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
            _kill_server()

        window.events.closed += _on_closed
        webview.start(debug=False)

    except Exception:
        # Fallback: abre no browser padrão
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{port}")
        try:
            _server_proc.wait()
        except KeyboardInterrupt:
            _kill_server()

    os._exit(0)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    bundle_dir = _get_bundle_dir()
    os.chdir(bundle_dir)

    splash = SplashScreen()

    threading.Thread(
        target=_startup,
        args=(splash, bundle_dir),
        daemon=True,
    ).start()

    splash.run()  # bloqueia na thread principal até fechar


if __name__ == "__main__":
    main()
