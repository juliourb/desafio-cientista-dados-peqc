-- int_educacao__aluno_bimestre
-- Grao: aluno x bimestre.
-- Papel: preparar a trajetoria do aluno para o alerta precoce:
--   1) alunos com 2 turmas no mesmo bimestre (~550 casos) viram 1 linha pela regra
--      "pior caso" (menor frequencia, mais faltas, menor media) - mesma regra do staging;
--   2) acumulados ate o bimestre (as normas do Rio usam frequencia ACUMULADA);
--   3) comparacao com o bimestre anterior (queda de frequencia).

with

avaliacao as (
    select * from {{ ref('int_educacao__avaliacao_enriquecida') }}
),

por_aluno_bimestre as (
    select
        id_aluno,
        bimestre,
        -- escola do registro com menor frequencia (coerente com o pior caso), ignorando
        -- registros sem escola identificada; nula se nenhum registro do bimestre tiver escola
        array_agg(id_escola ignore nulls
                  order by coalesce(frequencia_bimestre_pct, 101), id_escola limit 1)[safe_offset(0)]
            as id_escola,
        count(*)                          as qtd_turmas_no_bimestre,
        min(frequencia_bimestre_pct)      as frequencia_bimestre_pct,
        max(faltas_estimadas_bimestre)    as faltas_estimadas_bimestre,
        min(nota_media_bimestre)          as nota_media_bimestre,
        logical_or(tem_nota_baixa)        as tem_disciplina_abaixo_limite,
        logical_or(registro_conflitante)  as registro_conflitante
    from avaliacao
    group by id_aluno, bimestre
),

historico as (
    select
        *,
        -- media simples das frequencias bimestrais = frequencia acumulada
        -- (premissa: bimestres com o mesmo numero de dias letivos)
        avg(frequencia_bimestre_pct)   over acumulado as frequencia_acumulada_pct,
        sum(faltas_estimadas_bimestre) over acumulado as faltas_estimadas_acumuladas,
        count(*)                       over acumulado as qtd_bimestres_ate_aqui,
        lag(frequencia_bimestre_pct)   over ordem     as frequencia_bimestre_anterior_pct,
        lag(bimestre)                  over ordem     as bimestre_anterior
    from por_aluno_bimestre
    window
        ordem     as (partition by id_aluno order by bimestre),
        acumulado as (partition by id_aluno order by bimestre
                      rows between unbounded preceding and current row)
)

select
    id_aluno,
    bimestre,
    id_escola,
    qtd_turmas_no_bimestre,
    frequencia_bimestre_pct,
    round(frequencia_acumulada_pct, 1)    as frequencia_acumulada_pct,
    faltas_estimadas_bimestre,
    round(faltas_estimadas_acumuladas, 1) as faltas_estimadas_acumuladas,
    qtd_bimestres_ate_aqui,
    frequencia_bimestre_anterior_pct,
    -- so compara com o bimestre imediatamente anterior (buracos na serie = 0,2% dos alunos)
    case
        when bimestre - bimestre_anterior = 1
            then round(frequencia_bimestre_pct - frequencia_bimestre_anterior_pct, 1)
    end as variacao_frequencia_pp,
    nota_media_bimestre,
    -- curva frequencia x desempenho: "alguma disciplina < 5" atinge 30% ate de quem tem 95-100%;
    -- por isso a regra usa a MEDIA do bimestre (criterio de aprovacao), e a outra fica informativa
    nota_media_bimestre < {{ var('limite_nota_baixa') }} as nota_media_baixa,
    tem_disciplina_abaixo_limite,
    registro_conflitante
from historico