-- stg_educacao__turma
-- Grao: 1 linha por aluno (na pratica, matricula aluno x turma; EDA: id_aluno unico).

with

source as (
    select * from {{ source('educacao', 'turma') }}
),

renomeado as (
    select
        to_hex(id_aluno) as id_aluno,   -- mesma padronizacao de chave das outras tabelas
        id_turma,
        ano as ano_letivo                -- mascarado: sempre 2000
    from source
)

select * from renomeado