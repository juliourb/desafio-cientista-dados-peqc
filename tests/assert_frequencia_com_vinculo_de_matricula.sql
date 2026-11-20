-- Regra: so existe frequencia de aluno numa turma em que ele tem vinculo (matricula na
-- tabela turma ou avaliacao nessa turma). Analogo, com os dados disponiveis, ao exemplo do
-- enunciado "frequencia nao pode ser anterior a matricula" (nao ha data de matricula nos dados).
-- Por que importa: frequencia sem vinculo nao pode ser atribuida com seguranca a turma
-- de matricula do aluno.
-- Resultado nesta extracao: 105.922 pares (aluno, turma, escola) sem vinculo. O volume indica
-- INCONSISTENCIA DE CHAVE de turma entre os sistemas (mesmo padrao da EDA: 7.792 turmas da
-- avaliacao fora da frequencia), e nao lancamentos indevidos em massa. Por isso o pipeline
-- liga aluno -> escola por duas rotas (origem_escola) e nao depende so da turma.
-- Severidade warn: achado estrutural documentado no README.
{{ config(severity='warn') }}

with

frequencia as (
    select distinct id_aluno, id_turma, id_escola
    from {{ ref('stg_educacao__frequencia') }}
),

matricula as (
    select id_aluno, id_turma from {{ ref('stg_educacao__turma') }}
),

avaliacao as (
    select distinct id_aluno, id_turma from {{ ref('stg_educacao__avaliacao') }}
)

select f.*
from frequencia as f
left join matricula as m
    on f.id_aluno = m.id_aluno and f.id_turma = m.id_turma
left join avaliacao as a
    on f.id_aluno = a.id_aluno and f.id_turma = a.id_turma
where m.id_aluno is null
  and a.id_aluno is null