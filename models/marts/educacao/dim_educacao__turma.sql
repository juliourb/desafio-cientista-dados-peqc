-- dim_educacao__turma
-- Grao: 1 linha por turma que aparece em matricula, avaliacao ou no catalogo turma -> escola.
-- Papel: tabela de referencia da turma e da sua escola. E a "ponte" oficial do projeto:
-- todo vinculo com escola passa pela turma (a relacao aluno -> escola da frequencia foi
-- randomizada e nao e usada; eda/saida_05.txt).
-- Escola nula = turma fora do catalogo da frequencia (nao identificada com seguranca).
-- Com mais tempo: esta tabela viria do cadastro oficial de turmas, nao derivada da frequencia.

with

turmas as (
    select id_turma from {{ ref('stg_educacao__turma') }}
    union distinct
    select id_turma from {{ ref('stg_educacao__avaliacao') }}
    union distinct
    select id_turma from {{ ref('int_educacao__turma_escola') }}
),

turma_escola as (
    select * from {{ ref('int_educacao__turma_escola') }}
),

matriculas as (
    select
        id_turma,
        count(*) as qtd_alunos_matriculados
    from {{ ref('stg_educacao__turma') }}
    group by id_turma
),

final as (
    select
        t.id_turma,
        te.id_escola,
        te.id_escola is not null                as escola_identificada,
        coalesce(m.qtd_alunos_matriculados, 0)  as qtd_alunos_matriculados
    from turmas as t
    left join turma_escola as te
        on t.id_turma = te.id_turma
    left join matriculas as m
        on t.id_turma = m.id_turma
)

select * from final
