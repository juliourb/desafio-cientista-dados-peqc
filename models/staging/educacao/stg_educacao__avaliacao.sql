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

deduplicado as (
    -- EDA: 34 linhas repetidas no grao. Mesma politica da frequencia.
    select distinct * from renomeado
)

select * from deduplicado