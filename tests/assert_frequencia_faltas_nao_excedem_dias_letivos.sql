-- Regra: as faltas de um periodo nao podem passar do numero de dias letivos do periodo
-- (faltas/dias_letivos <= 1). Analogo, com os dados disponiveis, ao exemplo do enunciado
-- "presenca + ausencia nao deve ultrapassar a carga horaria".
-- Por que importa: uma razao > 1 (ex.: 2,67 = faltar 267% dos dias) e impossivel; o registro
-- distorce a frequencia do aluno e precisa de correcao na origem.
-- EDA (eda/saida_04.txt, a): ~0,07% das linhas, igual em todas as faixas etarias -> erro de
-- registro, nao contagem por aula. Severidade warn: achado de qualidade para a fila de
-- pendencias, nao falha de carga.
{{ config(severity='warn') }}

select
    id_aluno,
    id_turma,
    id_escola,
    disciplina,
    data_inicio,
    data_fim,
    razao_faltas_por_dia
from {{ ref('stg_educacao__frequencia') }}
where razao_faltas_por_dia > 1