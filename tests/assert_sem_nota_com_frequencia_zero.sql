-- Regra: aluno com 0% de frequencia no bimestre nao deveria ter nota lancada no mesmo
-- bimestre (nao houve presenca para ser avaliado).
-- Por que importa: e inconsistencia entre o diario de frequencia e o de notas - um dos dois
-- esta errado. Se a frequencia estiver errada, o aluno entra indevidamente em "alto";
-- se a nota estiver errada, ha lancamento automatico ou indevido.
-- Curva frequencia x desempenho: poucos registros na faixa 0-5% (~10).
-- Severidade warn: achado de qualidade (fila de pendencias).
{{ config(severity='warn') }}

select
    id_aluno,
    id_turma,
    id_escola,
    bimestre,
    frequencia_bimestre_pct,
    qtd_disciplinas_com_nota,
    nota_media_bimestre
from {{ ref('fct_educacao__avaliacao_bimestre') }}
where frequencia_bimestre_pct = 0
  and qtd_disciplinas_com_nota > 0