-- dim_educacao__escola
-- Grao: 1 linha por escola do cadastro (1.558), inclusive as sem alunos nesta extracao.
-- Papel: dimensao = o "quem/onde" que da contexto aos fatos. Mantem o cadastro completo
-- (eda/saida_04.txt, d3: so 521 escolas tem alunos) e diz, por flag, quais tem dados.

with

escola as (
    select * from {{ ref('stg_educacao__escola') }}
),

turmas_por_escola as (
    select
        id_escola,
        count(*) as qtd_turmas
    from {{ ref('int_educacao__turma_escola') }}
    group by id_escola
),

alunos_por_escola as (
    -- alunos matriculados (turma de matricula -> escola)
    select
        id_escola,
        count(*) as qtd_alunos_matriculados
    from {{ ref('int_educacao__aluno_escola') }}
    where id_escola is not null
    group by id_escola
),

final as (
    select
        e.id_escola,
        e.bairro_escola_hash,
        coalesce(t.qtd_turmas, 0)            as qtd_turmas,
        coalesce(a.qtd_alunos_matriculados, 0) as qtd_alunos_matriculados,
        t.id_escola is not null              as possui_alunos_na_extracao
    from escola as e
    left join turmas_por_escola as t
        on e.id_escola = t.id_escola
    left join alunos_por_escola as a
        on e.id_escola = a.id_escola
)

select * from final