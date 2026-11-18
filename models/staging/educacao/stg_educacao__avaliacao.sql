-- stg_educacao__avaliacao
-- Grao: aluno x turma x bimestre. Formato largo mantido (1:1 com a fonte).
-- Notas com ruido de anonimizacao: NAO arredondar (respeita a anonimizacao).

with

source as (
    select * from {{ source('educacao', 'avaliacao') }}
),

renomeado as (
    select
        to_hex(id_aluno)          as id_aluno,
        id_turma,
        cast(bimestre as int64)   as bimestre,               -- STRING -> INT64
        frequencia                as frequencia_bimestre_pct, -- 0 a 100, fonte principal de assiduidade
        disciplina_1              as nota_disciplina_1,
        disciplina_2              as nota_disciplina_2,
        disciplina_3              as nota_disciplina_3,       -- 100% nula nesta extracao
        disciplina_4              as nota_disciplina_4
    from source
),

sem_copias as (
    -- 1) remove copias identicas
    select distinct * from renomeado
),

consolidado as (
    -- 2) regra "pior caso" (eda/saida_03.txt): 31 grupos com 2 versoes
    --    (22 = uma versao incompleta; 8 = notas diferentes). MIN por coluna:
    --    menor frequencia e menor nota; MIN ignora nulos, entao preenche lacunas.
    --    Em ate 8 grupos a linha final combina valores das duas versoes (documentado).
    select
        id_aluno,
        id_turma,
        bimestre,
        min(frequencia_bimestre_pct) as frequencia_bimestre_pct,
        min(nota_disciplina_1)       as nota_disciplina_1,
        min(nota_disciplina_2)       as nota_disciplina_2,
        min(nota_disciplina_3)       as nota_disciplina_3,
        min(nota_disciplina_4)       as nota_disciplina_4,
        count(*)                     as qtd_versoes_distintas,
        count(*) > 1                 as registro_conflitante
    from sem_copias
    group by id_aluno, id_turma, bimestre
)

select * from consolidado