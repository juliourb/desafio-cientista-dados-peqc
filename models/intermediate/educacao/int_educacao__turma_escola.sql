-- int_educacao__turma_escola
-- Grao: 1 linha por turma.
-- Papel: ponte turma -> escola. A tabela turma nao tem id_escola; a ligacao so
-- existe na frequencia (EDA 4: cada turma aparece em exatamente 1 escola).
-- O teste unique em id_turma transforma esse achado da EDA em garantia permanente.

with

frequencia as (
    select
        id_turma,
        id_escola
    from {{ ref('stg_educacao__frequencia') }}
),

turma_escola as (
    select
        id_turma,
        id_escola
    from frequencia
    group by id_turma, id_escola
)

select * from turma_escola