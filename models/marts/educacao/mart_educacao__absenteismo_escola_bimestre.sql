-- mart_educacao__absenteismo_escola_bimestre
-- Grao: escola x bimestre.
-- Quem usa: coordenacao regional / gestao da rede.
-- Para decidir: em quais escolas concentrar busca ativa e acompanhamento no proximo
-- bimestre (frequencia abaixo do minimo legal e absenteismo cronico).
-- Leitura obrigatoria: qtd_alunos_avaliados e pct_alunos_15_17 mostram QUEM esta na base
-- (eda/saida_04.txt, b e c: a avaliacao cobre sobretudo 15-17, e mais ainda no 4o bimestre).

with

fato as (
    select * from {{ ref('fct_educacao__avaliacao_bimestre') }}
),

escola as (
    select
        id_escola,
        bairro_escola_hash
    from {{ ref('dim_educacao__escola') }}
),

por_escola_bimestre as (
    select
        id_escola,
        bimestre,

        -- base
        count(distinct id_aluno)                                         as qtd_alunos_avaliados,
        count(distinct case when faixa_etaria = '15-17' then id_aluno end) as qtd_alunos_15_17,

        -- assiduidade
        round(avg(frequencia_bimestre_pct), 1)                           as frequencia_media_pct,
        count(distinct case when abaixo_minimo_legal then id_aluno end)    as qtd_alunos_abaixo_minimo_legal,
        count(distinct case when em_absenteismo_cronico then id_aluno end) as qtd_alunos_absenteismo_cronico,

        -- qualidade / precisao da ligacao com a escola
        countif(origem_escola = 'aluno')                                 as qtd_registros_escola_via_aluno,
        count(*)                                                         as qtd_registros
    from fato
    group by id_escola, bimestre
),

final as (
    select
        p.id_escola,
        p.bimestre,
        e.bairro_escola_hash,

        p.qtd_alunos_avaliados,
        round(100 * safe_divide(p.qtd_alunos_15_17, p.qtd_alunos_avaliados), 1) as pct_alunos_15_17,

        p.frequencia_media_pct,
        p.qtd_alunos_abaixo_minimo_legal,
        round(100 * safe_divide(p.qtd_alunos_abaixo_minimo_legal, p.qtd_alunos_avaliados), 1)
            as pct_alunos_abaixo_minimo_legal,
        p.qtd_alunos_absenteismo_cronico,
        round(100 * safe_divide(p.qtd_alunos_absenteismo_cronico, p.qtd_alunos_avaliados), 1)
            as pct_alunos_absenteismo_cronico,

        -- numeros pequenos: 1 aluno em 3 vira "33%". Taxa instavel -> sinalizada, nao escondida
        p.qtd_alunos_avaliados < {{ var('tamanho_minimo_amostra') }} as amostra_pequena,

        round(100 * safe_divide(p.qtd_registros_escola_via_aluno, p.qtd_registros), 1)
            as pct_registros_escola_via_aluno
    from por_escola_bimestre as p
    left join escola as e
        on p.id_escola = e.id_escola
)

select * from final