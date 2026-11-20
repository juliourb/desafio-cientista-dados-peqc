-- mart_educacao__pendencias_qualidade_escola
-- Grao: 1 linha por escola com pendencia (mais 1 linha com escola nula = pendencias centrais,
-- de responsabilidade da Secretaria, como turmas sem escola no cadastro).
-- Quem usa: Secretaria, para distribuir as pendencias e acompanhar a correcao por escola.
-- Para decidir: por quais escolas comecar (ranking_pendencias: 1 = mais pendencias).

with

pendencias as (
    select * from {{ ref('mart_educacao__pendencias_qualidade') }}
),

por_escola as (
    select
        id_escola,
        count(*)                                                       as qtd_pendencias,
        countif(tipo_pendencia = 'frequencia_versoes_conflitantes')    as qtd_frequencia_versoes_conflitantes,
        countif(tipo_pendencia = 'faltas_acima_dias_letivos')          as qtd_faltas_acima_dias_letivos,
        countif(tipo_pendencia = 'avaliacao_versoes_conflitantes')     as qtd_avaliacao_versoes_conflitantes,
        countif(tipo_pendencia = 'nota_com_frequencia_zero')           as qtd_nota_com_frequencia_zero,
        countif(tipo_pendencia = 'avaliado_fora_da_turma_matricula')   as qtd_avaliado_fora_da_turma_matricula,
        countif(tipo_pendencia = 'turma_sem_escola')                   as qtd_turma_sem_escola,
        count(distinct id_turma)                                       as qtd_turmas_com_pendencia
    from pendencias
    group by id_escola
)

select
    id_escola,
    id_escola is not null as escola_identificada,
    -- ranking so entre escolas identificadas; a linha sem escola e da Secretaria
    case
        when id_escola is not null then
            rank() over (partition by id_escola is null order by qtd_pendencias desc)
    end as ranking_pendencias,
    qtd_pendencias,
    qtd_frequencia_versoes_conflitantes,
    qtd_faltas_acima_dias_letivos,
    qtd_avaliacao_versoes_conflitantes,
    qtd_nota_com_frequencia_zero,
    qtd_avaliado_fora_da_turma_matricula,
    qtd_turma_sem_escola,
    qtd_turmas_com_pendencia
from por_escola
