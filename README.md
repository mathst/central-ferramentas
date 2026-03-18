# Central — Plataforma de Utilitários Internos

Aplicativo desktop Windows para automatizar operações internas de geração de relatórios e extração de dados contábeis.

Distribuído como **executável `.exe`** — o usuário abre como qualquer programa, usa, e fecha pelo X da janela. Zero instalação, zero configuração.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.14 + FastAPI + uvicorn |
| Frontend | HTML/CSS/JS estático (sem framework) |
| Banco de dados | SQL Server via `pyodbc` + ODBC Driver 18 |
| Processamento | `pandas`, `openpyxl` |
| Desktop | `pywebview` (WebView2 / Edge nativo) |
| Empacotamento | `pyinstaller` |
| Gerenciador de pacotes | `uv` |

---

## Módulos disponíveis

### Balancete Extrator
Gera relatório de balancete contábil em Excel diretamente do banco UAU.

- Informe o **ano de referência** (ex: `2025`)
- Informe os **números das empresas** separados por vírgula, espaço ou ponto-e-vírgula (ex: `1, 5, 19`)
- Clique em **Baixar Excel**
  - 1 empresa → baixa `.xlsx`
  - 2+ empresas → baixa `.zip` com um `.xlsx` por empresa
- Empresas processadas **em paralelo** (até 4 simultâneas) com progresso em tempo real via SSE

---

## Desenvolvimento local

```bash
# 1. Instalar dependências
make deps   # ou: uv add fastapi uvicorn pywebview pyinstaller sse-starlette

# 2. Subir o servidor
make run    # ou: uv run python -m uvicorn app.main:app --reload --port 8000
```

Acesse `http://localhost:8000`.

As credenciais do banco estão embarcadas em `processar_saldos_final.py` (`_DEFAULTS`). Em dev, um arquivo `.env` na raiz sobrescreve os defaults.

---

## Build — gerar executável Windows

### Pré-requisito único
Baixar o instalador do ODBC Driver 18 e salvar como `assets/msodbcsql.msi`:

```
https://go.microsoft.com/fwlink/?linkid=2345415
```

### Pipeline de build

```bash
make build
```

Isso executa `pyinstaller balancete.spec` e gera `dist/CentralFerramentas/`.
**Não requer Node.js, Bun ou compilação de frontend.**

### Comportamento no Windows (usuário final)

1. Abre `CentralFerramentas.exe`
2. Se o ODBC Driver 18 não estiver instalado, o app instala automaticamente
   *(requer execução como Administrador na primeira vez)*
3. Janela desktop abre — sem browser, sem terminal visível
4. Usa normalmente e fecha pelo **X** da janela ou Alt+F4
5. Credenciais e conexão já vêm configuradas — zero setup

---

## Estrutura

```
api_assit_pg/
├── app/
│   ├── main.py                 # FastAPI: GET /, POST /gerar, GET /progresso, GET /ping
│   └── static/
│       └── index.html          # UI completa (HTML/CSS/JS, sem dependências externas)
├── processar_saldos_final.py   # lógica SQL → DataFrame → Excel (pyodbc + pandas)
├── launcher.py                 # entry point do .exe: sobe uvicorn + abre PyWebView
├── balancete.spec              # spec do PyInstaller
├── Makefile                    # comandos: run, build, deps, clean
└── assets/
    └── msodbcsql.msi           # instalador ODBC Driver 18 (não commitado)
```

---

## Adicionando um novo módulo

1. Adicione a rota no `app/main.py` (novo endpoint POST)
2. Adicione o card HTML na seção `#modules` do `app/static/index.html`
3. Adicione a lógica JS de chamada à API no mesmo `index.html`
4. A lógica de negócio fica em um novo arquivo Python na raiz (seguindo o padrão de `processar_saldos_final.py`)

---

## Requisitos de sistema (dev)

- Python >= 3.14
- ODBC Driver 18 for SQL Server instalado no host
- *Node.js não é necessário*
