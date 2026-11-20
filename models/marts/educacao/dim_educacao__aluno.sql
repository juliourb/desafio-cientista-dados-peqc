-- dim_educacao__aluno
-- Grao: 1 linha por aluno (97.044).
-- Papel: atributos do aluno que dao contexto aos fatos e ao alerta. Nenhum dado
-- identificavel: id_aluno e hash, bairro e hash (salt diferente do bairro da escola).
-- Escola de matricula pela turma de matricula (nula se a turma nao tem escola conhecida).
-- Mobilidade (troca de escola) nao e calculavel: so existiria na frequencia, onde a relacao
-- aluno -> escola foi randomizada (eda/saida_05.txt).

with

aluno as (
    select * from {{ ref('stg_educacao__aluno') }}
),

escola_referencia as (
    select * from {{ ref('int_educacao__aluno_escola') }}
),

avaliacoes as (
    select
        id_aluno,
        count(distinct bimestre) as qtd_bimestres_avaliados,
        min(bimestre)            as primeiro_bimestre_avaliado,
        max(bimestre)            as ultimo_bimestre_avaliado
    from {{ ref('int_educacao__avaliacao_enriquecida') }}
    group by id_aluno
),

final as (
    select
        a.id_aluno,
        a.faixa_etaria,
        a.ordem_faixa_etaria,
        a.bairro_residencia_hash,
        e.id_turma_matricula,
        e.id_escola                        as id_escola_matricula,
        av.id_aluno is not null            as possui_avaliacao,
        coalesce(av.qtd_bimestres_avaliados, 0) as qtd_bimestres_avaliados,
        av.primeiro_bimestre_avaliado,
        av.ultimo_bimestre_avaliado
    from aluno as a
    left join escola_referencia as e
        on a.id_aluno = e.id_aluno
    left join avaliacoes as av
        on a.id_aluno = av.id_aluno
)

select * from final