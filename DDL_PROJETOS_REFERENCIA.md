# DDL - CT_Projetos (tabela unificada)
**Origem:** `dados  de projetos.xlsx` / Planilha1 — **80 colunas → 76 campos + 4 auditoria**  
**Banco de referência:** SQL Server `10.30.10.238` / database `uau` (homologação)  
**Data:** 2026-04-08  
**Script DDL:** `CREATE_TABLE_PROJETOS.sql`

---

## 1. Referência de Padrões UAU

| Campo(s) | Tipo Adotado | Tabela UAU | Coluna UAU | Max observado na planilha |
|---|---|---|---|---|
| ID (PK) | `int IDENTITY(1,1)` | `AcaoProjeto` | `NumEtapa_AcaoProj int` | — |
| EMPRESA | `smallint` | `NumCheque`, `ParcelasParaReceber` | `Empresa smallint` | 143 |
| OBRA | `varchar(5)` | `Comentarios*` (múltiplas) | `Obra varchar(5)` | `'8401P'` |
| PAÍS | `varchar(50)` | `Empresas`, `PesEndereco` | `Cidade_emp varchar(50)` | `'BRASIL'` (6) |
| UF | `varchar(5)` | `Terreno` | `Uf_Terr varchar(5)` | `'AP'` (2) |
| UF_EXTENSO | `varchar(50)` | `Empresas` | `Cidade_emp varchar(50)` | `'MATO GROSSO DO SUL'` (18) |
| MUNICÍPIO | `varchar(50)` | `Terreno`, `Empresas` | `Cidade_Terr varchar(50)` | 23 chars |
| EMPREENDIMENTO | `varchar(100)` | `Terreno` | `Descricao_Terr varchar(100)` | 35 chars |
| LATITUDE / LONGITUDE | `numeric(18,6)` | `Terreno` | `Area_Terr numeric(18,6)` *(proxy)* | — |
| ÁREA (M²) — todos | `numeric(18,6)` | `Terreno` | `Area_Terr`, `AreaUtil_Terr`, `AreaLote_Terr`, `AreaSaldo_Terr`, `AreaAPP_Terr` | 146968.78 |
| EXTENSÃO (M) — todos | `numeric(18,2)` | `Terreno` | `CoefZona_Terr numeric(18,2)` | 20986.21 |
| VOLUME (m³) | `numeric(18,2)` | `Terreno` | `CoefZona_Terr numeric(18,2)` | 200 |
| VAZÃO (L/s, M3/H) — todos | `numeric(18,2)` | `Terreno` | `CoefZona_Terr numeric(18,2)` | 18.62 |
| TEMPO EXPLOTAÇÃO (H) | `numeric(18,2)` | `Terreno` | `CoefZona_Terr numeric(18,2)` | 19.2 |
| Nº LOTES / QUADRAS (QTD int) | `smallint` | `AqFerias`, `Calculo` | `QtdeDiasPend_AqF smallint` | 1814 ✅ (< 32767) |
| QTD PV / CAPTAÇÕES / EEE / ETE / POSTES / TRAFOS / ARVORES | `smallint` | `AqFerias` | `QtdeDiasPend_AqF smallint` | 634 |
| QTD BOOSTER / POÇOS | `smallint` | `AqFerias` | `QtdeDiasPend_AqF smallint` | 1 |
| INTERLIGADO A REDE PÚBLICA? | `varchar(5)` | `Terreno` | `Uf_Terr varchar(5)` | `'SIM'`/`'NÃO'` (3) |
| DATA (todas) | `datetime` | `Terreno`, `AcaoProjetoHist` | `DataCad_Terr datetime`, `DataLan_AcaoProjH datetime` | — |
| ANALISTA (todos) | `varchar(150)` | `AcaoACorretiva`, `AcaoAPreventiva` | `Responsavel_ACorret varchar(150)` | 18 chars |
| STATUS GERAL | `varchar(255)` | `ContasReceber`, `VendaHist` | `StatusCbr_Prc varchar(255)` | `'01_ESTUDOS INICIAIS'` (19) |
| UsrCad / UsrAlt (auditoria) | `varchar(8)` | `Terreno`, `FluxoCxEstrutura` | `UsrCad_Terr varchar(8)` | — |
| DataCad / DataAlt (auditoria) | `datetime` | `Terreno` | `DataCad_Terr datetime` | — |

---

## 2. Mapeamento Coluna Planilha → Campo SQL

| # | Coluna Planilha | Campo SQL | Tipo |
|---|---|---|---|
| 0 | ID | `IdPlanilha_Proj` | `int NULL` |
| 1 | EMPRESA | `Empresa_Proj` | `smallint NOT NULL` |
| 2 | OBRA | `Obra_Proj` | `varchar(5) NOT NULL` |
| 3 | PAÍS | `Pais_Proj` | `varchar(50)` |
| 4 | UF | `Uf_Proj` | `varchar(5)` |
| 5 | UF_EXTENSO | `UfExtenso_Proj` | `varchar(50)` |
| 6 | MUNICÍPIO | `Municipio_Proj` | `varchar(50)` |
| 7 | EMPREENDIMENTO | `Empreend_Proj` | `varchar(100) NOT NULL` |
| 8 | LATITUDE | `Latitude_Proj` | `numeric(18,6)` |
| 9 | LONGITUDE | `Longitude_Proj` | `numeric(18,6)` |
| 10 | ÁREA DA GLEBA (M²) | `AreaGleba_Proj` | `numeric(18,6)` |
| 11 | ÁREA PARCELÁVEL (M²) | `AreaParcel_Proj` | `numeric(18,6)` |
| 12 | ÁREA DE LOTES (M²) | `AreaLotes_Proj` | `numeric(18,6)` |
| 13 | RESERVA DO PROPRIETÁRIO (M²) | `AreaResProp_Proj` | `numeric(18,6)` |
| 14 | ÁREAS PÚBLICAS (M²) | `AreaPublicas_Proj` | `numeric(18,6)` |
| 15 | ÁREA DE VIÁRIO (M²) | `AreaViario_Proj` | `numeric(18,6)` |
| 16 | ÁREA VERDE (M²) | `AreaVerde_Proj` | `numeric(18,6)` |
| 17 | Nº LOTES PROSP | `QtdLotesProsp_Proj` | `smallint` |
| 18 | Nº LOTES LAND BANK | `QtdLotesLB_Proj` | `smallint` |
| 19 | Nº LOTES | `QtdLotes_Proj` | `smallint` |
| 20 | Nº QUADRAS | `QtdQuadras_Proj` | `smallint` |
| 21 | Nº LOTES APOS RETIF | `QtdLotesRetif_Proj` | `smallint` |
| 22 | Nº QUADRAS APOS RETIF | `QtdQdRetif_Proj` | `smallint` |
| 23 | Nº LOTES EXCLUIDOS | `QtdLotesExcl_Proj` | `smallint` |
| 24 | DATA AQUISIÇÃO DA ÁREA | `DtAquisicao_Proj` | `datetime` |
| 25 | DATA DECRETO | `DtDecreto_Proj` | `datetime` |
| 26 | DATA REGISTRO | `DtRegistro_Proj` | `datetime` |
| 27 | DATA LANÇAMENTO | `DtLancamento_Proj` | `datetime` |
| 28 | DATA RECEBIMENTO DE OBRAS | `DtRecObras_Proj` | `datetime` |
| 29 | PREVISAO LANÇAMENTO | `DtPrevLanc_Proj` | `datetime` |
| 30 | EXTENSÃO DE VIAS (M) | `ExtVias_Proj` | `numeric(18,2)` |
| 31 | ÁREA DE VIAS (M²) | `AreaVias_Proj` | `numeric(18,6)` |
| 32 | EXTENSÃO DE GALERIA (M) | `ExtGaleria_Proj` | `numeric(18,2)` |
| 33 | EXTENSÃO DE RAMAIS (M) | `ExtRamais_Proj` | `numeric(18,2)` |
| 34 | QTD PV (DRENAGEM) | `QtdPVDren_Proj` | `smallint` |
| 35 | QTD CAPTAÇÕES | `QtdCaptacoes_Proj` | `smallint` |
| 36 | VAZÃO MÉDIA SAA (L/s) | `VazaoMediaSAA_Proj` | `numeric(18,2)` |
| 37 | VAZÃO MÁXIMA DIÁRIA SAA (L/s) | `VazaoMaxDiaSAA_Proj` | `numeric(18,2)` |
| 38 | VAZÃO MÁXIMA HORÁRIA SAA (L/s) | `VazaoMaxHorSAA_Proj` | `numeric(18,2)` |
| 39 | EXTENSÃO DE REDE SAA (M) | `ExtRedeSAA_Proj` | `numeric(18,2)` |
| 40 | VOLUME RESERVATÓRIO APOIADO (m³) | `VolResApoiado_Proj` | `numeric(18,2)` |
| 41 | VOLUME RESERVATÓRIO ELEVADO (m³) | `VolResElevado_Proj` | `numeric(18,2)` |
| 42 | INTERLIGADO A REDE PÚBLICA? | `InterligRede_Proj` | `varchar(5)` |
| 43 | QTD BOOSTER | `QtdBooster_Proj` | `smallint` |
| 44 | VAZÃO BOOSTER (M3/H) | `VazaoBooster_Proj` | `numeric(18,2)` |
| 45 | QTD POÇOS | `QtdPocos_Proj` | `smallint` |
| 46 | VAZÃO TOTAL DOS POÇOS (M3/H) | `VazaoPocos_Proj` | `numeric(18,2)` |
| 47 | TEMPO DE EXPLOTAÇÃO (HORAS) | `TempoExplot_Proj` | `numeric(18,2)` |
| 48 | VAZÃO MÉDIA SES (L/s) | `VazaoMediaSES_Proj` | `numeric(18,2)` |
| 49 | VAZÃO MÁXIMA DIÁRIA SES (L/s) | `VazaoMaxDiaSES_Proj` | `numeric(18,2)` |
| 50 | VAZÃO MÁXIMA HORÁRIA SES (L/s) | `VazaoMaxHorSES_Proj` | `numeric(18,2)` |
| 51 | EXTENSÃO DE REDE SES (M) | `ExtRedeSES_Proj` | `numeric(18,2)` |
| 52 | QTD PV (SES) | `QtdPVSES_Proj` | `smallint` |
| 53 | QTD EEE | `QtdEEE_Proj` | `smallint` |
| 54 | VAZÃO EEE 01 (L/s) | `VazaoEEE01_Proj` | `numeric(18,2)` |
| 55 | EXTENSÃO RECALQUE EEE 01 (M) | `ExtRecEEE01_Proj` | `numeric(18,2)` |
| 56 | VAZÃO EEE 02 (L/s) | `VazaoEEE02_Proj` | `numeric(18,2)` |
| 57 | EXTENSÃO RECALQUE EEE 02 (M) | `ExtRecEEE02_Proj` | `numeric(18,2)` |
| 58 | VAZÃO EEE 03 (L/s) | `VazaoEEE03_Proj` | `numeric(18,2)` |
| 59 | EXTENSÃO RECALQUE EEE 03 (M) | `ExtRecEEE03_Proj` | `numeric(18,2)` |
| 60 | VAZÃO EEE 04 (L/s) | `VazaoEEE04_Proj` | `numeric(18,2)` |
| 61 | EXTENSÃO RECALQUE EEE 04 (M) | `ExtRecEEE04_Proj` | `numeric(18,2)` |
| 62 | VAZÃO EEE 05 (L/s) | `VazaoEEE05_Proj` | `numeric(18,2)` |
| 63 | EXTENSÃO RECALQUE EEE 05 (M) | `ExtRecEEE05_Proj` | `numeric(18,2)` |
| 64 | QTD ETE | `QtdETE_Proj` | `smallint` |
| 65 | VAZÃO ETE | `VazaoETE_Proj` | `numeric(18,2)` |
| 66 | EXTENSÃO DE REDE MT (M) | `ExtRedeMT_Proj` | `numeric(18,2)` |
| 67 | EXTENSÃO DE REDE BT (M) | `ExtRedeBT_Proj` | `numeric(18,2)` |
| 68 | QTD POSTES | `QtdPostes_Proj` | `smallint` |
| 69 | QTD POSTES ORNAMENTAL | `QtdPostOrnm_Proj` | `smallint` |
| 70 | QTD TRAFOS 30KVA | `QtdTraf30_Proj` | `smallint` |
| 71 | QTD TRAFOS 45KVA | `QtdTraf45_Proj` | `smallint` |
| 72 | QTD TRAFOS 75KVA | `QtdTraf75_Proj` | `smallint` |
| 73 | QTD TRAFOS 112KVA | `QtdTraf112_Proj` | `smallint` |
| 74 | QTD TRAFOS 150KVA | `QtdTraf150_Proj` | `smallint` |
| 75 | QTD ARVORES | `QtdArvores_Proj` | `smallint` |
| 76 | ANALISTA URBANISMO | `AnalistaUrb_Proj` | `varchar(150)` |
| 77 | ANALISTA LEGALIZAÇÃO | `AnalistaLeg_Proj` | `varchar(150)` |
| 78 | ANALISTA PROJETOS | `AnalistaPrj_Proj` | `varchar(150)` |
| 79 | STATUS GERAL | `StatusGeral_Proj` | `varchar(255)` |
| — | (auditoria) | `UsrCad_Proj`, `DataCad_Proj`, `UsrAlt_Proj`, `DataAlt_Proj` | padrão UAU |

---

## 3. Pontos de Atenção

| # | Item | Detalhe |
|---|---|---|
| 1 | **Campos com fórmulas Excel** | Colunas 14, 17, 18, 19, 46, 48, 49 contêm fórmulas (`=K131/10000*20` etc.). Na carga, resolver e persistir apenas o valor numérico |
| 2 | **`smallint` para QTD** | Suporta até 32.767. Maior valor observado: 1814 lotes. Sem risco |
| 3 | **`INTERLIGADO A REDE PÚBLICA?`** | Valor `'NÃO'` tem 3 chars + cedilha. `varchar(5)` cobre com margem |
| 4 | **EEE 03/04/05** | Colunas 58–63 aparecem com valor 0 ou 281 (possivelmente dado ruim). Manter `NULL`able |
| 5 | **`VAZÃO ETE` col 65** | Observado valor `281` que parece ser erro de cópia (mesmo valor de QTD ETE). Validar na carga |
| 6 | **Prefixo `CT_`** | Confirmar com DBA UAU antes de executar |
| 7 | **`UsrCad_Proj NOT NULL`** | Preencher via trigger `AFTER INSERT` ou pela aplicação de carga |

---

## 4. Tabelas UAU Consultadas

| Tabela UAU | Campo consultado | Uso |
|---|---|---|
| `Terreno` | `Area_Terr numeric(18,6)` | Todas as áreas e coordenadas |
| `Terreno` | `CoefZona_Terr numeric(18,2)` | Todas as extensões, vazões, volumes |
| `Terreno` | `Uf_Terr varchar(5)` | UF, INTERLIGADO |
| `Terreno` | `Cidade_Terr varchar(50)` | MUNICÍPIO |
| `Terreno` | `Descricao_Terr varchar(100)` | EMPREENDIMENTO |
| `Terreno` | `UsrCad_Terr varchar(8)` | Auditoria |
| `Terreno` | `DataCad_Terr datetime` | Auditoria e datas |
| `NumCheque` | `Empresa smallint` | EMPRESA |
| `ParcelasParaReceber` | `Empresa smallint` | Confirmação |
| `Comentarios*` | `Obra varchar(5)` | OBRA |
| `Empresas` | `Cidade_emp varchar(50)` | PAÍS, UF_EXTENSO |
| `AqFerias` | `QtdeDiasPend_AqF smallint` | Todas as quantidades |
| `Calculo` | `QtdeRemuneracao_Cal smallint` | Confirmação QTD |
| `AcaoProjetoHist` | `DataLan_AcaoProjH datetime` | Datas de legalização |
| `ContasReceber` | `StatusCbr_Prc varchar(255)` | STATUS GERAL |
| `VendaHist` | `StatusEscritura_vhist varchar(255)` | Confirmação STATUS |
| `AcaoACorretiva` | `Responsavel_ACorret varchar(150)` | ANALISTAS |
| `AcaoAPreventiva` | `Responsavel_APrev varchar(150)` | Confirmação ANALISTAS |
| `FluxoCxEstrutura` | `UsrCad varchar(8)` | Confirmação auditoria |
