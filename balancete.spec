# balancete.spec — PyInstaller spec para Central de Ferramentas
# Executar: uv run pyinstaller balancete.spec --clean --noconfirm
# Não requer build de frontend — o HTML é estático e já está em app/static/

from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
project_root = Path(SPECPATH)

# ── Datas ────────────────────────────────────────────────────────────────────
datas = [
    (str(project_root / "app" / "static"), "app/static"),
    (str(project_root / "app" / "main.py"), "app"),
    (str(project_root / "processar_saldos_final.py"), "."),
]

# ODBC Driver 18 — incluir se existir em assets/
odbc_msi = project_root / "assets" / "msodbcsql.msi"
if odbc_msi.exists():
    datas.append((str(odbc_msi), "assets"))

# Dados do fastapi/starlette (templates, etc.)
_, _, uvicorn_h   = collect_all("uvicorn")
_, _, webview_h   = collect_all("webview")
webview_d, webview_b, _ = collect_all("webview")
openpyxl_d, _, _  = collect_all("openpyxl")
lxml_d, lxml_b, _ = collect_all("lxml")

datas += webview_d + openpyxl_d + lxml_d

# ── Hidden imports ────────────────────────────────────────────────────────────
hiddenimports = [
    "app.main",
    "processar_saldos_final",
    # FastAPI / Starlette
    "fastapi", "fastapi.responses", "fastapi.staticfiles",
    "starlette", "starlette.staticfiles", "starlette.responses",
    "starlette.middleware.cors",
    # Uvicorn
    *uvicorn_h,
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    # Async
    "anyio", "anyio._backends._asyncio",
    "h11",
    # PyWebView (Windows usa WinForms via pythonnet)
    *webview_h,
    "webview.platforms.winforms", "clr",
    # Data
    "pandas",
    "openpyxl", *collect_submodules("openpyxl"),
    "lxml", "lxml.etree", *collect_submodules("lxml"),
    "pyodbc",
    "psutil",
    "xlrd",
    "dotenv",
    "pydantic", "pydantic.v1",
    # Tkinter (fallback de erro)
    "tkinter", "tkinter.messagebox",
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    [str(project_root / "launcher.py")],
    pathex=[str(project_root)],
    binaries=webview_b + lxml_b,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "reflex", "sqlalchemy", "alembic",      # não mais necessários
        "matplotlib", "scipy", "sklearn",
        "IPython", "jupyter", "pytest",
        "black", "isort", "flake8", "mypy",
    ],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="CentralFerramentas",
    debug=False,
    console=False,
    upx=True,
    runtime_tmpdir=None,
)
