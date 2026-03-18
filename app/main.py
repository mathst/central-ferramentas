"""
app/main.py — Backend FastAPI para Central de Ferramentas.

Rotas:
  GET  /           → serve index.html
  POST /gerar      → processa empresas em paralelo, retorna arquivo
  GET  /progresso  → SSE com updates por empresa durante processamento
  GET  /ping       → healthcheck para o launcher
"""
import asyncio
import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import sys
import pandas as pd
from openpyxl.utils import get_column_letter
sys.path.insert(0, str(Path(__file__).parent.parent))
from processar_saldos_final import conectar_banco, processar_empresa


def _df_to_xlsx_bytes(df: pd.DataFrame, empresa: int, ano: int) -> bytes:
    """Converte DataFrame para bytes xlsx (sem salvar em disco)."""
    fmt_brl = '#,##0.00'
    df = df.copy()
    idx_mon = {
        i for i, c in enumerate(df.columns)
        if c == "Saldo Anterior" or c.startswith("Saldo ")
    }
    for i in idx_mon:
        df.iloc[:, i] = pd.to_numeric(df.iloc[:, i], errors="coerce")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        wb = writer.book
        ws = wb.create_sheet(title="Balancete")
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]
        writer.sheets["Balancete"] = ws

        for col_i, col_name in enumerate(df.columns, 1):
            ws.cell(row=1, column=col_i, value=col_name)

        for row_i, tup in enumerate(df.itertuples(index=False), 2):
            for col_i, val in enumerate(tup, 1):
                if isinstance(val, float) and pd.isna(val):
                    val = None
                cell = ws.cell(row=row_i, column=col_i, value=val)
                if (col_i - 1) in idx_mon and val is not None:
                    cell.number_format = fmt_brl

        for i, col in enumerate(df.columns, 1):
            max_len = max(
                df.iloc[:, i - 1].astype(str).apply(len).max(),
                len(str(col))
            ) + 2
            ws.column_dimensions[get_column_letter(i)].width = min(max_len, 45)

        ws.freeze_panes = "A2"

    return buf.getvalue()

app = FastAPI(docs_url=None, redoc_url=None)

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Fila de progresso por request (SSE) ──────────────────────────────────────
_progress_queues: dict[str, asyncio.Queue] = {}


# ── Schemas ───────────────────────────────────────────────────────────────────

class GerarRequest(BaseModel):
    ano: int
    empresas: list[int]
    request_id: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/ping")
async def ping():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
async def index():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.get("/progresso/{request_id}")
async def progresso(request_id: str, request: Request):
    """SSE stream de progresso para um request específico."""
    queue: asyncio.Queue = asyncio.Queue()
    _progress_queues[request_id] = queue

    async def event_stream() -> AsyncGenerator[bytes, None]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=60.0)
                except asyncio.TimeoutError:
                    yield b"data: {\"type\": \"ping\"}\n\n"
                    continue
                yield f"data: {json.dumps(msg)}\n\n".encode()
                if msg.get("type") == "done" or msg.get("type") == "error":
                    break
        finally:
            _progress_queues.pop(request_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/gerar")
async def gerar(body: GerarRequest):
    """
    Processa as empresas em paralelo (ThreadPoolExecutor, max 4 workers).
    Emite progresso via SSE na fila do request_id.
    Retorna o arquivo xlsx/zip diretamente na resposta.
    """
    ano = body.ano
    empresas = body.empresas
    request_id = body.request_id

    if not (1900 <= ano <= date.today().year + 1):
        raise HTTPException(status_code=400, detail=f"Ano inválido: {ano}")
    if not empresas:
        raise HTTPException(status_code=400, detail="Informe ao menos uma empresa.")

    queue = _progress_queues.get(request_id)

    async def push(msg: dict):
        if queue:
            await queue.put(msg)

    # Testa conectividade antes de despachar threads
    await push({"type": "step", "msg": "Conectando ao banco de dados..."})
    try:
        _test_conn = conectar_banco()
        _test_conn.close()
    except SystemExit:
        await push({"type": "error", "msg": "Falha ao conectar no banco. Verifique a rede."})
        raise HTTPException(status_code=500, detail="Falha na conexão com o banco.")

    buffers: list[tuple[int, bytes]] = []
    erros: list[str] = []
    total = len(empresas)
    concluidas = 0

    # Cada thread abre sua própria conexão — pyodbc não é thread-safe
    def _processar(emp: int) -> tuple[int, bytes | None, str | None]:
        try:
            conn = conectar_banco()
            try:
                df = processar_empresa(conn, emp, ano)
            finally:
                conn.close()
            if df.empty:
                return emp, None, f"Empresa {emp}: sem dados para {ano}"
            return emp, _df_to_xlsx_bytes(df, emp, ano), None
        except Exception as exc:
            return emp, None, f"Empresa {emp}: {exc}"

    await push({"type": "step", "msg": f"Processando {total} empresa(s)..."})

    with ThreadPoolExecutor(max_workers=min(4, total)) as pool:
        futures = {pool.submit(_processar, emp): emp for emp in empresas}
        for future in as_completed(futures):
            emp_id, xlsx_bytes, erro = future.result()
            concluidas += 1
            if erro:
                erros.append(erro)
                await push({"type": "progress", "msg": f"⚠ Empresa {emp_id} ignorada", "done": concluidas, "total": total})
            else:
                buffers.append((emp_id, xlsx_bytes))
                await push({"type": "progress", "msg": f"✓ Empresa {emp_id} concluída", "done": concluidas, "total": total})

    if not buffers:
        msg = "Nenhum dado gerado. " + " | ".join(erros)
        await push({"type": "error", "msg": msg})
        raise HTTPException(status_code=422, detail=msg)

    await push({"type": "step", "msg": "Montando arquivo para download..."})

    if len(buffers) == 1:
        emp_id, data = buffers[0]
        filename = f"BALANCETE {ano} - EMP {emp_id}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for emp_id, xlsx_data in sorted(buffers):
                zf.writestr(f"BALANCETE {ano} - EMP {emp_id}.xlsx", xlsx_data)
        data = zip_buf.getvalue()
        filename = f"BALANCETE {ano} - LOTE.zip"
        media_type = "application/zip"

    ok_emps = ", ".join(str(e) for e, _ in sorted(buffers))
    success = f"✅ {len(buffers)} arquivo(s) gerado(s): empresa(s) {ok_emps}"
    if erros:
        success += f" | ⚠ Ignorados: {'; '.join(erros)}"
    await push({"type": "done", "msg": success, "filename": filename})

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
