-- Teste generico customizado: validador de chaves de ligacao.
-- Compara duas colunas que DEVERIAM apontar para o mesmo valor (ex.: a escola obtida por
-- duas rotas diferentes) e falha se a concordancia, entre as linhas em que as duas existem,
-- ficar abaixo de minimo_pct. Devolve 1 linha (com os numeros) quando falha.
-- Por que existe: na analise de chaves, uma rota aparentemente valida (aluno -> escola pela
-- frequencia) concordava em 0,3% com a rota da turma. Este teste detecta esse tipo de
-- quebra automaticamente em cargas futuras.
{% test concordancia_minima(model, column_name, coluna_comparacao, minimo_pct) %}

with

pares as (
    select
        {{ column_name }}       as valor_a,
        {{ coluna_comparacao }} as valor_b
    from {{ model }}
    where {{ column_name }} is not null
      and {{ coluna_comparacao }} is not null
),

resumo as (
    select
        count(*)                                       as qtd_pares,
        sum(case when valor_a = valor_b then 1 else 0 end) as qtd_iguais
    from pares
)

select
    qtd_pares,
    qtd_iguais,
    round(100.0 * qtd_iguais / nullif(qtd_pares, 0), 2) as pct_concordancia
from resumo
where qtd_pares = 0
   or 100.0 * qtd_iguais / qtd_pares < {{ minimo_pct }}

{% endtest %}
