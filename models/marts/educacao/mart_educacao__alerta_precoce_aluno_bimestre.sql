-- mart_educacao__alerta_precoce_aluno_bimestre
-- Grao: aluno x bimestre.
-- Quem usa: direcao da escola, Agente de Frequencia, CIPE e CRE (Programa Bora pra Escola).
-- Visao territorial (por bairro de residencia): mart_educacao__alerta_bairro_bimestre.
-- Para decidir: quem procurar primeiro (busca ativa), com quem fazer atendimento
-- individualizado e quem acompanhar - e quais casos a lei manda comunicar ao Conselho Tutelar.
-- Regras (limites em vars; fontes no README):
--   alto    = freq. acumulada < 75% (SME-Rio: busca ativa; LDB: reprovacao)
--             OU freq. acumulada < 85% E media do bimestre < 5
--   medio   = freq. acumulada < 85% (SME-Rio: atendimento individualizado) OU media < 5
--   atencao = queda de 5 p.p. ou mais na frequencia em relacao ao bimestre anterior
--   comunicar_conselho_tutelar = 15+ faltas estimadas acumuladas (LDB art. 12, VIII;
--             Circular E/SUBAIR 02/2026) - obrigacao legal, coluna separada do nivel.
-- Limite: sem registro diario, as regras de faltas consecutivas (SP: 3; Rio: 1 por semana)
-- nao sao calculaveis. Ausencia de avaliacao apos o 1o bimestre NAO e sinal (recorte da extracao).

with

aluno_bimestre as (
    select * from {{ ref('int_educacao__aluno_bimestre') }}
),

aluno as (
    select
        id_aluno,
        faixa_etaria,
        bairro_residencia_hash,
        qtd_bimestres_avaliados
    from {{ ref('dim_educacao__aluno') }}
),

sinais as (
    select
        ab.*,
        al.faixa_etaria,
        al.bairro_residencia_hash,
        al.qtd_bimestres_avaliados,

        coalesce(ab.frequencia_acumulada_pct < {{ var('limite_frequencia_legal') }}, false)
            as sinal_frequencia_busca_ativa,
        coalesce(ab.frequencia_acumulada_pct < {{ var('limite_frequencia_atendimento') }}, false)
            as sinal_frequencia_atendimento,
        coalesce(ab.nota_media_baixa, false)
            as sinal_nota_baixa,
        coalesce(ab.variacao_frequencia_pp <= -{{ var('limite_queda_frequencia_pp') }}, false)
            as sinal_queda_frequencia,
        coalesce(ab.faltas_estimadas_acumuladas >= {{ var('limite_faltas_conselho_tutelar') }}, false)
            as comunicar_conselho_tutelar
    from aluno_bimestre as ab
    left join aluno as al
        on ab.id_aluno = al.id_aluno
),

classificado as (
    select
        *,
        case
            when sinal_frequencia_busca_ativa                      then 'alto'
            when sinal_frequencia_atendimento and sinal_nota_baixa then 'alto'
            when sinal_frequencia_atendimento or sinal_nota_baixa  then 'medio'
            when sinal_queda_frequencia                            then 'atencao'
            else 'sem_alerta'
        end as nivel_alerta
    from sinais
)

select
    id_aluno,
    bimestre,
    id_escola,
    -- escola nula = nao identificada com seguranca (README, analise de chaves): o aluno
    -- continua na lista; a Secretaria resolve a escola com a chave real
    id_escola is not null as escola_identificada,
    -- territorio de residencia (hash): permite organizar a busca ativa por bairro e
    -- acionar parceiros territoriais (Circular E/SUBAIR 02/2026)
    bairro_residencia_hash,
    faixa_etaria,

    nivel_alerta,
    case nivel_alerta
        when 'alto' then 1 when 'medio' then 2 when 'atencao' then 3 else 4
    end as ordem_nivel_alerta,
    -- transparencia: por que o aluno esta neste nivel (nulos sao omitidos)
    array_to_string([
        if(sinal_frequencia_busca_ativa, 'frequencia acumulada abaixo de {{ var("limite_frequencia_legal") }}%', null),
        if(sinal_frequencia_atendimento and not sinal_frequencia_busca_ativa,
           'frequencia acumulada abaixo de {{ var("limite_frequencia_atendimento") }}%', null),
        if(sinal_nota_baixa, 'media do bimestre abaixo de {{ var("limite_nota_baixa") }}', null),
        if(sinal_queda_frequencia, 'queda de frequencia em relacao ao bimestre anterior', null)
    ], '; ') as motivos,
    comunicar_conselho_tutelar,

    -- sinais (sim/nao)
    sinal_frequencia_busca_ativa,
    sinal_frequencia_atendimento,
    sinal_nota_baixa,
    sinal_queda_frequencia,

    -- medidas que sustentam os sinais
    frequencia_bimestre_pct,
    frequencia_acumulada_pct,
    variacao_frequencia_pp,
    faltas_estimadas_acumuladas,
    nota_media_bimestre,
    tem_disciplina_abaixo_limite,

    -- contexto (nao entra na regra)
    qtd_turmas_no_bimestre,
    qtd_bimestres_ate_aqui,
    qtd_bimestres_avaliados,
    registro_conflitante
from classificado