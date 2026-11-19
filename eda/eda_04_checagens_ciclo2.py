r"""
EDA parte 4 - checagens rapidas que decidem o intermediate e o mart de absenteismo.
Cada bloco responde a UMA pergunta pendente do DECISOES.md (ciclo 2).
Rodar a partir da raiz do repo:  python -X utf8 eda\eda_04_checagens_ciclo2.py > eda\saida_04.txt
"""
import duckdb

con = duckdb.connect()
for t in ["aluno", "escola", "turma", "frequencia", "avaliacao"]:
    con.sql(f"CREATE VIEW {t} AS SELECT * FROM 'data/{t}.parquet'")


# ordem numerica das faixas (como texto, '6-10' viria depois de '15-17')
ORDEM = """CASE faixa_etaria WHEN '0-5' THEN 1 WHEN '6-10' THEN 2 WHEN '11-14' THEN 3
                             WHEN '15-17' THEN 4 ELSE 5 END"""


def q(titulo, sql):
    print(f"\n### {titulo}")
    con.sql(sql).show(max_width=250, max_rows=60)


# (a) Razao faltas/dia > 1 => faltas contadas por AULA, nao por dia?
#     Hipotese do Julio: depende do ciclo (idade). Se for, cresce nas faixas mais velhas
#     (mais aulas/professores por dia). razao = 100 - valor_bruto (formula decifrada).
q("a. Razao faltas/dia > 1, por faixa etaria (tabela frequencia, bruta)", """
    SELECT a.faixa_etaria,
           COUNT(*)                                              AS linhas,
           COUNT(*) FILTER (WHERE 100 - f.frequencia > 1)        AS linhas_razao_maior_1,
           ROUND(100.0 * COUNT(*) FILTER (WHERE 100 - f.frequencia > 1) / COUNT(*), 2) AS pct_linhas,
           COUNT(DISTINCT f.id_aluno) FILTER (WHERE 100 - f.frequencia > 1)            AS alunos_afetados,
           ROUND(MAX(100 - f.frequencia), 2)                     AS razao_maxima
    FROM frequencia f JOIN aluno a USING (id_aluno)
    GROUP BY ALL ORDER BY MIN(""" + ORDEM.replace("faixa_etaria", "a.faixa_etaria") + """)
""")

# (b) A queda de 66,9 mil (bim 1) para 44,7 mil (bim 4) e evasao ou lacuna de lancamento?
#     Evasao: queda concentrada nas faixas mais velhas (15-17, 18+).
#     Lacuna: queda parecida em todas as faixas (inclusive 6-10, onde evasao e rara).
q("b1. Alunos avaliados por bimestre x faixa etaria (indice: bim 4 / bim 1)", """
    WITH base AS (
        SELECT a.faixa_etaria, CAST(av.bimestre AS INT) AS bim, av.id_aluno
        FROM avaliacao av JOIN aluno a USING (id_aluno)
    )
    SELECT faixa_etaria,
           COUNT(DISTINCT id_aluno) FILTER (WHERE bim = 1) AS bim_1,
           COUNT(DISTINCT id_aluno) FILTER (WHERE bim = 2) AS bim_2,
           COUNT(DISTINCT id_aluno) FILTER (WHERE bim = 3) AS bim_3,
           COUNT(DISTINCT id_aluno) FILTER (WHERE bim = 4) AS bim_4,
           ROUND(100.0 * COUNT(DISTINCT id_aluno) FILTER (WHERE bim = 4)
                 / NULLIF(COUNT(DISTINCT id_aluno) FILTER (WHERE bim = 1), 0), 1) AS pct_bim4_sobre_bim1
    FROM base GROUP BY ALL ORDER BY MIN(""" + ORDEM + """)
""")

# b2. Trajetoria do aluno: quem esta no bim 1 some depois? Ou entra gente nova no meio?
q("b2. Padrao de bimestres por aluno (ex.: '1234' = todos; '1' = so no 1o)", """
    WITH padrao AS (
        SELECT id_aluno, STRING_AGG(DISTINCT bimestre, '' ORDER BY bimestre) AS bimestres
        FROM avaliacao GROUP BY id_aluno
    )
    SELECT bimestres, COUNT(*) AS alunos,
           ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
    FROM padrao GROUP BY ALL ORDER BY alunos DESC LIMIT 12
""")

# (c) Os 27.542 alunos sem avaliacao: 0-5 (educacao infantil nao tem nota) explica o resto?
q("c. Alunos sem nenhuma avaliacao, por faixa etaria", """
    SELECT a.faixa_etaria,
           COUNT(*)                                            AS alunos,
           COUNT(*) FILTER (WHERE av.id_aluno IS NULL)         AS sem_avaliacao,
           ROUND(100.0 * COUNT(*) FILTER (WHERE av.id_aluno IS NULL) / COUNT(*), 1) AS pct_sem_avaliacao
    FROM aluno a
    LEFT JOIN (SELECT DISTINCT id_aluno FROM avaliacao) av USING (id_aluno)
    GROUP BY ALL ORDER BY MIN(""" + ORDEM.replace("faixa_etaria", "a.faixa_etaria") + """)
""")

# (d) O mart por escola depende de turma -> escola (so existe via frequencia).
#     Quantas turmas/linhas da avaliacao conseguem chegar numa escola?
q("d1. Cobertura turma -> escola nas turmas da avaliacao", """
    WITH turma_escola AS (SELECT DISTINCT id_turma, id_escola FROM frequencia)
    SELECT COUNT(DISTINCT av.id_turma)                                   AS turmas_na_avaliacao,
           COUNT(DISTINCT av.id_turma) FILTER (WHERE te.id_escola IS NULL) AS turmas_sem_escola,
           COUNT(*)                                                       AS linhas_avaliacao,
           COUNT(*) FILTER (WHERE te.id_escola IS NULL)                   AS linhas_sem_escola,
           COUNT(DISTINCT te.id_escola)                                   AS escolas_alcancadas
    FROM avaliacao av LEFT JOIN turma_escola te USING (id_turma)
""")

# d2. E os 6.952 pares avaliados fora da turma de matricula: a turma deles tem escola?
#     E a escola e a mesma da turma de matricula? (mesma escola = troca de turma interna)
q("d2. Pares (aluno, turma) da avaliacao fora da tabela turma: escola da turma avaliada x da matricula", """
    WITH turma_escola AS (SELECT DISTINCT id_turma, id_escola FROM frequencia),
    fora AS (
        SELECT DISTINCT av.id_aluno, av.id_turma AS turma_avaliada, t.id_turma AS turma_matricula
        FROM avaliacao av
        JOIN turma t USING (id_aluno)
        WHERE av.id_turma <> t.id_turma
    )
    SELECT COUNT(*)                                               AS pares_fora,
           COUNT(*) FILTER (WHERE ea.id_escola IS NULL)           AS turma_avaliada_sem_escola,
           COUNT(*) FILTER (WHERE ea.id_escola = em.id_escola)    AS mesma_escola,
           COUNT(*) FILTER (WHERE ea.id_escola <> em.id_escola)   AS outra_escola
    FROM fora
    LEFT JOIN turma_escola ea ON ea.id_turma = fora.turma_avaliada
    LEFT JOIN turma_escola em ON em.id_turma = fora.turma_matricula
""")

# d3. Contexto para a dim_escola: das 1.558 escolas, quantas tem aluno? quantas tem avaliacao?
q("d3. Escolas: cadastro x com frequencia x com avaliacao", """
    WITH turma_escola AS (SELECT DISTINCT id_turma, id_escola FROM frequencia)
    SELECT (SELECT COUNT(*) FROM escola)                                   AS escolas_cadastro,
           (SELECT COUNT(DISTINCT id_escola) FROM frequencia)              AS com_frequencia,
           (SELECT COUNT(DISTINCT te.id_escola)
              FROM avaliacao av JOIN turma_escola te USING (id_turma))     AS com_avaliacao
""")