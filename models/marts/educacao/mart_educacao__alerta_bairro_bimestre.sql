-- mart_educacao__alerta_bairro_bimestre
-- Grao: bairro de residencia (hash) x bimestre.
-- Quem usa: equipes de busca ativa e parceiros territoriais (Programa Bora pra Escola;
-- Circular E/SUBAIR 02/2026: associacoes de moradores e demais parceiros territoriais).
-- Para decidir: em quais territorios concentrar a busca ativa no bimestre.
-- ranking_prioridade: 1 = bairro com mais alunos em "alto"; empates desfeitos por "medio"
-- e depois por "atencao" (rank: empates totais recebem a mesma posicao).
-- Inclui alunos com escola nao identificada: para eles, o territorio e o unico caminho.
-- Bairro em hash: a Secretaria (dona do salt) converte no bairro real. Nunca reidentificamos.

with

alerta as (
    select * from {{ ref('mart_educacao__alerta_precoce_aluno_bimestre') }}
),

por_bairro as (
    select
        bairro_residencia_hash,
        bimestre,
        count(distinct id_aluno)                                    as qtd_alunos_avaliados,
        countif(nivel_alerta = 'alto')                              as qtd_alunos_alto,
        countif(nivel_alerta = 'medio')                             as qtd_alunos_medio,
        countif(nivel_alerta = 'atencao')                           as qtd_alunos_atencao,
        countif(comunicar_conselho_tutelar)                         as qtd_alunos_comunicar_conselho_tutelar,
        countif(nivel_alerta = 'alto' and not escola_identificada)  as qtd_alunos_alto_sem_escola,
        count(distinct id_escola)                                   as qtd_escolas
    from alerta
    group by bairro_residencia_hash, bimestre
),

final as (
    select
        bairro_residencia_hash,
        bimestre,
        bairro_residencia_hash is not null as bairro_informado,
        rank() over (
            partition by bimestre
            order by qtd_alunos_alto desc, qtd_alunos_medio desc, qtd_alunos_atencao desc
        ) as ranking_prioridade,
        qtd_alunos_avaliados,
        qtd_alunos_alto,
        qtd_alunos_medio,
        qtd_alunos_atencao,
        round(100 * safe_divide(qtd_alunos_alto, qtd_alunos_avaliados), 1) as pct_alunos_alto,
        qtd_alunos_comunicar_conselho_tutelar,
        qtd_alunos_alto_sem_escola,
        qtd_escolas,
        -- poucos alunos: percentual instavel (sinalizado, nao escondido; o consumidor e a
        -- equipe de busca ativa, que precisa ver todos os territorios)
        qtd_alunos_avaliados < {{ var('tamanho_minimo_amostra') }} as amostra_pequena
    from por_bairro
)

select * from final
