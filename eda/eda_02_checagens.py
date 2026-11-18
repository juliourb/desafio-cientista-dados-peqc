r"""
EDA parte 2 - checagens de chaves, relacoes e distribuicoes (DuckDB 2.x).
Cada bloco responde a uma pergunta que decide algo no staging ou nos marts.
Rodar a partir da raiz do repo:  python -X utf8 eda\eda_02_checagens.py
"""
import duckdb

con = duckdb.connect()
for t in ["aluno", "escola", "turma", "frequencia", "avaliacao"]:
    # VIEW = atalho com nome, igual a uma camada virtual no QGIS
    con.sql(f"CREATE VIEW {t} AS SELECT * FROM 'data/{t}.parquet'")


def q(titulo, sql):
    print(f"\n### {titulo}")
    con.sql(sql).show(max_width=250)


q("1. Unicidade das chaves (linhas = distintos -> chave unica)", """
    SELECT 'aluno: id_aluno' AS chave, COUNT(*) AS linhas, COUNT(DISTINCT id_aluno) AS distintos FROM aluno
    UNION ALL SELECT 'escola: id_escola', COUNT(*), COUNT(DISTINCT id_escola) FROM escola
    UNION ALL SELECT 'turma: id_aluno', COUNT(*), COUNT(DISTINCT id_aluno) FROM turma
    UNION ALL SELECT 'turma: (id_turma, id_aluno)', COUNT(*), COUNT(DISTINCT (id_turma, id_aluno)) FROM turma
    UNION ALL SELECT 'frequencia: (aluno, turma, disciplina, data_inicio)', COUNT(*),
                     COUNT(DISTINCT (id_aluno, id_turma, disciplina, data_inicio)) FROM frequencia
    UNION ALL SELECT 'avaliacao: (aluno, turma, bimestre)', COUNT(*),
                     COUNT(DISTINCT (id_aluno, id_turma, bimestre)) FROM avaliacao
""")

q("2. aluno x turma: os pares (id_aluno, id_turma) sao os mesmos?", """
    SELECT (SELECT COUNT(*) FROM aluno ANTI JOIN turma USING (id_aluno, id_turma)) AS aluno_sem_par_em_turma,
           (SELECT COUNT(*) FROM turma ANTI JOIN aluno USING (id_aluno, id_turma)) AS turma_sem_par_em_aluno
""")

q("3. Orfaos e cobertura (ANTI JOIN = 'esta em A e nao esta em B')", """
    SELECT 'escolas da frequencia fora de escola' AS checagem,
           (SELECT COUNT(DISTINCT id_escola) FROM frequencia ANTI JOIN escola USING (id_escola)) AS qtd
    UNION ALL SELECT 'escolas de escola sem nenhuma frequencia',
           (SELECT COUNT(DISTINCT id_escola) FROM escola ANTI JOIN frequencia USING (id_escola))
    UNION ALL SELECT 'alunos da frequencia fora de aluno',
           (SELECT COUNT(DISTINCT id_aluno) FROM frequencia ANTI JOIN aluno USING (id_aluno))
    UNION ALL SELECT 'alunos da avaliacao fora de aluno',
           (SELECT COUNT(DISTINCT id_aluno) FROM avaliacao ANTI JOIN aluno USING (id_aluno))
    UNION ALL SELECT 'pares (aluno, turma) da avaliacao fora de turma',
           (SELECT COUNT(*) FROM (SELECT DISTINCT id_aluno, id_turma FROM avaliacao) ANTI JOIN turma USING (id_aluno, id_turma))
    UNION ALL SELECT 'alunos sem nenhuma frequencia',
           (SELECT COUNT(DISTINCT id_aluno) FROM aluno ANTI JOIN frequencia USING (id_aluno))
    UNION ALL SELECT 'alunos sem nenhuma avaliacao',
           (SELECT COUNT(DISTINCT id_aluno) FROM aluno ANTI JOIN avaliacao USING (id_aluno))
""")

q("4. Cada turma pertence a UMA escola? (turma nao tem id_escola; so a frequencia liga as duas)", """
    SELECT n_escolas, COUNT(*) AS turmas
    FROM (SELECT id_turma, COUNT(DISTINCT id_escola) AS n_escolas FROM frequencia GROUP BY id_turma)
    GROUP BY n_escolas ORDER BY n_escolas
""")

q("5. Bairro: o hash do aluno e o da escola falam a mesma lingua?", """
    SELECT COUNT(DISTINCT bairro) AS bairros_aluno,
           COUNT(DISTINCT bairro) FILTER (WHERE bairro IN (SELECT bairro FROM escola)) AS em_comum_com_escola,
           (SELECT COUNT(DISTINCT bairro) FROM escola) AS bairros_escola
    FROM aluno
""")

q("6. Faixa etaria (distribuicao)", """
    SELECT faixa_etaria, COUNT(*) AS alunos FROM aluno GROUP BY ALL ORDER BY alunos DESC
""")

q("7. Frequencia (tabela): periodos", """
    SELECT data_inicio, data_fim, COUNT(*) AS linhas, COUNT(DISTINCT id_aluno) AS alunos
    FROM frequencia GROUP BY ALL ORDER BY data_inicio
""")

q("8. Frequencia (tabela): valores mais comuns", """
    SELECT frequencia, COUNT(*) AS linhas,
           ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
    FROM frequencia GROUP BY ALL ORDER BY linhas DESC LIMIT 12
""")

q("9. Frequencia (avaliacao, por bimestre): faixas de politica (75% = minimo legal da LDB)", """
    SELECT CASE WHEN frequencia IS NULL THEN '0 nulo'
                WHEN frequencia < 75 THEN '1 abaixo de 75'
                WHEN frequencia < 90 THEN '2 de 75 a 90'
                ELSE '3 90 ou mais' END AS faixa,
           COUNT(*) AS linhas,
           ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
    FROM avaliacao GROUP BY ALL ORDER BY faixa
""")

q("10. Avaliacao por bimestre", """
    SELECT bimestre, COUNT(*) AS linhas, COUNT(DISTINCT id_aluno) AS alunos
    FROM avaliacao GROUP BY ALL ORDER BY bimestre
""")

q("11. Notas: distribuicao da nota arredondada (disciplina_1)", """
    SELECT ROUND(disciplina_1) AS nota, COUNT(*) AS linhas
    FROM avaliacao WHERE disciplina_1 IS NOT NULL GROUP BY ALL ORDER BY nota
""")

q("12. Ruido: a parte 'quebrada' da nota e igual entre disciplinas na mesma linha?", """
    SELECT COUNT(*) AS linhas_com_d1_e_d2,
           COUNT(*) FILTER (WHERE ROUND(disciplina_1 - ROUND(disciplina_1), 2)
                                = ROUND(disciplina_2 - ROUND(disciplina_2), 2)) AS ruido_igual
    FROM avaliacao WHERE disciplina_1 IS NOT NULL AND disciplina_2 IS NOT NULL
""")