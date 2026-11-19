-- fct_educacao__avaliacao_bimestre
-- Grao: aluno x turma x bimestre (1 medicao bimestral de frequencia e notas).
-- Papel: tabela fato = os eventos medidos, com chaves para as dimensoes e as medidas.
-- E o "contrato publico" da camada gold: o intermediate pode mudar por dentro,
-- o fato mantem nome, grao e colunas.
-- faixa_etaria fica aqui por enquanto (atributo do aluno); vai para dim_educacao__aluno
-- quando o mart de alerta precoce for criado.

with

avaliacao as (
    select * from {{ ref('int_educacao__avaliacao_enriquecida') }}
),

final as (
    select
        -- chaves (ligam o fato as dimensoes)
        id_aluno,
        id_turma,
        id_escola,
        bimestre,

        -- atributos de contexto
        origem_escola,
        faixa_etaria,
        ordem_faixa_etaria,
        avaliado_fora_da_turma_matricula,

        -- medidas
        frequencia_bimestre_pct,
        abaixo_minimo_legal,
        em_absenteismo_cronico,
        nota_disciplina_1,
        nota_disciplina_2,
        nota_disciplina_3,
        nota_disciplina_4,

        -- qualidade
        registro_conflitante
    from avaliacao
)

select * from final