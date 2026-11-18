-- stg_educacao__escola
-- Grao: 1 linha por escola (id_escola unico na EDA).

with

source as (
    select * from {{ source('educacao', 'escola') }}
),

renomeado as (
    select
        id_escola,
        -- codigo anonimizado; salt diferente do bairro do aluno (EDA: 0 valores em comum)
        bairro as bairro_escola_hash
    from source
)

select * from renomeado