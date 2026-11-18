r"""
EDA parte 1 - perfil das 5 tabelas brutas (Parquet local, via DuckDB 2.x).
Objetivo: conhecer tipos, faixas, cardinalidade e nulos ANTES de escrever os stagings.
Rodar a partir da raiz do repo:  python -X utf8 eda\eda_01_perfil.py
"""
import duckdb

TABELAS = ["aluno", "escola", "turma", "frequencia", "avaliacao"]

con = duckdb.connect()  # banco em memoria, nada e gravado em disco

for t in TABELAS:
    caminho = f"data/{t}.parquet"
    # DuckDB 2.x: fetchall() devolve lista de tuplas -> [0][0] pega o valor
    n = con.sql(f"SELECT COUNT(*) FROM '{caminho}'").fetchall()[0][0]
    print(f"\n{'=' * 70}\n{t.upper()} - {n:,} linhas\n{'=' * 70}")

    # SUMMARIZE: perfil automatico de cada coluna (como 'Estatisticas' no QGIS)
    con.sql(f"""
        SELECT column_name     AS coluna,
               column_type     AS tipo,
               min, max,
               approx_unique   AS distintos_aprox,
               null_percentage AS pct_nulos
        FROM (SUMMARIZE SELECT * FROM '{caminho}')
    """).show(max_width=250)

    # 3 linhas de exemplo, para ver o formato real dos valores
    con.sql(f"SELECT * FROM '{caminho}' LIMIT 3").show(max_width=250)