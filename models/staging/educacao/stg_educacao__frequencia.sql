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
        frequencia                as frequencia_valor_bruto,
        -- formula documentada: frequencia = 100 - faltas/dias_letivos
        -- logo faltas/dias_letivos = 100 - frequencia (conversao de unidade, nao hipotese)
        round(100 - frequencia, 6) as razao_faltas_por_dia
    from source
),

deduplicado as (
    -- EDA: 2.576 linhas repetidas no grao. Aqui removemos so copias identicas;
    -- se restar conflito, o teste de unicidade no YAML avisa (warn).
    select distinct * from renomeado
)

select * from deduplicado