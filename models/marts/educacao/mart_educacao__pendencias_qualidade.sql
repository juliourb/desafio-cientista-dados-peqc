-- mart_educacao__pendencias_qualidade
-- Grao: 1 linha por pendencia de qualidade (um registro ou turma que viola uma regra).
-- Quem usa: Secretaria (dona do dado e do salt da anonimizacao), que distribui as pendencias
-- as escolas e corrige o que e central (cadastro de turmas).
-- Para decidir: o que corrigir na ORIGEM, por quem e em qual escola. Fecha o ciclo de retorno:
-- o pipeline trata e sinaliza (pior caso, flags), mas a correcao definitiva e na fonte.
-- Padrao adotado: sinalizacao + fila de pendencias (o registro segue no fluxo); nao e quarentena.
-- Fora da fila, de proposito: frequencia sem vinculo de matricula (105.922 pares) - e efeito da
-- randomizacao da extracao (eda/saida_05.txt), nao erro corrigivel na escola.
-- Obs.: nas pendencias vindas da frequencia, id_aluno identifica a linha da propria frequencia;
-- ele nao pode ser cruzado com as demais tabelas (associacao aluno x turma randomizada).

with

frequencia as (
    select * from {{ ref('stg_educacao__frequencia') }}
),

avaliacao as (
    select * from {{ ref('int_educacao__avaliacao_enriquecida') }}
),

-- 1. frequencia: mais de uma versao para o mesmo aluno, turma, disciplina e periodo
frequencia_conflitante as (
    select
        'frequencia_versoes_conflitantes' as tipo_pendencia,
        'unicidade'   as dimensao_qualidade,
        'Um registro por aluno, turma, disciplina e periodo' as regra,
        'escola'      as responsavel_correcao,
        'Confirmar qual lancamento de frequencia e o correto e excluir o outro' as acao_sugerida,
        'frequencia'  as tabela_origem,
        id_escola, id_turma, id_aluno,
        cast(null as int64) as bimestre,
        disciplina, data_inicio, data_fim,
        concat(cast(qtd_versoes_distintas as string), ' versoes; o pipeline adotou o menor valor (pior caso)') as detalhe
    from frequencia
    where registro_conflitante
),

-- 2. frequencia: faltas acima dos dias letivos do periodo (razao faltas/dia > 1)
faltas_acima_dias_letivos as (
    select
        'faltas_acima_dias_letivos', 'validade',
        'Faltas no periodo <= dias letivos do periodo',
        'escola',
        'Corrigir as faltas ou os dias letivos lancados para o periodo',
        'frequencia',
        id_escola, id_turma, id_aluno,
        cast(null as int64),
        disciplina, data_inicio, data_fim,
        concat('razao faltas/dia = ', format('%.2f', razao_faltas_por_dia))
    from frequencia
    where razao_faltas_por_dia > 1
),

-- 3. avaliacao: mais de uma versao para o mesmo aluno, turma e bimestre
avaliacao_conflitante as (
    select
        'avaliacao_versoes_conflitantes', 'unicidade',
        'Um registro por aluno, turma e bimestre',
        'escola',
        'Confirmar as notas e a frequencia corretas do bimestre',
        'avaliacao',
        id_escola, id_turma, id_aluno,
        bimestre,
        cast(null as string), cast(null as date), cast(null as date),
        concat(cast(qtd_versoes_distintas as string), ' versoes; o pipeline adotou o menor valor (pior caso)')
    from avaliacao
    where registro_conflitante
),

-- 4. avaliacao: nota lancada com 0% de frequencia no bimestre
nota_com_frequencia_zero as (
    select
        'nota_com_frequencia_zero', 'consistencia',
        'Aluno sem presenca no bimestre nao deveria ter nota',
        'escola',
        'Conferir o diario de frequencia e o diario de notas do bimestre',
        'avaliacao',
        id_escola, id_turma, id_aluno,
        bimestre,
        cast(null as string), cast(null as date), cast(null as date),
        concat('notas lancadas em ', cast(qtd_disciplinas_com_nota as string), ' disciplina(s)')
    from avaliacao
    where frequencia_bimestre_pct = 0
      and qtd_disciplinas_com_nota > 0
),

-- 5. avaliacao: aluno avaliado em turma diferente da turma de matricula (1 linha por par)
avaliado_fora_da_turma as (
    select
        'avaliado_fora_da_turma_matricula', 'consistencia',
        'O aluno e avaliado na turma em que esta matriculado',
        'escola',
        'Atualizar a enturmacao (matricula) ou corrigir a turma da avaliacao',
        'avaliacao',
        any_value(id_escola), id_turma, id_aluno,
        cast(null as int64),
        cast(null as string), cast(null as date), cast(null as date),
        concat('bimestres: ', string_agg(cast(bimestre as string), ',' order by bimestre))
    from avaliacao
    where avaliado_fora_da_turma_matricula
    group by id_aluno, id_turma
),

-- 6. cadastro: turma avaliada sem escola conhecida (1 linha por turma)
turma_sem_escola as (
    select
        'turma_sem_escola', 'completude',
        'Toda turma tem escola no cadastro de turmas',
        'secretaria',
        'Vincular a turma a sua escola no cadastro de turmas',
        'avaliacao',
        cast(null as int64), id_turma, cast(null as string),
        cast(null as int64),
        cast(null as string), cast(null as date), cast(null as date),
        concat(cast(count(*) as string), ' registros de avaliacao de ',
               cast(count(distinct id_aluno) as string), ' alunos sem escola identificada')
    from avaliacao
    where id_escola is null
    group by id_turma
),

unidas as (
    select * from frequencia_conflitante
    union all select * from faltas_acima_dias_letivos
    union all select * from avaliacao_conflitante
    union all select * from nota_com_frequencia_zero
    union all select * from avaliado_fora_da_turma
    union all select * from turma_sem_escola
)

select
    {{ dbt_utils.generate_surrogate_key([
        'tipo_pendencia', 'id_aluno', 'id_turma', 'id_escola',
        'bimestre', 'disciplina', 'data_inicio', 'data_fim'
    ]) }} as id_pendencia,
    *
from unidas
