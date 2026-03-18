# balancete.spec — PyInstaller spec para Central de Ferramentas
# Executar: uv run pyinstaller balancete.spec --clean --noconfirm
# Sem PyWebView — abre no browser padrão do usuário (zero processos extras)

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

_, _, uvicorn_h  = collect_all("uvicorn")
openpyxl_d, _, _ = collect_all("openpyxl")
lxml_d, lxml_b, _ = collect_all("lxml")

datas += openpyxl_d + lxml_d

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
    # Data
    "pandas",
    "openpyxl", *collect_submodules("openpyxl"),
    "lxml", "lxml.etree", *collect_submodules("lxml"),
    "pyodbc",
    "xlrd",
    "dotenv",
    "pydantic", "pydantic.v1",
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    [str(project_root / "launcher.py")],
    pathex=[str(project_root)],
    binaries=lxml_b,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "webview", "clr", "pythonnet",
        "psutil",
        "reflex", "sqlalchemy", "alembic",
        "matplotlib", "scipy", "sklearn",
        "IPython", "jupyter", "pytest",
        "black", "isort", "flake8", "mypy",
        "tkinter",
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
