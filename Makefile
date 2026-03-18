.PHONY: run build pyinstaller clean deps

# ── Dev ───────────────────────────────────────────────────────────────────────

run:
	uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# ── Build pipeline (sem Node/Bun necessário) ──────────────────────────────────

build: pyinstaller
	@echo ""
	@echo "✅ Bundle pronto: dist/CentralFerramentas/"

pyinstaller:
	@echo "Empacotando com PyInstaller..."
	uv run pyinstaller balancete.spec --clean --noconfirm
	@echo "Bundle criado."

# ── Dependências ──────────────────────────────────────────────────────────────

deps:
	uv add pywebview pyinstaller fastapi uvicorn sse-starlette
	uv sync

# ── Limpeza ───────────────────────────────────────────────────────────────────

clean:
	rm -rf build/ dist/
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
