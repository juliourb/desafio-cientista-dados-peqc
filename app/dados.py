"""Leitura dos parquets do snapshot, constantes de apresentação e formatação em português."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

import regras

DIR = Path(__file__).resolve().parent
DADOS = DIR / "data"
REPO_URL = "https://github.com/juliourb/desafio-cientista-dados-peqc"

# níveis de alerta: cor fixa no app inteiro; o nível aparece sempre também em texto
NIVEIS = ["alto", "medio", "atencao", "sem_alerta"]
ROTULO = {"alto": "Alto", "medio": "Médio", "atencao": "Atenção", "sem_alerta": "Sem alerta"}
COR = {"alto": "#B42318", "medio": "#E07B12", "atencao": "#C9A227", "sem_alerta": "#9AA4AE"}
ACAO = {
    "alto": "busca ativa",
    "medio": "atendimento individualizado",
    "atencao": "acompanhamento",
    "sem_alerta": "sem ação específica",
}
GRUPOS = {"15-17": "15 a 17 anos", "demais": "Demais idades", "todos": "Todos"}


@st.cache_data
def carregar(nome: str) -> pd.DataFrame:
    return pd.read_parquet(DADOS / f"{nome}.parquet")


@st.cache_data
def metadados() -> dict:
    return json.loads((DADOS / "metadados.json").read_text(encoding="utf-8"))


@st.cache_data
def limites() -> dict:
    """Limites de política, lidos das `vars` do dbt_project.yml."""
    return regras.carregar_vars()


# ----------------------------------------------------------------------------
# formatação (vírgula decimal, ponto de milhar)
# ----------------------------------------------------------------------------
def _nulo(x) -> bool:
    return x is None or bool(pd.isna(x))


def f_int(x) -> str:
    if _nulo(x):
        return "—"
    return f"{int(round(float(x))):,}".replace(",", ".")


def f_dec(x, casas: int = 1) -> str:
    if _nulo(x):
        return "—"
    return f"{float(x):,.{casas}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def f_pct(x, casas: int = 1) -> str:
    return "—" if _nulo(x) else f"{f_dec(x, casas)}%"


def rotulo_bimestre(b) -> str:
    return f"{int(b)}º bimestre"


def data_snapshot() -> str:
    gerado = metadados()["gerado_em_utc"][:10]
    ano, mes, dia = gerado.split("-")
    return f"{dia}/{mes}/{ano}"


def commit_curto() -> str:
    return metadados()["commit"][:7]
