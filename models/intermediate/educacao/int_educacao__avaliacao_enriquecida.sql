-- int_educacao__avaliacao_enriquecida
-- Grao: aluno x turma x bimestre (o mesmo do stg_educacao__avaliacao; teste equal_rowcount).
-- Papel: juntar a avaliacao com escola e faixa etaria e aplicar as regras de politica
-- (limites de frequencia). E a base do fato e dos marts de absenteismo e alerta.

with

avaliacao as (
    select * from {{ ref('stg_educacao__avaliacao') }}
),

aluno as (
    select
        id_aluno,
        id_turma as id_turma_matricula,
        faixa_etaria,
        ordem_faixa_etaria
    from {{ ref('stg_educacao__aluno') }}
),

turma_escola as (
    select * from {{ ref('int_educacao__turma_escola') }}
),

aluno_escola as (
    select
        id_aluno,
        id_escola
    from {{ ref('int_educacao__aluno_escola') }}
),

enriquecido as (
    select
        av.id_aluno,
        av.id_turma,
        av.bimestre,

        -- escola: 1o pela turma avaliada (ligacao mais especifica);
        -- se a turma nao tem escola, pela escola de referencia do aluno.
        -- origem_escola registra qual caminho foi usado (como o "nivel de precisao" de um geocoding)
        coalesce(te.id_escola, ae.id_escola) as id_escola,
        case
            when te.id_escola is not null then 'turma'
            when ae.id_escola is not null then 'aluno'
        end as origem_escola,

        al.faixa_etaria,
        al.ordem_faixa_etaria,

        -- EDA 5: troca de turma ao longo do ano (sinal para o alerta, nao erro)
        av.id_turma != al.id_turma_matricula as avaliado_fora_da_turma_matricula,

        -- assiduidade e regras de politica (limites em vars do dbt_project.yml)
        av.frequencia_bimestre_pct,
        av.frequencia_bimestre_pct < {{ var('limite_frequencia_legal') }}    as abaixo_minimo_legal,
        av.frequencia_bimestre_pct < {{ var('limite_absenteismo_cronico') }} as em_absenteismo_cronico,

        -- faltas estimadas no bimestre: (100 - frequencia)% x dias letivos do bimestre.
        -- Premissa: 200 dias letivos/ano (LDB art. 24, I) / 4 = 50 por bimestre (var).
        -- Serve para a regra das 15 faltas (LDB art. 12, VIII; Circular E/SUBAIR 02/2026).
        round((100 - av.frequencia_bimestre_pct) / 100 * {{ var('dias_letivos_bimestre') }}, 1)
            as faltas_estimadas_bimestre,

        av.nota_disciplina_1,
        av.nota_disciplina_2,
        av.nota_disciplina_3,
        av.nota_disciplina_4,

        -- desempenho no bimestre (disciplina_3 e 100% nula; nulos ficam fora da media)
        (if(av.nota_disciplina_1 is null, 0, 1) + if(av.nota_disciplina_2 is null, 0, 1)
         + if(av.nota_disciplina_3 is null, 0, 1) + if(av.nota_disciplina_4 is null, 0, 1))
            as qtd_disciplinas_com_nota,
        safe_divide(
            coalesce(av.nota_disciplina_1, 0) + coalesce(av.nota_disciplina_2, 0)
            + coalesce(av.nota_disciplina_3, 0) + coalesce(av.nota_disciplina_4, 0),
            if(av.nota_disciplina_1 is null, 0, 1) + if(av.nota_disciplina_2 is null, 0, 1)
            + if(av.nota_disciplina_3 is null, 0, 1) + if(av.nota_disciplina_4 is null, 0, 1)
        ) as nota_media_bimestre,
        -- nota baixa = alguma disciplina abaixo do limite (equivalente ao "failing a course" de
        -- Balfanz). Nulo se o aluno nao tem nenhuma nota no bimestre.
        case
            when av.nota_disciplina_1 is null and av.nota_disciplina_2 is null
             and av.nota_disciplina_3 is null and av.nota_disciplina_4 is null then null
            else coalesce(av.nota_disciplina_1 < {{ var('limite_nota_baixa') }}, false)
              or coalesce(av.nota_disciplina_2 < {{ var('limite_nota_baixa') }}, false)
              or coalesce(av.nota_disciplina_3 < {{ var('limite_nota_baixa') }}, false)
              or coalesce(av.nota_disciplina_4 < {{ var('limite_nota_baixa') }}, false)
        end as tem_nota_baixa,

        -- rastreabilidade da qualidade (vem do staging)
        av.qtd_versoes_distintas,
        av.registro_conflitante

    from avaliacao as av
    left join aluno as al
        on av.id_aluno = al.id_aluno
    left join turma_escola as te
        on av.id_turma = te.id_turma
    left join aluno_escola as ae
        on av.id_aluno = ae.id_aluno
)

select * from enriquecido