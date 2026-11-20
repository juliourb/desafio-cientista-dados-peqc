"""Peças de interface repetidas nas páginas: padrão de bloco e rodapé."""

from __future__ import annotations

import streamlit as st

from dados import REPO_URL, commit_curto, data_snapshot


def secao(numero: int | str, titulo: str) -> None:
    st.markdown(f"#### {numero} · {titulo}")


def conclusao(texto: str) -> None:
    """Título-conclusão do gráfico: a frase que o gráfico demonstra."""
    st.markdown(f"##### {texto}")


def o_que_mostra(texto: str) -> None:
    st.markdown(f"**O que isto mostra.** {texto}")


def decisao(texto: str) -> None:
    with st.container(border=True):
        st.markdown(f"**Decisão de gestão.** {texto}")


def rodape() -> None:
    st.divider()
    st.caption(
        f"Snapshot de {data_snapshot()} · commit {commit_curto()} · dados anonimizados do desafio · "
        f"[repositório]({REPO_URL})"
    )
