-- Regra: na educacao infantil (faixa 0-5) nao ha nota. A LDB (art. 31, I) define a avaliacao
-- nessa etapa como acompanhamento e registro do desenvolvimento, sem objetivo de promocao.
-- Por que importa: nota lancada para crianca de 0-5 indica faixa etaria errada no cadastro ou
-- lancamento indevido - e entraria no alerta precoce como "media baixa".
-- EDA (eda/saida_04.txt, b1): 3.483 alunos de 0-5 avaliados no 1o bimestre.
-- Severidade warn: achado de qualidade (fila de pendencias), nao falha de carga.
{{ config(severity='warn') }}

select
    id_aluno,
    id_turma,
    id_escola,
    bimestre,
    faixa_etaria,
    qtd_disciplinas_com_nota,
    nota_media_bimestre
from {{ ref('fct_educacao__avaliacao_bimestre') }}
where faixa_etaria = '0-5'
  and qtd_disciplinas_com_nota > 0