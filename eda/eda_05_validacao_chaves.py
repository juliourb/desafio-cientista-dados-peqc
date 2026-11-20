r"""
EDA parte 5 - validacao das chaves de ligacao aluno -> turma -> escola.
Pergunta: qual caminho permite atribuir a escola de um registro da avaliacao com seguranca?
Resultado esperado (decisao no README, "Analise de chaves"):
  - matricula (turma) e avaliacao concordam entre si;
  - na frequencia, turma -> escola e coerente, mas aluno -> turma/escola foi randomizado.
Rodar a partir da raiz do repo:  python -X utf8 eda\eda_05_validacao_chaves.py > eda\saida_05.txt
"""
import duckdb

con = duckdb.connect()
for t in ["aluno", "turma", "frequencia", "avaliacao"]:
    con.sql(f"CREATE VIEW {t} AS SELECT * FROM 'data/{t}.parquet'")

# ponte turma -> escola (unica relacao da frequencia que usamos)
con.sql("CREATE VIEW turma_escola AS SELECT DISTINCT id_turma, id_escola FROM frequencia")
# escola "do aluno" segundo a frequencia (escola com mais registros do aluno)
con.sql("""
    CREATE VIEW escola_do_aluno_freq AS
    SELECT id_aluno, arg_max(id_escola, n) AS id_escola
    FROM (SELECT id_aluno, id_escola, COUNT(*) AS n FROM frequencia GROUP BY ALL)
    GROUP BY id_aluno
""")


def q(titulo, sql):
    print(f"\n### {titulo}")
    con.sql(sql).show(max_width=250)


# 1. A ponte turma -> escola e coerente? (cada turma em uma unica escola)
q("1. Turmas da frequencia com mais de uma escola (esperado: 0)", """
    SELECT COUNT(*) AS turmas, COUNT(*) FILTER (WHERE n_escolas > 1) AS turmas_com_2_ou_mais_escolas
    FROM (SELECT id_turma, COUNT(DISTINCT id_escola) AS n_escolas FROM frequencia GROUP BY id_turma)
""")

# 2. O par aluno x turma da frequencia e o mesmo da matricula?
q("2. Pares aluno x turma da frequencia que existem na matricula", """
    WITH f AS (SELECT DISTINCT id_aluno, id_turma FROM frequencia)
    SELECT COUNT(*) AS pares_freq,
           COUNT(t.id_aluno) AS pares_que_batem_com_matricula,
           ROUND(100.0 * COUNT(t.id_aluno) / COUNT(*), 3) AS pct
    FROM f LEFT JOIN turma t USING (id_aluno, id_turma)
""")

# 3. Rota 'turma avaliada -> escola' x rota 'turma de matricula -> escola' (ambas pela ponte)
q("3. Concordancia: escola pela turma avaliada x escola pela turma de matricula", """
    SELECT COUNT(*) AS linhas_com_as_duas,
           COUNT(*) FILTER (WHERE t1.id_escola = t2.id_escola) AS iguais,
           ROUND(100.0 * COUNT(*) FILTER (WHERE t1.id_escola = t2.id_escola) / COUNT(*), 1) AS pct_concordancia
    FROM avaliacao av
    JOIN turma_escola t1 ON av.id_turma = t1.id_turma
    JOIN aluno al ON av.id_aluno = al.id_aluno
    JOIN turma_escola t2 ON al.id_turma = t2.id_turma
""")

# 4. Rota 'turma avaliada -> escola' x escola "do aluno" na frequencia
q("4. Concordancia: escola pela turma avaliada x escola do aluno na frequencia (rota descartada)", """
    SELECT COUNT(*) AS linhas_com_as_duas,
           COUNT(*) FILTER (WHERE t1.id_escola = ea.id_escola) AS iguais,
           ROUND(100.0 * COUNT(*) FILTER (WHERE t1.id_escola = ea.id_escola) / COUNT(*), 1) AS pct_concordancia
    FROM avaliacao av
    JOIN turma_escola t1 ON av.id_turma = t1.id_turma
    JOIN escola_do_aluno_freq ea ON av.id_aluno = ea.id_aluno
""")

# 5. Cobertura final da escola nas linhas da avaliacao (rotas validas)
q("5. Cobertura da escola na avaliacao pelas rotas validas", """
    SELECT COUNT(*) AS linhas,
           COUNT(*) FILTER (WHERE t1.id_escola IS NOT NULL) AS via_turma_avaliada,
           COUNT(*) FILTER (WHERE t1.id_escola IS NULL AND t2.id_escola IS NOT NULL) AS via_turma_matricula,
           COUNT(*) FILTER (WHERE t1.id_escola IS NULL AND t2.id_escola IS NULL) AS escola_nao_identificada,
           ROUND(100.0 * COUNT(*) FILTER (WHERE t1.id_escola IS NULL AND t2.id_escola IS NULL) / COUNT(*), 1) AS pct_nao_identificada
    FROM avaliacao av
    LEFT JOIN turma_escola t1 ON av.id_turma = t1.id_turma
    LEFT JOIN aluno al ON av.id_aluno = al.id_aluno
    LEFT JOIN turma_escola t2 ON al.id_turma = t2.id_turma
""")
