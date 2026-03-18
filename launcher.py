"""
launcher.py — Entry point do bundle PyInstaller para Central de Ferramentas.

Splash screen implementada com Win32 puro via ctypes (sem tkinter, sem Qt).
Funciona garantidamente dentro do bundle PyInstaller --onefile.
"""
import os
import sys
import socket
import time
import threading
import subprocess
import atexit
from pathlib import Path

# ── Processo global ───────────────────────────────────────────────────────────
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


# ── Splash Win32 nativo (ctypes) ──────────────────────────────────────────────

def _run_splash(status_ref: list, stop_event: threading.Event) -> None:
    """
    Cria uma janela Win32 simples com GDI para mostrar status e animação.
    Roda na thread principal (necessário no Windows para message pump).
    status_ref[0] = texto atual | status_ref[1] = True → fechar | status_ref[2] = erro
    """
    import ctypes
    import ctypes.wintypes as wt

    user32   = ctypes.windll.user32
    gdi32    = ctypes.windll.gdi32
    kernel32 = ctypes.windll.kernel32

    # Constantes Win32
    WS_POPUP        = 0x80000000
    WS_VISIBLE      = 0x10000000
    CS_HREDRAW      = 0x0002
    CS_VREDRAW      = 0x0001
    WM_DESTROY      = 0x0002
    WM_PAINT        = 0x000F
    WM_TIMER        = 0x0113
    WM_CLOSE        = 0x0010
    WM_LBUTTONUP    = 0x0202
    IDT_ANIM        = 1
    IDT_CHECK       = 2
    COLOR_WINDOW    = 5

    # Cores (GDI usa BGR)
    BG_COLOR    = 0x2e1a1a  # #1a1a2e
    TEXT_COLOR  = 0xe8e2e2  # #e2e8f0
    SUB_COLOR   = 0xb8a394  # #94a3b8
    BAR_BG      = 0x48372d  # #2d3748
    BAR_FG      = 0xf16363  # #6366f1
    ERR_COLOR   = 0x7171f8  # #f87171

    W, H = 440, 210
    anim_x   = [0]
    anim_dir = [1]
    CHUNK    = 80
    BAR_W    = 360
    hwnd_ref = [None]

    def wnd_proc(hwnd, msg, wparam, lparam):
        if msg == WM_DESTROY:
            user32.KillTimer(hwnd, IDT_ANIM)
            user32.KillTimer(hwnd, IDT_CHECK)
            user32.PostQuitMessage(0)
            return 0

        if msg == WM_CLOSE:
            _kill_server()
            os._exit(0)

        if msg == WM_TIMER:
            if wparam == IDT_ANIM:
                # Avança animação
                anim_x[0] += 6 * anim_dir[0]
                if anim_x[0] + CHUNK >= BAR_W:
                    anim_x[0] = BAR_W - CHUNK
                    anim_dir[0] = -1
                elif anim_x[0] <= 0:
                    anim_x[0] = 0
                    anim_dir[0] = 1
                user32.InvalidateRect(hwnd, None, False)

            if wparam == IDT_CHECK:
                # Verifica se a thread de startup pediu para fechar
                if status_ref[1]:
                    user32.DestroyWindow(hwnd)
            return 0

        if msg == WM_PAINT:
            ps = ctypes.create_string_buffer(64)
            hdc = user32.BeginPaint(hwnd, ps)

            # Fundo
            rc = (ctypes.c_long * 4)(0, 0, W, H)
            bg_brush = gdi32.CreateSolidBrush(BG_COLOR)
            user32.FillRect(hdc, rc, bg_brush)
            gdi32.DeleteObject(bg_brush)

            # Título
            title_font = gdi32.CreateFontW(
                22, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0, "Segoe UI"
            )
            old_font = gdi32.SelectObject(hdc, title_font)
            ctypes.windll.gdi32.SetBkMode(hdc, 1)  # TRANSPARENT
            gdi32.SetTextColor(hdc, TEXT_COLOR)
            rc_title = (ctypes.c_long * 4)(0, 30, W, 70)
            user32.DrawTextW(hdc, "Central de Ferramentas", -1, rc_title, 0x25)
            gdi32.SelectObject(hdc, old_font)
            gdi32.DeleteObject(title_font)

            # Status
            status_font = gdi32.CreateFontW(
                16, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, 0, "Segoe UI"
            )
            gdi32.SelectObject(hdc, status_font)
            color = ERR_COLOR if status_ref[2] else SUB_COLOR
            gdi32.SetTextColor(hdc, color)
            rc_status = (ctypes.c_long * 4)(20, 75, W - 20, 130)
            user32.DrawTextW(hdc, status_ref[0], -1, rc_status, 0x25)
            gdi32.SelectObject(hdc, old_font)
            gdi32.DeleteObject(status_font)

            # Barra de fundo
            bar_x = (W - BAR_W) // 2
            bar_y = 145
            rc_bar_bg = (ctypes.c_long * 4)(bar_x, bar_y, bar_x + BAR_W, bar_y + 10)
            bg_bar_brush = gdi32.CreateSolidBrush(BAR_BG)
            user32.FillRect(hdc, rc_bar_bg, bg_bar_brush)
            gdi32.DeleteObject(bg_bar_brush)

            # Bloco animado (oculto se erro)
            if not status_ref[2]:
                rc_bar_fg = (ctypes.c_long * 4)(
                    bar_x + anim_x[0], bar_y,
                    bar_x + anim_x[0] + CHUNK, bar_y + 10
                )
                fg_brush = gdi32.CreateSolidBrush(BAR_FG)
                user32.FillRect(hdc, rc_bar_fg, fg_brush)
                gdi32.DeleteObject(fg_brush)

            # Instrução em modo erro
            if status_ref[2]:
                hint_font = gdi32.CreateFontW(
                    14, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, 0, "Segoe UI"
                )
                gdi32.SelectObject(hdc, hint_font)
                gdi32.SetTextColor(hdc, SUB_COLOR)
                rc_hint = (ctypes.c_long * 4)(0, 165, W, 195)
                user32.DrawTextW(hdc, "Clique no X para fechar.", -1, rc_hint, 0x25)
                gdi32.SelectObject(hdc, old_font)
                gdi32.DeleteObject(hint_font)

            user32.EndPaint(hwnd, ps)
            return 0

        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    WNDPROC = ctypes.WINFUNCTYPE(
        ctypes.c_long, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM
    )
    proc = WNDPROC(wnd_proc)

    hinstance = kernel32.GetModuleHandleW(None)
    class_name = "CentralSplash"

    wc = (ctypes.c_long * 12)(
        ctypes.sizeof(ctypes.c_long) * 12,  # cbSize
        CS_HREDRAW | CS_VREDRAW,             # style
        ctypes.cast(proc, ctypes.c_void_p).value,  # lpfnWndProc
        0, 0,                                # cbClsExtra, cbWndExtra
        hinstance,                           # hInstance
        0,                                   # hIcon
        user32.LoadCursorW(0, 32512),        # hCursor (IDC_ARROW)
        gdi32.CreateSolidBrush(BG_COLOR),    # hbrBackground
        0,                                   # lpszMenuName
        ctypes.cast(
            ctypes.create_unicode_buffer(class_name),
            ctypes.c_void_p
        ).value,                             # lpszClassName
        0,                                   # hIconSm
    )
    user32.RegisterClassExW(wc)

    # Centralizar
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    x = (sw - W) // 2
    y = (sh - H) // 2

    hwnd = user32.CreateWindowExW(
        0, class_name, "Central de Ferramentas",
        WS_POPUP | WS_VISIBLE,
        x, y, W, H,
        0, 0, hinstance, 0,
    )
    hwnd_ref[0] = hwnd

    # Borda arredondada (Windows 11)
    try:
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        pref = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(pref), ctypes.sizeof(pref)
        )
    except Exception:
        pass

    user32.SetTimer(hwnd, IDT_ANIM,  33, None)   # ~30fps
    user32.SetTimer(hwnd, IDT_CHECK, 100, None)   # verifica status a cada 100ms
    user32.ShowWindow(hwnd, 1)
    user32.UpdateWindow(hwnd)

    msg = ctypes.create_string_buffer(48)
    while user32.GetMessageW(msg, 0, 0, 0) > 0:
        user32.TranslateMessage(msg)
        user32.DispatchMessageW(msg)

    stop_event.set()


# ── Startup (thread separada) ─────────────────────────────────────────────────

def _startup(
    status_ref: list,
    stop_event: threading.Event,
    bundle_dir: Path,
) -> None:
    global _server_proc

    def set_status(text: str, error: bool = False) -> None:
        status_ref[0] = text
        status_ref[2] = error

    def fail(msg: str) -> None:
        set_status(msg, error=True)
        # Não fecha o splash — usuário lê o erro e fecha com X

    # 1. ODBC
    if not _odbc_driver_installed():
        set_status("Instalando ODBC Driver 18 (aguarde)...")
        if not _install_odbc_driver(bundle_dir):
            fail(
                "Erro: ODBC Driver não instalado.\n"
                "Execute como Administrador e tente novamente."
            )
            return

    # 2. Porta
    set_status("Alocando porta...")
    try:
        port = _find_free_port()
    except RuntimeError as exc:
        fail(str(exc))
        return

    # 3. Uvicorn
    set_status("Iniciando servidor...")
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
        fail(f"Erro ao iniciar servidor:\n{exc}")
        return

    threading.Thread(
        target=lambda: [_ for _ in _server_proc.stdout],
        daemon=True,
    ).start()

    # 4. Aguarda
    set_status("Aguardando servidor responder...")
    if not _wait_for_server(port, timeout=60):
        rc = _server_proc.poll()
        fail(
            f"Servidor não respondeu (código {rc}).\n"
            "Verifique rede/VPN e execute como Administrador."
        )
        return

    # 5. Sinaliza fechamento do splash
    set_status("Abrindo aplicação...")
    time.sleep(0.3)
    status_ref[1] = True  # dispara DestroyWindow no timer IDT_CHECK

    stop_event.wait(timeout=2)  # aguarda splash fechar
    time.sleep(0.2)

    # 6. WebView
    try:
        import webview
        window = webview.create_window(
            title="Central de Ferramentas",
            url=f"http://127.0.0.1:{port}",
            width=1280, height=820,
            min_size=(900, 600),
            confirm_close=False,
        )
        window.events.closed += _kill_server
        webview.start(debug=False)
    except Exception:
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

    # status_ref: [texto, fechar_splash, é_erro]
    status_ref = ["Iniciando...", False, False]
    stop_event = threading.Event()

    threading.Thread(
        target=_startup,
        args=(status_ref, stop_event, bundle_dir),
        daemon=True,
    ).start()

    # Splash roda na thread principal (Win32 exige)
    _run_splash(status_ref, stop_event)


if __name__ == "__main__":
    main()
