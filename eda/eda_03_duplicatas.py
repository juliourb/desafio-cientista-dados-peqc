r"""
EDA parte 3 - duplicatas CONFLITANTES no grao (as que sobraram depois do DISTINCT).
Pergunta: o que muda entre as linhas repetidas? Isso decide a regra de dedup.
Rodar a partir da raiz do repo:  python -X utf8 eda\eda_03_duplicatas.py
"""
import duckdb

con = duckdb.connect()
for t in ["frequencia", "avaliacao"]:
    con.sql(f"CREATE VIEW {t} AS SELECT DISTINCT * FROM 'data/{t}.parquet'")  # igual ao staging


def q(titulo, sql):
    print(f"\n### {titulo}")
    con.sql(sql).show(max_width=250)


q("1. FREQUENCIA: quais colunas variam dentro do mesmo grao (aluno, turma, disciplina, data_inicio)?", """
    WITH g AS (
        SELECT id_aluno, id_turma, disciplina, data_inicio,
               COUNT(*)                   AS n,
               COUNT(DISTINCT id_escola)  AS n_escola,
               COUNT(DISTINCT data_fim)   AS n_data_fim,
               COUNT(DISTINCT frequencia) AS n_freq,
               MAX(frequencia) - MIN(frequencia) AS dif_freq
        FROM frequencia GROUP BY ALL HAVING COUNT(*) > 1
    )
    SELECT COUNT(*)                   AS grupos_conflitantes,
           MAX(n)                     AS max_linhas_por_grupo,
           COUNT_IF(n_escola > 1)     AS varia_escola,
           COUNT_IF(n_data_fim > 1)   AS varia_data_fim,
           COUNT_IF(n_freq > 1)       AS varia_frequencia,
           ROUND(MAX(dif_freq), 4)    AS maior_dif_frequencia
    FROM g
""")

q("2. FREQUENCIA: 5 exemplos", """
    WITH g AS (
        SELECT id_aluno, id_turma, disciplina, data_inicio
        FROM frequencia GROUP BY ALL HAVING COUNT(*) > 1 LIMIT 5
    )
    SELECT f.id_turma, f.disciplina, f.data_inicio, f.data_fim, f.id_escola, f.frequencia
    FROM frequencia f JOIN g USING (id_aluno, id_turma, disciplina, data_inicio)
    ORDER BY f.id_turma, f.disciplina, f.data_inicio
""")

q("3. AVALIACAO: quais colunas variam dentro do mesmo grao (aluno, turma, bimestre)?", """
    WITH g AS (
        SELECT id_aluno, id_turma, bimestre,
               COUNT(*) AS n,
               COUNT(DISTINCT frequencia)   AS n_freq,
               COUNT(DISTINCT disciplina_1) AS n_d1,
               COUNT(DISTINCT disciplina_2) AS n_d2,
               COUNT(DISTINCT disciplina_4) AS n_d4,
               COUNT_IF(frequencia IS NULL)   AS freq_nula,
               COUNT_IF(disciplina_1 IS NULL) AS d1_nula
        FROM avaliacao GROUP BY ALL HAVING COUNT(*) > 1
    )
    SELECT COUNT(*)              AS grupos_conflitantes,
           MAX(n)                AS max_linhas_por_grupo,
           COUNT_IF(n_freq > 1)  AS varia_frequencia,
           COUNT_IF(n_d1 > 1 OR n_d2 > 1 OR n_d4 > 1) AS varia_alguma_nota,
           COUNT_IF(freq_nula BETWEEN 1 AND n - 1)   AS uma_freq_nula_outra_nao,
           COUNT_IF(d1_nula  BETWEEN 1 AND n - 1)    AS uma_nota1_nula_outra_nao
    FROM g
""")

q("4. AVALIACAO: 5 exemplos", """
    WITH g AS (
        SELECT id_aluno, id_turma, bimestre
        FROM avaliacao GROUP BY ALL HAVING COUNT(*) > 1 LIMIT 5
    )
    SELECT a.id_turma, a.bimestre, a.frequencia, a.disciplina_1, a.disciplina_2, a.disciplina_4
    FROM avaliacao a JOIN g USING (id_aluno, id_turma, bimestre)
    ORDER BY a.id_turma, a.bimestre
""")