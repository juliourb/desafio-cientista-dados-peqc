-- stg_educacao__frequencia
-- Grao: aluno x turma x disciplina x periodo (aprox. mensal, fev-jul).
-- Atencao: o valor bruto NAO e percentual (ver eda/ e a descricao da source).

with

source as (
    select * from {{ source('educacao', 'frequencia') }}
),

renomeado as (
    select
        to_hex(id_aluno) as id_aluno,
        id_turma,
        id_escola,
        disciplina,
        cast(data_inicio as date) as data_inicio,   -- STRING 'AAAA-MM-DD' -> DATE
        cast(data_fim as date)    as data_fim,
        frequencia                as frequencia_valor_bruto
    from source
),

sem_copias as (
    -- 1) remove copias identicas (lixo de carga, sem ambiguidade)
    select distinct * from renomeado
),

consolidado as (
    -- 2) regra de qualidade "pior caso" (eda/saida_03.txt):
    --    1.093 grupos com 2 versoes que so diferem na frequencia (uma delas 100,0).
    --    Fica o MENOR valor = mais faltas. Produto de alerta: prefere-se falso positivo
    --    a perder aluno em risco. A ambiguidade fica visivel em registro_conflitante.
    select
        id_aluno,
        id_turma,
        id_escola,
        disciplina,
        data_inicio,
        data_fim,
        min(frequencia_valor_bruto) as frequencia_valor_bruto,
        count(*)                    as qtd_versoes_distintas,
        count(*) > 1                as registro_conflitante
    from sem_copias
    group by id_aluno, id_turma, id_escola, disciplina, data_inicio, data_fim
)

select
    *,
    -- formula documentada: frequencia = 100 - faltas/dias_letivos
    -- logo faltas/dias_letivos = 100 - frequencia (conversao de unidade, nao hipotese)
    round(100 - frequencia_valor_bruto, 6) as razao_faltas_por_dia
from consolidado