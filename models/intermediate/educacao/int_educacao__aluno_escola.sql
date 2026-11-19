-- int_educacao__aluno_escola
-- Grao: 1 linha por aluno.
-- Papel: escola de referencia do aluno, via frequencia (EDA: 100% dos alunos tem frequencia).
-- Serve de "plano B" quando a turma avaliada nao tem escola (eda/saida_04.txt, d1:
-- 41.490 linhas da avaliacao sem escola pela turma).
-- Regra: se o aluno aparece em mais de uma escola, fica a do registro mais recente
-- (onde ele esta agora = onde a acao da gestao chega). Empate: mais registros; depois,
-- menor id_escola, so para o resultado ser deterministico (mesma entrada, mesma saida).

with

frequencia as (
    select
        id_aluno,
        id_escola,
        data_fim
    from {{ ref('stg_educacao__frequencia') }}
),

por_aluno_escola as (
    select
        id_aluno,
        id_escola,
        max(data_fim) as ultima_data_frequencia,
        count(*)      as qtd_registros
    from frequencia
    group by id_aluno, id_escola
),

ranqueado as (
    select
        *,
        row_number() over (
            partition by id_aluno
            order by ultima_data_frequencia desc, qtd_registros desc, id_escola
        ) as ordem,
        count(*) over (partition by id_aluno) as qtd_escolas_distintas
    from por_aluno_escola
)

select
    id_aluno,
    id_escola,
    ultima_data_frequencia,
    qtd_escolas_distintas,
    qtd_escolas_distintas > 1 as frequentou_mais_de_uma_escola
from ranqueado
where ordem = 1