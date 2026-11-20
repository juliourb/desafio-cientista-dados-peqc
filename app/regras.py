"""Réplica em Python das regras do alerta precoce.

Espelha, linha a linha, duas peças do projeto dbt:

* `int_educacao__aluno_bimestre`: pior caso entre turmas, frequência acumulada, variação em
  relação ao bimestre imediatamente anterior e faltas estimadas;
* `mart_educacao__alerta_precoce_aluno_bimestre`: sinais, nível, motivos e a flag de
  comunicação ao Conselho Tutelar.

Todos os limites vêm das `vars` do `dbt_project.yml`; não há número de política fixo aqui.
A concordância com o dbt é conferida a cada exportação (`scripts/exportar_snapshot.py`).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
ORDEM_NIVEL = {"alto": 1, "medio": 2, "atencao": 3, "sem_alerta": 4}


def carregar_vars(caminho: Path | None = None) -> dict:
    caminho = caminho or RAIZ / "dbt_project.yml"
    return dict(yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))["vars"])


def arredondar_1_escalar(x: float | None) -> float | None:
    """ROUND(x, 1) do BigQuery: arredonda o valor binário exato do float, metade se afasta do zero.

    `Decimal(x)` (e não `Decimal(str(x))`) preserva o valor binário: 7.35 é 7.3499999... e vira 7.3.
    """
    if x is None or x != x:
        return None
    return float(Decimal(x).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def arredondar_1(x: pd.Series | np.ndarray) -> pd.Series:
    """Versão em série de `arredondar_1_escalar` (nulo continua nulo)."""
    s = pd.Series(x, dtype=float)
    return s.map(arredondar_1_escalar).astype(float)


def _booleano(s: pd.Series) -> pd.Series:
    """Nulo vira falso (equivale ao coalesce(..., false) do SQL)."""
    return s.map(lambda x: bool(x) if x is not None and x == x else False).astype(bool)


def faltas_estimadas_bimestre(freq: pd.Series, v: dict) -> pd.Series:
    """(100 - frequência)% x dias letivos do bimestre, com uma casa."""
    return arredondar_1((100 - freq) / 100 * v["dias_letivos_bimestre"])


def pior_caso(df: pd.DataFrame, v: dict) -> pd.DataFrame:
    """Aluno com mais de uma turma no bimestre vira 1 linha: menor frequência, mais faltas,
    menor média. A escola é a do registro de menor frequência (ignora nulas)."""
    d = df.copy()
    if "id_escola" not in d:
        d["id_escola"] = pd.NA
    if "nota_media_bimestre" not in d:
        d["nota_media_bimestre"] = np.nan
    d["_ordem"] = d["frequencia_bimestre_pct"].fillna(101)
    com_escola = d[d["id_escola"].notna()].sort_values(["_ordem", "id_escola"])
    escola = com_escola.groupby(["id_aluno", "bimestre"])["id_escola"].first()
    g = d.groupby(["id_aluno", "bimestre"], sort=False)
    out = g.agg(
        qtd_turmas_no_bimestre=("id_aluno", "size"),
        frequencia_bimestre_pct=("frequencia_bimestre_pct", "min"),
        faltas_estimadas_bimestre=("faltas_estimadas_bimestre", "max"),
        nota_media_bimestre=("nota_media_bimestre", "min"),
    ).reset_index()
    out = out.merge(escola.rename("id_escola").reset_index(), how="left", on=["id_aluno", "bimestre"])
    return out


def acumular(df: pd.DataFrame, v: dict) -> pd.DataFrame:
    """Acumulados até o bimestre e comparação com o bimestre imediatamente anterior.

    Entrada (aluno x bimestre): id_aluno, bimestre, frequencia_bimestre_pct,
    faltas_estimadas_bimestre. Premissa do dbt: bimestres com o mesmo número de dias
    letivos, então a frequência acumulada é a média simples das bimestrais.
    """
    d = df.sort_values(["id_aluno", "bimestre"]).reset_index(drop=True)
    f = d["frequencia_bimestre_pct"].astype(float)
    falt = d["faltas_estimadas_bimestre"].astype(float)
    g_id = d["id_aluno"]

    soma_f = f.fillna(0).groupby(g_id).cumsum()
    n_f = f.notna().astype(int).groupby(g_id).cumsum()
    # média antes do arredondamento: usada só na checagem de empates da paridade
    d["frequencia_acumulada_bruta"] = soma_f / n_f.where(n_f > 0)
    d["frequencia_acumulada_pct"] = arredondar_1(d["frequencia_acumulada_bruta"])

    soma_falt = falt.fillna(0).groupby(g_id).cumsum()
    n_falt = falt.notna().astype(int).groupby(g_id).cumsum()
    d["faltas_estimadas_acumuladas"] = arredondar_1(soma_falt.where(n_falt > 0))

    d["qtd_bimestres_ate_aqui"] = d.groupby("id_aluno").cumcount() + 1
    anterior_f = f.groupby(g_id).shift(1)
    anterior_b = d["bimestre"].groupby(g_id).shift(1)
    consecutivo = (d["bimestre"] - anterior_b) == 1
    variacao = arredondar_1(f - anterior_f)
    d["variacao_frequencia_pp"] = variacao.where(consecutivo)
    return d


def classificar(df: pd.DataFrame, v: dict) -> pd.DataFrame:
    """Sinais, nível, motivos e flag do Conselho Tutelar, na ordem de prioridade do mart.

    Usa `nota_media_baixa` se vier pronta; senão a calcula de `nota_media_bimestre`
    (média do bimestre abaixo do limite). Nulos nunca disparam sinal.
    """
    d = df.copy()
    if "nota_media_baixa" in d:
        nota_baixa = _booleano(d["nota_media_baixa"])
    else:
        nota_baixa = (d["nota_media_bimestre"].astype(float) < v["limite_nota_baixa"]).fillna(False)
        nota_baixa = nota_baixa.astype(bool)

    freq = d["frequencia_acumulada_pct"].astype(float)
    var = d["variacao_frequencia_pp"].astype(float)
    faltas = d["faltas_estimadas_acumuladas"].astype(float)

    busca_ativa = (freq < v["limite_frequencia_legal"]).fillna(False).astype(bool)
    atendimento = (freq < v["limite_frequencia_atendimento"]).fillna(False).astype(bool)
    queda = (var <= -v["limite_queda_frequencia_pp"]).fillna(False).astype(bool)
    conselho = (faltas >= v["limite_faltas_conselho_tutelar"]).fillna(False).astype(bool)

    nivel = np.select(
        [busca_ativa, atendimento & nota_baixa, atendimento | nota_baixa, queda],
        ["alto", "alto", "medio", "atencao"],
        default="sem_alerta",
    )

    def texto(i: int) -> str:
        partes = []
        if busca_ativa.iat[i]:
            partes.append(f"frequencia acumulada abaixo de {v['limite_frequencia_legal']}%")
        if atendimento.iat[i] and not busca_ativa.iat[i]:
            partes.append(f"frequencia acumulada abaixo de {v['limite_frequencia_atendimento']}%")
        if nota_baixa.iat[i]:
            partes.append(f"media do bimestre abaixo de {v['limite_nota_baixa']}")
        if queda.iat[i]:
            partes.append("queda de frequencia em relacao ao bimestre anterior")
        return "; ".join(partes)

    d["sinal_frequencia_busca_ativa"] = busca_ativa.to_numpy()
    d["sinal_frequencia_atendimento"] = atendimento.to_numpy()
    d["sinal_nota_baixa"] = nota_baixa.to_numpy()
    d["sinal_queda_frequencia"] = queda.to_numpy()
    d["comunicar_conselho_tutelar"] = conselho.to_numpy()
    d["nivel_alerta"] = nivel
    d["ordem_nivel_alerta"] = d["nivel_alerta"].map(ORDEM_NIVEL).astype(int)
    d["motivos"] = [texto(i) for i in range(len(d))]
    return d
