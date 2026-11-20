-- mart_educacao__frequencia_desempenho
-- Grao: grupo etario x faixa de 5 p.p. de frequencia bimestral.
-- Quem usa: equipe de planejamento / quem calibra o alerta precoce.
-- Para decidir: a partir de qual frequencia o desempenho piora de forma clara
-- (limiar LOCAL, validando os limiares da norma nesta rede).
-- Cuidados: e associacao, nao causa; notas tem ruido de anonimizacao (+-0,2);
-- grupo etario separado porque a base muda de composicao entre bimestres (efeito composicao).

with

fato as (
    select
        id_aluno,
        frequencia_bimestre_pct,
        nota_media_bimestre,
        tem_nota_baixa,
        case when faixa_etaria = '15-17' then '15-17' else 'demais' end as grupo_etario
    from {{ ref('fct_educacao__avaliacao_bimestre') }}
    where frequencia_bimestre_pct is not null
      and qtd_disciplinas_com_nota > 0
),

com_faixa as (
    select
        *,
        -- faixas de 5 p.p.: 0-5, 5-10, ..., 95-100 (100 entra na ultima)
        cast(least(floor(frequencia_bimestre_pct / 5) * 5, 95) as int64) as faixa_frequencia_inicio
    from fato
),

por_faixa as (
    select
        grupo_etario,
        faixa_frequencia_inicio,
        count(*)                       as qtd_registros,
        count(distinct id_aluno)       as qtd_alunos,
        round(avg(nota_media_bimestre), 2) as nota_media,
        countif(tem_nota_baixa)        as qtd_registros_nota_baixa
    from com_faixa
    group by grupo_etario, faixa_frequencia_inicio
),

referencia as (
    -- grupo de comparacao: quem tem 95-100% de frequencia
    select
        grupo_etario,
        safe_divide(qtd_registros_nota_baixa, qtd_registros) as taxa_nota_baixa_referencia
    from por_faixa
    where faixa_frequencia_inicio = 95
),

final as (
    select
        p.grupo_etario,
        p.faixa_frequencia_inicio,
        p.faixa_frequencia_inicio + 5 as faixa_frequencia_fim,
        p.qtd_registros,
        p.qtd_alunos,
        p.nota_media,
        p.qtd_registros_nota_baixa,
        round(100 * safe_divide(p.qtd_registros_nota_baixa, p.qtd_registros), 1)
            as pct_registros_nota_baixa,
        -- risco relativo: quantas vezes a chance de nota baixa e maior que a de quem
        -- tem 95-100% de frequencia (1,0 = igual; 2,0 = o dobro)
        round(safe_divide(safe_divide(p.qtd_registros_nota_baixa, p.qtd_registros),
                          r.taxa_nota_baixa_referencia), 2)
            as risco_relativo_nota_baixa,
        p.qtd_registros < {{ var('tamanho_minimo_amostra') }} as amostra_pequena
    from por_faixa as p
    left join referencia as r
        on p.grupo_etario = r.grupo_etario
)

select * from final