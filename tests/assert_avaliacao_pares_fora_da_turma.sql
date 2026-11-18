-- (EDA 5) Pares (aluno, turma) avaliados que nao existem na matricula atual.
-- Hipotese: troca de turma durante o ano. Severidade warn: e sinal de negocio,
-- nao erro de carga -> alimenta o alerta precoce, nao bloqueia o pipeline.
{{ config(severity='warn') }}

select distinct
    a.id_aluno,
    a.id_turma
from {{ ref('stg_educacao__avaliacao') }} as a
left join {{ ref('stg_educacao__turma') }} as t
    on  a.id_aluno = t.id_aluno
    and a.id_turma = t.id_turma
where t.id_aluno is null