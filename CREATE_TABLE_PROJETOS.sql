-- ============================================================
-- CREATE TABLE - DADOS DE PROJETOS (tabela unificada)
-- Origem: dados  de projetos.xlsx / Planilha1 (80 colunas)
-- Banco referencia: uau / 10.30.10.238
-- ATENCAO: Confirmar prefixo CT_ com DBA antes de executar
-- Data: 2026-04-08
-- ============================================================

USE uau
GO

CREATE TABLE CT_Projetos (

    -- --------------------------------------------------------
    -- IDENTIFICACAO
    -- --------------------------------------------------------
    Id_Proj             int             NOT NULL IDENTITY(1,1),   -- PK gerada
    IdPlanilha_Proj     int             NULL,                      -- ID original da planilha
    Empresa_Proj        smallint        NOT NULL,                  -- REF: NumCheque.Empresa smallint
    Obra_Proj           varchar(5)      NOT NULL,                  -- REF: Comentarios*.Obra varchar(5)

    -- --------------------------------------------------------
    -- LOCALIZACAO
    -- --------------------------------------------------------
    Pais_Proj           varchar(50)     NULL,                      -- REF: Empresas.Cidade_emp varchar(50)
    Uf_Proj             varchar(5)      NULL,                      -- REF: Terreno.Uf_Terr varchar(5)
    UfExtenso_Proj      varchar(50)     NULL,                      -- REF: Empresas.Cidade_emp varchar(50) | max obs: 18
    Municipio_Proj      varchar(50)     NULL,                      -- REF: Terreno.Cidade_Terr varchar(50) | max obs: 23
    Empreend_Proj       varchar(100)    NOT NULL,                  -- REF: Terreno.Descricao_Terr varchar(100)
    Latitude_Proj       numeric(18,6)   NULL,                      -- REF: Terreno.Area_Terr numeric(18,6)
    Longitude_Proj      numeric(18,6)   NULL,                      -- REF: Terreno.Area_Terr numeric(18,6)

    -- --------------------------------------------------------
    -- URBANISMO - AREAS (M2)
    -- --------------------------------------------------------
    AreaGleba_Proj      numeric(18,6)   NULL,                      -- REF: Terreno.Area_Terr numeric(18,6)
    AreaParcel_Proj     numeric(18,6)   NULL,                      -- REF: Terreno.AreaUtil_Terr numeric(18,6)
    AreaLotes_Proj      numeric(18,6)   NULL,                      -- REF: Terreno.AreaLote_Terr numeric(18,6)
    AreaResProp_Proj    numeric(18,6)   NULL,                      -- REF: Terreno.AreaSaldo_Terr numeric(18,6)
    AreaPublicas_Proj   numeric(18,6)   NULL,                      -- REF: Terreno.AreaAPP_Terr numeric(18,6)
    AreaViario_Proj     numeric(18,6)   NULL,                      -- REF: Terreno.Area_Terr numeric(18,6)
    AreaVerde_Proj      numeric(18,6)   NULL,                      -- REF: Terreno.Area_Terr numeric(18,6)

    -- --------------------------------------------------------
    -- URBANISMO - QUANTIDADES
    -- --------------------------------------------------------
    QtdLotesProsp_Proj  smallint        NULL,                      -- REF: AqFerias.QtdeDiasPend_AqF smallint
    QtdLotesLB_Proj     smallint        NULL,                      -- REF: AqFerias.QtdeDiasPend_AqF smallint
    QtdLotes_Proj       smallint        NULL,                      -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 1814
    QtdQuadras_Proj     smallint        NULL,                      -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 101
    QtdLotesRetif_Proj  smallint        NULL,                      -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 1814
    QtdQdRetif_Proj     smallint        NULL,                      -- REF: AqFerias.QtdeDiasPend_AqF smallint
    QtdLotesExcl_Proj   smallint        NULL,                      -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 1503

    -- --------------------------------------------------------
    -- LEGALIZACAO - DATAS
    -- --------------------------------------------------------
    DtAquisicao_Proj    datetime        NULL,                      -- REF: Terreno.DataCad_Terr datetime
    DtDecreto_Proj      datetime        NULL,                      -- REF: AcaoProjetoHist.DataLan_AcaoProjH datetime
    DtRegistro_Proj     datetime        NULL,                      -- REF: AcaoProjetoHist.DataLan_AcaoProjH datetime
    DtLancamento_Proj   datetime        NULL,                      -- REF: AcaoProjetoHist.DataLan_AcaoProjH datetime
    DtRecObras_Proj     datetime        NULL,                      -- REF: AcaoProjetoHist.DataLan_AcaoProjH datetime
    DtPrevLanc_Proj     datetime        NULL,                      -- REF: AcaoProjetoHist.DataLan_AcaoProjH datetime

    -- --------------------------------------------------------
    -- DRENAGEM
    -- --------------------------------------------------------
    ExtVias_Proj        numeric(18,2)   NULL,                      -- REF: Terreno.CoefZona_Terr numeric(18,2)
    AreaVias_Proj       numeric(18,6)   NULL,                      -- REF: Terreno.Area_Terr numeric(18,6)
    ExtGaleria_Proj     numeric(18,2)   NULL,                      -- REF: Terreno.CoefZona_Terr numeric(18,2)
    ExtRamais_Proj      numeric(18,2)   NULL,                      -- REF: Terreno.CoefZona_Terr numeric(18,2)
    QtdPVDren_Proj      smallint        NULL,                      -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 152
    QtdCaptacoes_Proj   smallint        NULL,                      -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 132

    -- --------------------------------------------------------
    -- SAA - SISTEMA DE ABASTECIMENTO DE AGUA
    -- --------------------------------------------------------
    VazaoMediaSAA_Proj      numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    VazaoMaxDiaSAA_Proj     numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    VazaoMaxHorSAA_Proj     numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    ExtRedeSAA_Proj         numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    VolResApoiado_Proj      numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2) | max obs: 150
    VolResElevado_Proj      numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2) | max obs: 200
    InterligRede_Proj       varchar(5)      NULL,                  -- SIM/NAO | REF: Terreno.Uf_Terr varchar(5)
    QtdBooster_Proj         smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint
    VazaoBooster_Proj       numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    QtdPocos_Proj           smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint
    VazaoPocos_Proj         numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    TempoExplot_Proj        numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)

    -- --------------------------------------------------------
    -- SES - SISTEMA DE ESGOTO SANITARIO
    -- --------------------------------------------------------
    VazaoMediaSES_Proj      numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    VazaoMaxDiaSES_Proj     numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    VazaoMaxHorSES_Proj     numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    ExtRedeSES_Proj         numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    QtdPVSES_Proj           smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 281
    QtdEEE_Proj             smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 2
    VazaoEEE01_Proj         numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    ExtRecEEE01_Proj        numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2) | max obs: 232
    VazaoEEE02_Proj         numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    ExtRecEEE02_Proj        numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2) | max obs: 2700
    VazaoEEE03_Proj         numeric(18,2)   NULL,
    ExtRecEEE03_Proj        numeric(18,2)   NULL,
    VazaoEEE04_Proj         numeric(18,2)   NULL,
    ExtRecEEE04_Proj        numeric(18,2)   NULL,
    VazaoEEE05_Proj         numeric(18,2)   NULL,
    ExtRecEEE05_Proj        numeric(18,2)   NULL,
    QtdETE_Proj             smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint
    VazaoETE_Proj           numeric(18,2)   NULL,

    -- --------------------------------------------------------
    -- RDU - REDE DE DISTRIBUICAO DE ENERGIA
    -- --------------------------------------------------------
    ExtRedeMT_Proj          numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2)
    ExtRedeBT_Proj          numeric(18,2)   NULL,                  -- REF: Terreno.CoefZona_Terr numeric(18,2) | max obs: 4601
    QtdPostes_Proj          smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 634
    QtdPostOrnm_Proj        smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 44
    QtdTraf30_Proj          smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint
    QtdTraf45_Proj          smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 15
    QtdTraf75_Proj          smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 51
    QtdTraf112_Proj         smallint        NULL,
    QtdTraf150_Proj         smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 24

    -- --------------------------------------------------------
    -- ARBORIZACAO
    -- --------------------------------------------------------
    QtdArvores_Proj         smallint        NULL,                  -- REF: AqFerias.QtdeDiasPend_AqF smallint | max obs: 116

    -- --------------------------------------------------------
    -- RESPONSAVEIS
    -- --------------------------------------------------------
    AnalistaUrb_Proj        varchar(150)    NULL,                  -- REF: AcaoACorretiva.Responsavel_ACorret varchar(150) | max obs: 18
    AnalistaLeg_Proj        varchar(150)    NULL,                  -- REF: AcaoACorretiva.Responsavel_ACorret varchar(150) | max obs: 14
    AnalistaPrj_Proj        varchar(150)    NULL,                  -- REF: AcaoACorretiva.Responsavel_ACorret varchar(150) | max obs: 16
    StatusGeral_Proj        varchar(255)    NULL,                  -- REF: ContasReceber.StatusCbr_Prc varchar(255) | max obs: 19

    -- --------------------------------------------------------
    -- AUDITORIA (padrao obrigatorio UAU)
    -- --------------------------------------------------------
    UsrCad_Proj             varchar(8)      NOT NULL,              -- REF: Terreno.UsrCad_Terr varchar(8)
    DataCad_Proj            datetime        NOT NULL,              -- REF: Terreno.DataCad_Terr datetime
    UsrAlt_Proj             varchar(8)      NULL,
    DataAlt_Proj            datetime        NULL,

    CONSTRAINT PK_CT_Projetos PRIMARY KEY (Id_Proj),
    CONSTRAINT UQ_CT_Projetos_EmpObra UNIQUE (Empresa_Proj, Obra_Proj)
)
GO

-- ============================================================
-- VERIFICACAO POS-CRIACAO
-- ============================================================
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    NUMERIC_PRECISION,
    NUMERIC_SCALE,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'CT_Projetos'
ORDER BY ORDINAL_POSITION
GO
