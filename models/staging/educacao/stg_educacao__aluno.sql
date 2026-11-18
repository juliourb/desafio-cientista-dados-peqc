-- stg_educacao__aluno
-- Grao: 1 linha por aluno (id_aluno unico na EDA).
-- Papel: limpar e padronizar a tabela bruta. Sem joins, sem regra de negocio.

with

source as (
    select * from {{ source('educacao', 'aluno') }}
),

renomeado as (
    select
        -- chave padronizada no ponto de entrada: BYTES -> texto hexadecimal
        -- (a mesma conversao sera aplicada em turma, frequencia e avaliacao)
        to_hex(id_aluno) as id_aluno,
        id_turma,
        faixa_etaria,

        -- ordem numerica: como texto, '6-10' ficaria depois de '15-17'
        case faixa_etaria
            when '0-5'   then 1
            when '6-10'  then 2
            when '11-14' then 3
            when '15-17' then 4
            when '18+'   then 5
        end as ordem_faixa_etaria,

        -- codigo anonimizado, nao e o nome do bairro
        bairro as bairro_residencia_hash

    from source
)

select * from renomeado