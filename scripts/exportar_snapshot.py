"""Exporta o snapshot agregado e anonimizado que alimenta o app Radar da Busca Ativa.

Roda no ambiente `rmi` (dbt) a partir da raiz do repositório:

    python scripts/exportar_snapshot.py

Só lê (SELECT) os marts em `dbt_dev_marts`. Nada identificável é gravado em disco nem
impresso: escolas e bairros viram pseudônimos, linhas individuais existem apenas em memória
(para as checagens de paridade) e o terminal mostra somente contagens.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from google.cloud import bigquery

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "app" / "data"
sys.path.insert(0, str(RAIZ / "app"))

MAX_BYTES = 2 * 1024**3  # teto de custo por job (2 GB)
warnings.filterwarnings("ignore", message="BigQuery Storage module not found")


# ----------------------------------------------------------------------------
# infraestrutura
# ----------------------------------------------------------------------------
def ler_vars() -> dict:
    cfg = yaml.safe_load((RAIZ / "dbt_project.yml").read_text(encoding="utf-8"))
    return dict(cfg["vars"])


def commit_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=RAIZ, text=True).strip()


class Consulta:
    def __init__(self, projeto: str, dataset: str):
        self.projeto = projeto
        self.dataset = dataset
        self.cliente = bigquery.Client(project=projeto)

    def tabela(self, nome: str) -> str:
        return f"`{self.projeto}.{self.dataset}.{nome}`"

    def rodar(self, sql: str) -> pd.DataFrame:
        cfg = bigquery.QueryJobConfig(maximum_bytes_billed=MAX_BYTES)
        return self.cliente.query(sql, job_config=cfg).result().to_arrow().to_pandas()


def gravar(df: pd.DataFrame, nome: str) -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SAIDA / f"{nome}.parquet", index=False)
    return len(df)


# ----------------------------------------------------------------------------
# pseudônimos (mapeamento só em memória; nunca persistido)
# ----------------------------------------------------------------------------
def mapa_pseudonimos(valores: pd.Series, prefixo: str, largura: int) -> dict:
    unicos = sorted(pd.unique(valores.dropna()))
    return {v: f"{prefixo} {i:0{largura}d}" for i, v in enumerate(unicos, start=1)}


def aplicar(valores: pd.Series, mapa: dict, nulo: str) -> pd.Series:
    return valores.map(mapa).fillna(nulo).astype(str)


def suprimir(df: pd.DataFrame, base: str, minimo: int, colunas: list[str]) -> pd.DataFrame:
    """Linhas com base < minimo: colunas de taxa/contagem ficam nulas e `suprimido` = True."""
    df = df.copy()
    mascara = df[base] < minimo
    for c in colunas:
        if pd.api.types.is_integer_dtype(df[c]):
            df[c] = df[c].astype("Int64")
            df.loc[mascara, c] = pd.NA
        else:
            df[c] = df[c].astype(float)
            df.loc[mascara, c] = np.nan
    df["suprimido"] = mascara.astype(bool)
    return df


# ----------------------------------------------------------------------------
# exportações agregadas (etapa 1)
# ----------------------------------------------------------------------------
def exportar_curva(q: Consulta, v: dict) -> pd.DataFrame:
    df = q.rodar(f"select * from {q.tabela('mart_educacao__frequencia_desempenho')}")
    df = suprimir(
        df,
        "qtd_registros",
        v["tamanho_minimo_amostra"],
        ["qtd_alunos", "nota_media", "qtd_registros_nota_baixa", "pct_registros_nota_baixa",
         "risco_relativo_nota_baixa"],
    )
    return df.sort_values(["grupo_etario", "faixa_frequencia_inicio"]).reset_index(drop=True)


def exportar_alerta_resumo(q: Consulta, v: dict) -> pd.DataFrame:
    sql = f"""
        select
            bimestre,
            nivel_alerta,
            ordem_nivel_alerta,
            count(*)                                       as qtd_alunos,
            countif(faixa_etaria = '15-17')                as qtd_alunos_15_17,
            countif(comunicar_conselho_tutelar)            as qtd_comunicar_conselho_tutelar,
            countif(not escola_identificada)               as qtd_sem_escola
        from {q.tabela('mart_educacao__alerta_precoce_aluno_bimestre')}
        group by bimestre, nivel_alerta, ordem_nivel_alerta
        order by bimestre, ordem_nivel_alerta
    """
    df = q.rodar(sql)
    return suprimir(
        df,
        "qtd_alunos",
        v["tamanho_minimo_amostra"],
        ["qtd_alunos", "qtd_alunos_15_17", "qtd_comunicar_conselho_tutelar", "qtd_sem_escola"],
    )


def exportar_absenteismo(q: Consulta, v: dict, mapa_escola: dict) -> pd.DataFrame:
    df = q.rodar(f"select * from {q.tabela('mart_educacao__absenteismo_escola_bimestre')}")
    df["escola"] = aplicar(df["id_escola"], mapa_escola, "Não identificada")
    df = df.drop(columns=["id_escola", "bairro_escola_hash"])
    metricas = [c for c in df.columns if c.startswith(("qtd_", "pct_")) or c == "frequencia_media_pct"]
    df = suprimir(df, "qtd_alunos_avaliados", v["tamanho_minimo_amostra"], metricas)
    cols = ["escola", "bimestre"] + [c for c in df.columns if c not in ("escola", "bimestre")]
    return df[cols].sort_values(["bimestre", "escola"]).reset_index(drop=True)


def exportar_bairro(q: Consulta, v: dict, mapa_bairro: dict) -> pd.DataFrame:
    df = q.rodar(f"select * from {q.tabela('mart_educacao__alerta_bairro_bimestre')}")
    df["bairro"] = aplicar(df["bairro_residencia_hash"], mapa_bairro, "Bairro não informado")
    df = df.drop(columns=["bairro_residencia_hash"])
    metricas = [c for c in df.columns if c.startswith(("qtd_", "pct_"))]
    df = suprimir(df, "qtd_alunos_avaliados", v["tamanho_minimo_amostra"], metricas)
    cols = ["bairro", "bimestre"] + [c for c in df.columns if c not in ("bairro", "bimestre")]
    return df[cols].sort_values(["bimestre", "ranking_prioridade", "bairro"]).reset_index(drop=True)


def exportar_pendencias(q: Consulta, mapa_escola: dict) -> pd.DataFrame:
    df = q.rodar(f"select * from {q.tabela('mart_educacao__pendencias_qualidade_escola')}")
    df["escola"] = aplicar(df["id_escola"], mapa_escola, "Secretaria (central)")
    df = df.drop(columns=["id_escola"])
    cols = ["escola"] + [c for c in df.columns if c != "escola"]
    return df[cols].sort_values(["ranking_pendencias", "escola"], na_position="last").reset_index(drop=True)


# ----------------------------------------------------------------------------
# correlação frequência x nota (etapa 2a)
# ----------------------------------------------------------------------------
def classe_correlacao(r: float) -> str | None:
    if r != r:
        return None
    return "fraca" if abs(r) < 0.3 else "moderada" if abs(r) < 0.5 else "forte"


def estatisticas(sub: pd.DataFrame) -> dict:
    n = len(sub)
    x, y = sub["frequencia_bimestre_pct"], sub["nota_media_bimestre"]
    if n < 3 or x.nunique() < 2 or y.nunique() < 2:
        pearson = spearman = np.nan
    else:
        pearson = x.corr(y, method="pearson")
        # Spearman = Pearson dos postos; empates recebem posto médio
        spearman = x.rank(method="average").corr(y.rank(method="average"))
    return {
        "n": n,
        "pearson": pearson,
        "spearman": spearman,
        "r2": pearson**2 if pearson == pearson else np.nan,
        "classificacao": classe_correlacao(pearson),
    }


def exportar_correlacao(q: Consulta, v: dict) -> pd.DataFrame:
    # só as duas colunas numéricas e o recorte entram na memória (sem chave de aluno)
    df = q.rodar(f"""
        select
            bimestre,
            case when faixa_etaria = '15-17' then '15-17' else 'demais' end as grupo_etario,
            frequencia_bimestre_pct,
            nota_media_bimestre
        from {q.tabela('fct_educacao__avaliacao_bimestre')}
        where nota_media_bimestre is not null and frequencia_bimestre_pct is not null
    """)
    linhas = []
    for bim in [1, 2, 3, 4, None]:
        por_bim = df if bim is None else df[df["bimestre"] == bim]
        for grupo in ["15-17", "demais", None]:
            sub = por_bim if grupo is None else por_bim[por_bim["grupo_etario"] == grupo]
            linhas.append({
                "bimestre": pd.NA if bim is None else bim,
                "rotulo_bimestre": "Ano" if bim is None else f"{bim}º bimestre",
                "grupo_etario": "todos" if grupo is None else grupo,
                **estatisticas(sub),
            })
    out = pd.DataFrame(linhas)
    out["bimestre"] = out["bimestre"].astype("Int64")
    out = suprimir(out, "n", v["tamanho_minimo_amostra"], ["pearson", "spearman", "r2"])
    return out


# ----------------------------------------------------------------------------
# paridade das regras em Python com o dbt (etapa 2c), tudo em memória
# ----------------------------------------------------------------------------
TOL_EMPATE = 1e-9
CRITERIO_FREQUENCIA = (
    "Linha fora de empate (media bruta a mais de 1e-9 de um valor .x5): concordancia com o dbt "
    "dentro de 0,01 em 100% das linhas. Linha em empate (a ate 1e-9 de .x5): diferenca de ate 0,1, "
    "em 100% das linhas (a ordem de soma do AVG em ponto flutuante nao e deterministica). "
    "Nenhuma divergencia pode ficar em lados opostos de 75 ou 85."
)


def _igual(a: pd.Series, b: pd.Series, tol: float = 0.01) -> pd.Series:
    a, b = a.astype(float), b.astype(float)
    return (a.isna() & b.isna()) | ((a - b).abs() <= tol)


def _taxa(ok: pd.Series) -> float:
    return float(ok.mean() * 100)


def paridade_mart(q: Consulta, v: dict) -> dict:
    import regras

    df = q.rodar(f"""
        select
            id_aluno, bimestre,
            frequencia_bimestre_pct, frequencia_acumulada_pct, variacao_frequencia_pp,
            faltas_estimadas_acumuladas, nota_media_bimestre,
            nivel_alerta, comunicar_conselho_tutelar, motivos,
            sinal_frequencia_busca_ativa, sinal_frequencia_atendimento,
            sinal_nota_baixa, sinal_queda_frequencia
        from {q.tabela('mart_educacao__alerta_precoce_aluno_bimestre')}
    """)
    n = len(df)

    # classificação: entradas do mart -> regras.py -> compara com o próprio mart
    r = regras.classificar(df, v)
    ok_nivel = r["nivel_alerta"] == df["nivel_alerta"]
    ok_ct = r["comunicar_conselho_tutelar"] == df["comunicar_conselho_tutelar"].astype(bool)
    ok_sinais = np.logical_and.reduce([
        r[c] == df[c].astype(bool)
        for c in ["sinal_frequencia_busca_ativa", "sinal_frequencia_atendimento",
                  "sinal_nota_baixa", "sinal_queda_frequencia"]
    ])
    ok_motivos = r["motivos"] == df["motivos"].fillna("")

    # acumulado: recalcula a partir da frequência do bimestre
    base = df[["id_aluno", "bimestre", "frequencia_bimestre_pct"]].copy()
    base["faltas_estimadas_bimestre"] = regras.faltas_estimadas_bimestre(base["frequencia_bimestre_pct"], v)
    ac = regras.acumular(base, v)
    ref = df.sort_values(["id_aluno", "bimestre"]).reset_index(drop=True)
    # frequência acumulada: o AVG em janela do BigQuery não tem ordem de soma determinística,
    # então médias que caem em empate (.x5) aceitam 0,1 de diferença; as demais, 0,01.
    bruta = ac["frequencia_acumulada_bruta"].astype(float)
    mina, dbt = ac["frequencia_acumulada_pct"].astype(float), ref["frequencia_acumulada_pct"].astype(float)
    empate = ((bruta - (np.floor(bruta * 10) + 0.5) / 10).abs() <= TOL_EMPATE).fillna(False)
    ok_nao_empate = _igual(mina, dbt, 0.01)[~empate]
    ok_empate = _igual(mina, dbt, 0.1 + 1e-9)[empate]
    diverge = ~_igual(mina, dbt, 0.01)
    cruza = pd.Series(False, index=mina.index)
    for limite in (v["limite_frequencia_legal"], v["limite_frequencia_atendimento"]):
        cruza |= diverge & ((mina < limite) != (dbt < limite))
    detalhe_freq = {
        "criterio": CRITERIO_FREQUENCIA,
        "n_linhas": int(len(ac)),
        "n_empates": int(empate.sum()),
        "n_divergentes_em_empate": int((diverge & empate).sum()),
        "n_divergentes_fora_de_empate": int((diverge & ~empate).sum()),
        "n_cruzam_limite": int(cruza.sum()),
    }
    ok_falt = _igual(ac["faltas_estimadas_acumuladas"], ref["faltas_estimadas_acumuladas"])
    ok_var = _igual(ac["variacao_frequencia_pp"], ref["variacao_frequencia_pp"])

    res = {
        "linhas_comparadas": int(n),
        "classificacao_nivel_pct": _taxa(ok_nivel),
        "classificacao_conselho_tutelar_pct": _taxa(ok_ct),
        "classificacao_sinais_pct": _taxa(pd.Series(ok_sinais)),
        "classificacao_motivos_pct": _taxa(ok_motivos),
        "acumulado_frequencia_nao_empate_pct": _taxa(ok_nao_empate),
        "acumulado_frequencia_empate_pct": _taxa(ok_empate),
        "acumulado_frequencia_detalhe": detalhe_freq,
        "acumulado_faltas_pct": _taxa(ok_falt),
        "acumulado_variacao_pct": _taxa(ok_var),
    }
    if res["classificacao_nivel_pct"] < 100:
        res["matriz_nivel"] = pd.crosstab(df["nivel_alerta"], r["nivel_alerta"]).to_dict()
    return res


def paridade_unit_tests(v: dict) -> dict:
    """Roda regras.py nos casos de borda de _educacao__unit_tests.yml e compara com o esperado."""
    import regras

    cfg = yaml.safe_load((RAIZ / "models/marts/educacao/_educacao__unit_tests.yml").read_text(encoding="utf-8"))
    casos = ok = 0
    falhas: list[str] = []

    def igual(a, b) -> bool:
        if b is None or (isinstance(b, float) and b != b):
            return a is None or a != a
        if isinstance(b, (int, float)) and not isinstance(b, bool):
            return a == a and abs(float(a) - float(b)) <= 0.01
        return a == b

    for ut in cfg["unit_tests"]:
        entradas = {i["input"]: pd.DataFrame(i["rows"]) for i in ut["given"]}
        esperado = pd.DataFrame(ut["expect"]["rows"])
        if ut["model"] == "mart_educacao__alerta_precoce_aluno_bimestre":
            entrada = entradas["ref('int_educacao__aluno_bimestre')"]
            obtido = regras.classificar(entrada, v)
        else:
            entrada = entradas["ref('int_educacao__avaliacao_enriquecida')"]
            obtido = regras.acumular(regras.pior_caso(entrada, v), v)
        chave = ["id_aluno", "bimestre"] if "bimestre" in esperado else ["id_aluno"]
        obtido = obtido.set_index(chave)
        for _, linha in esperado.iterrows():
            casos += 1
            chave_linha = tuple(linha[c] for c in chave)
            ref = obtido.loc[chave_linha[0] if len(chave) == 1 else chave_linha]
            erros = [c for c in esperado.columns if c not in chave and not igual(ref[c], linha[c])]
            if erros:
                falhas.append(f"{ut['name']}: caso {linha['id_aluno']}/{linha.get('bimestre', '-')}: {erros}")
            else:
                ok += 1
    return {"casos": casos, "ok": ok, "concordancia_pct": 100.0 * ok / casos, "falhas": falhas}


def validar_paridade(paridade: dict) -> list[str]:
    problemas = []
    for chave, valor in paridade["mart"].items():
        if chave.endswith("_pct") and valor < 100:
            problemas.append(f"mart.{chave} = {valor:.4f}%")
    if paridade["mart"]["acumulado_frequencia_detalhe"]["n_cruzam_limite"] > 0:
        problemas.append("divergencias da frequencia acumulada cruzam limite de politica: "
                         f"{paridade['mart']['acumulado_frequencia_detalhe']['n_cruzam_limite']}")
    if paridade["unit_tests"]["ok"] != paridade["unit_tests"]["casos"]:
        problemas.append("unit tests: " + "; ".join(paridade["unit_tests"]["falhas"]))
    return problemas


# ----------------------------------------------------------------------------
# alunos fictícios (etapa 3): nenhum dado individual real
# ----------------------------------------------------------------------------
SEMENTE = 20261121
N_ALUNOS = 120
ESCOLAS_FICTICIAS = ["Escola Demonstração A", "Escola Demonstração B", "Escola Demonstração C"]
BAIRROS_FICTICIOS = ["Bairro Demonstração 1", "Bairro Demonstração 2", "Bairro Demonstração 3"]

# casos de borda desenhados à mão: (frequências por bimestre, notas por bimestre)
BORDAS = {
    "b74_9":      ([74.9] * 4, [7.0] * 4),                 # logo abaixo de 75: alto
    "b75_0":      ([75.0] * 4, [7.0] * 4),                 # 75 não é < 75: medio
    "b84_9":      ([84.9] * 4, [7.0] * 4),                 # abaixo de 85: medio
    "b85_0":      ([85.0] * 4, [7.0] * 4),                 # 85 não é < 85; 15,0 faltas no 2º bim.
    "b84_9_nota": ([84.9] * 4, [4.5] * 4),                 # abaixo de 85 e nota baixa: alto
    "b85_0_nota": ([85.0] * 4, [4.5] * 4),                 # só a nota: medio
    "queda5":     ([95.0, 90.0, 90.0, 90.0], [7.0] * 4),   # queda de exatamente 5 p.p.: atencao
    "queda4_9":   ([95.0, 90.1, 90.1, 90.1], [7.0] * 4),   # queda de 4,9 p.p.: sem alerta
    "faltas15":   ([90.0] * 4, [7.0] * 4),                 # 15,0 faltas estimadas no 3º bim.
    "faltas14_9": ([90.0, 90.0, 90.2, 90.0], [7.0] * 4),   # 14,9 faltas no 3º bim.; 19,9 no 4º
}
# esperado por borda: {bimestre: (nivel, comunicar_conselho_tutelar)}
BORDAS_ESPERADO = {
    "b74_9":      {1: ("alto", False), 2: ("alto", True)},
    "b75_0":      {1: ("medio", False), 2: ("medio", True)},
    "b84_9":      {1: ("medio", False), 2: ("medio", True)},
    "b85_0":      {1: ("sem_alerta", False), 2: ("sem_alerta", True)},
    "b84_9_nota": {1: ("alto", False)},
    "b85_0_nota": {1: ("medio", False)},
    "queda5":     {1: ("sem_alerta", False), 2: ("atencao", False), 3: ("sem_alerta", False), 4: ("sem_alerta", True)},
    "queda4_9":   {2: ("sem_alerta", False)},
    "faltas15":   {2: ("sem_alerta", False), 3: ("sem_alerta", True)},
    "faltas14_9": {3: ("sem_alerta", False), 4: ("sem_alerta", True)},
}


DERIVAS_CANDIDATAS = (0.0, 0.5, 1.0)  # média da deriva entre bimestres (dp 4), testadas nesta ordem


def _gerar_alunos(curva: pd.DataFrame, v: dict, deriva: float) -> pd.DataFrame | None:
    """Gera os fictícios com a deriva dada. Devolve None se algum nível ficar com menos de 5 alunos."""
    import regras

    rng = np.random.default_rng(SEMENTE)
    base = curva[~curva["suprimido"]].copy()
    base["nota_media"] = base["nota_media"].astype(float)

    def sortear_primeira(grupo: str) -> tuple[float, float]:
        c = base[base["grupo_etario"] == grupo]
        faixa = c.iloc[rng.choice(len(c), p=(c["qtd_registros"] / c["qtd_registros"].sum()).to_numpy())]
        inicio = float(faixa["faixa_frequencia_inicio"])
        return float(np.clip(round(rng.uniform(inicio, inicio + 5), 1), 0, 100)), float(faixa["nota_media"])

    def nota_da_faixa(grupo: str, freq: float) -> float:
        c = base[base["grupo_etario"] == grupo]
        inicio = min(np.floor(freq / 5) * 5, 95)
        linha = c[c["faixa_frequencia_inicio"] == inicio]
        media = float(linha["nota_media"].iloc[0]) if len(linha) else float(c["nota_media"].mean())
        return float(np.clip(round(media + rng.normal(0, 1.2), 1), 0, 10))

    registros = []
    ids = list(BORDAS) + [f"r{i:03d}" for i in range(N_ALUNOS - len(BORDAS))]
    faixas = ["15-17"] * len(BORDAS) + [
        "15-17" if rng.random() < 0.82 else "18+" for _ in range(N_ALUNOS - len(BORDAS))
    ]
    for chave, faixa in zip(ids, faixas):
        grupo = "15-17" if faixa == "15-17" else "demais"
        if chave in BORDAS:
            freqs, notas = BORDAS[chave]
        else:
            f1, _ = sortear_primeira(grupo)
            freqs = [f1]
            for _ in range(3):
                freqs.append(float(np.clip(round(freqs[-1] + rng.normal(deriva, 4), 1), 0, 100)))
            notas = [nota_da_faixa(grupo, f) for f in freqs]
        escola = ESCOLAS_FICTICIAS[int(rng.integers(len(ESCOLAS_FICTICIAS)))]
        bairro = BAIRROS_FICTICIOS[int(rng.integers(len(BAIRROS_FICTICIOS)))]
        for b in range(4):
            registros.append({
                "chave": chave, "escola": escola, "bairro": bairro, "faixa_etaria": faixa,
                "bimestre": b + 1, "frequencia_bimestre_pct": freqs[b], "nota_media_bimestre": notas[b],
            })
    df = pd.DataFrame(registros)

    # nomes "Aluno 001"... em ordem embaralhada (as bordas não ficam nas primeiras linhas)
    ordem = rng.permutation(N_ALUNOS)
    nomes = {chave: f"Aluno {int(i) + 1:03d}" for chave, i in zip(ids, ordem)}
    df["aluno"] = df["chave"].map(nomes)

    # classificação pelas mesmas regras do mart
    df["id_aluno"] = df["chave"]  # só como chave de agrupamento em memória
    df["faltas_estimadas_bimestre"] = regras.faltas_estimadas_bimestre(df["frequencia_bimestre_pct"], v)
    df = regras.classificar(regras.acumular(df, v), v)

    # confere os casos de borda desenhados
    for chave, esperado in BORDAS_ESPERADO.items():
        for bim, (nivel, ct) in esperado.items():
            linha = df[(df["chave"] == chave) & (df["bimestre"] == bim)].iloc[0]
            if linha["nivel_alerta"] != nivel or bool(linha["comunicar_conselho_tutelar"]) != ct:
                print(f"BORDA FALHOU: {chave} bimestre {bim}: {linha['nivel_alerta']}, ct={linha['comunicar_conselho_tutelar']}")
                sys.exit(4)

    por_nivel = df.groupby("nivel_alerta")["aluno"].nunique()
    if any(por_nivel.get(n, 0) < 5 for n in regras.ORDEM_NIVEL):
        return None

    df["ficticio"] = True
    colunas = [
        "aluno", "escola", "bairro", "faixa_etaria", "bimestre",
        "frequencia_bimestre_pct", "frequencia_acumulada_pct", "variacao_frequencia_pp",
        "faltas_estimadas_acumuladas", "nota_media_bimestre",
        "nivel_alerta", "ordem_nivel_alerta", "motivos", "comunicar_conselho_tutelar",
        "sinal_frequencia_busca_ativa", "sinal_frequencia_atendimento",
        "sinal_nota_baixa", "sinal_queda_frequencia", "ficticio",
    ]
    return df[colunas].sort_values(["aluno", "bimestre"]).reset_index(drop=True)


def gerar_alunos_ficticios(curva: pd.DataFrame, v: dict) -> tuple[pd.DataFrame, float]:
    """Escolhe a primeira deriva candidata em que o nível alto no 4º bimestre não supera o do 1º
    (a tendência agregada real cai). Mesma semente em todas as tentativas."""
    tentativas = []
    for deriva in DERIVAS_CANDIDATAS:
        df = _gerar_alunos(curva, v, deriva)
        if df is None:
            tentativas.append((deriva, "algum nível com menos de 5 alunos"))
            continue
        alto = df[df["nivel_alerta"] == "alto"].groupby("bimestre").size().reindex([1, 2, 3, 4], fill_value=0).tolist()
        tentativas.append((deriva, alto))
        if alto[-1] <= alto[0]:
            print(f"deriva dos fictícios: {deriva} (alto por bimestre: {alto})")
            return df, deriva
    print("NENHUMA DERIVA CANDIDATA ATENDE AO CRITERIO (alto no 4o bimestre <= alto no 1o):")
    for deriva, alto in tentativas:
        print(f"  deriva {deriva}: {alto}")
    sys.exit(5)


def autoverificar_arredondamento() -> None:
    """Para tudo se o arredondamento de regras.py não reproduzir o ROUND(x, 1) do BigQuery."""
    import regras

    casos = {7.35: 7.3, 17.65: 17.6, 0.25: 0.3, -0.25: -0.3, -7.35: -7.3}
    erros = [f"{x} -> {regras.arredondar_1_escalar(x)} (esperado {e})"
             for x, e in casos.items() if regras.arredondar_1_escalar(x) != e]
    if regras.arredondar_1_escalar(None) is not None or regras.arredondar_1_escalar(float("nan")) is not None:
        erros.append("nulo/NaN deveria retornar None")
    if erros:
        print("AUTOVERIFICACAO DO ARREDONDAMENTO FALHOU:", *erros, sep="\n  ")
        sys.exit(3)
    print(f"autoverificacao do arredondamento: {len(casos)}/{len(casos)} casos ok")


# ----------------------------------------------------------------------------
# principal
# ----------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--projeto", default="desafio-rmi-515002")
    ap.add_argument("--dataset", default="dbt_dev_marts")
    args = ap.parse_args()

    autoverificar_arredondamento()
    v = ler_vars()
    q = Consulta(args.projeto, args.dataset)
    meta: dict = {
        "gerado_em_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "commit": commit_head(),
        "projeto": args.projeto,
        "dataset": args.dataset,
        "limites": v,
        "linhas": {},
    }

    # paridade primeiro: abaixo de 100% nada é gravado (só contagens e taxas são impressas)
    paridade = {"mart": paridade_mart(q, v), "unit_tests": paridade_unit_tests(v)}
    problemas = validar_paridade(paridade)
    print(f"paridade: {json.dumps({k: (round(x, 4) if isinstance(x, float) else x) for k, x in paridade['mart'].items() if k != 'matriz_nivel'})}")
    print(f"unit tests: {paridade['unit_tests']['ok']}/{paridade['unit_tests']['casos']} casos")
    if problemas:
        print("PARIDADE ABAIXO DE 100%:", *problemas, sep="\n  ")
        if "matriz_nivel" in paridade["mart"]:
            print("matriz de confusão (linha = mart, coluna = regras.py), só contagens:")
            print(pd.DataFrame(paridade["mart"]["matriz_nivel"]).fillna(0).astype(int))
        sys.exit(2)
    paridade["unit_tests"].pop("falhas")
    paridade["mart"].pop("matriz_nivel", None)
    meta["paridade"] = paridade

    # chaves reais só em memória: o mapeamento id -> pseudônimo cobre o conjunto exportado
    abs_bruto = q.rodar(f"select id_escola from {q.tabela('mart_educacao__absenteismo_escola_bimestre')}")
    pen_bruto = q.rodar(f"select id_escola from {q.tabela('mart_educacao__pendencias_qualidade_escola')}")
    bai_bruto = q.rodar(f"select bairro_residencia_hash from {q.tabela('mart_educacao__alerta_bairro_bimestre')}")
    mapa_escola = mapa_pseudonimos(pd.concat([abs_bruto["id_escola"], pen_bruto["id_escola"]]), "Escola", 4)
    mapa_bairro = mapa_pseudonimos(bai_bruto["bairro_residencia_hash"], "Bairro", 3)

    saidas = {
        "curva": exportar_curva(q, v),
        "alerta_resumo": exportar_alerta_resumo(q, v),
        "absenteismo_escola": exportar_absenteismo(q, v, mapa_escola),
        "alerta_bairro": exportar_bairro(q, v, mapa_bairro),
        "pendencias_escola": exportar_pendencias(q, mapa_escola),
        "correlacao": exportar_correlacao(q, v),
    }
    saidas["alunos_ficticios"], deriva = gerar_alunos_ficticios(saidas["curva"], v)
    meta["alunos_ficticios"] = {"semente": SEMENTE, "n_alunos": N_ALUNOS, "deriva_media": deriva, "deriva_dp": 4}
    for nome, df in saidas.items():
        meta["linhas"][nome] = gravar(df, nome)

    (SAIDA / "metadados.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    for nome, n in meta["linhas"].items():
        print(f"{nome}.parquet: {n} linhas")
    fic = saidas["alunos_ficticios"]
    print("alunos fictícios: nível x bimestre (linhas)")
    print(pd.crosstab(fic["nivel_alerta"], fic["bimestre"]).reindex(
        ["alto", "medio", "atencao", "sem_alerta"]).to_string())
    print("alunos distintos por nível:", fic.groupby("nivel_alerta")["aluno"].nunique().to_dict(),
          "| comunicar CT:", int(fic["comunicar_conselho_tutelar"].sum()),
          "| 15-17:", int(fic[fic.bimestre == 1].faixa_etaria.eq("15-17").sum()), "de", N_ALUNOS)
    print("metadados.json gravado")


if __name__ == "__main__":
    main()
