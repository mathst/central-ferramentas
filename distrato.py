SELECT * FROM (


SELECT EntSaiEmpAplic.*, CategoriasDeMovFin.Desc_cmf,
Desc_cger As DescricaoNatureza , Pessoas.cod_pes, Pessoas.nome_pes 


FROM EntSaiEmpAplic 


LEFT JOIN CategoriasDeMovFin 


   ON
EntSaiEmpAplic.CategMovFin_es = CategoriasDeMovFin.Codigo_cmf 


LEFT JOIN CategoriasDeTipoDeMovimentacao 


   ON
EntSaiEmpAplic.Natureza_es = CategoriasDeTipoDeMovimentacao.Codigo_cger 


LEFT  JOIN Pessoas 


ON Pessoas.cod_pes = EntSaiEmpAplic.ClienteVenda_es 


WHERE Empresa_es IN (12)


   AND Banco_es
<> -1


   AND (Data_es
BETWEEN '03/01/2026' And '03/31/2026')


   AND (NOT EXISTS
(SELECT BancoContaUsuarios.Banco_BcoCont


 FROM
BancoContaUsuarios WITH(NOLOCK) 


 WHERE Usuario_BcoCont
= 'JAC92'


 AND
EntSaiEmpAplic.Empresa_es = BancoContaUsuarios.Empresa_BcoCont


 AND
EntSaiEmpAplic.Banco_es = BancoContaUsuarios.Banco_BcoCont


 AND
EntSaiEmpAplic.Conta_es = BancoContaUsuarios.Conta_BcoCont))


) AS EntSaiEmpAplic WHERE EntSai_es =  0