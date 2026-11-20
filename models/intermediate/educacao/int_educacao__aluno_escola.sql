-- int_educacao__aluno_escola
-- Grao: 1 linha por aluno.
-- Papel: escola de MATRICULA do aluno = turma de matricula (stg_educacao__aluno) ligada a
-- escola pela ponte int_educacao__turma_escola.
-- Por que nao usar a escola do aluno na tabela de frequencia: nela a associacao
-- aluno -> turma/escola foi randomizada (eda/saida_05.txt: so 11 de 105.934 pares
-- aluno x turma batem com a matricula; a escola "do aluno" concorda com a da turma em 0,3%).
-- Da frequencia usamos apenas a relacao turma -> escola, que foi preservada.
-- Escola nula = turma de matricula fora do catalogo turma -> escola ("nao identificada").

with

aluno as (
    select
        id_aluno,
        id_turma as id_turma_matricula
    from {{ ref('stg_educacao__aluno') }}
),

turma_escola as (
    select * from {{ ref('int_educacao__turma_escola') }}
),

final as (
    select
        al.id_aluno,
        al.id_turma_matricula,
        te.id_escola
    from aluno as al
    left join turma_escola as te
        on al.id_turma_matricula = te.id_turma
)

select * from final
