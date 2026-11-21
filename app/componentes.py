"""Peças de interface repetidas nas páginas: cabeçalho, aviso, padrão de card e rodapé."""

from __future__ import annotations

import streamlit as st

from dados import REPO_URL, commit_curto, data_snapshot, limites, metadados

CSS = """
<style>
.block-container, [data-testid="stMainBlockContainer"] {
    padding-top: 4rem !important; padding-bottom: 1rem !important; max-width: 1320px !important;
}
h1, h2, h3, h4, h5 { margin: 0; padding: 0; }
[data-testid="stMetricValue"] { font-size: 1.6rem; }
[data-testid="stMetricLabel"] p { font-size: 0.85rem; }
[data-testid="stVerticalBlockBorderWrapper"] p { margin-bottom: 0.25rem; }
h1 { font-size: 1.6rem !important; line-height: 1.2 !important; }
.st-key-cab_meta { text-align: right; }
.st-key-cab_meta p { text-align: right; }
</style>
"""


def estilo() -> None:
    st.html(CSS)


def cabecalho() -> None:
    meta = metadados()
    paridade = meta["paridade"]["mart"]["classificacao_nivel_pct"]
    esq, dir_ = st.columns([5, 3], vertical_alignment="bottom")
    with esq:
        st.markdown("# Radar da Busca Ativa")
        st.caption(
            "Frequência, desempenho e prioridade territorial na rede municipal do Rio · "
            "prova de conceito com dados anonimizados"
        )
    with dir_:
        with st.container(key="cab_meta"):
            st.caption(f"Snapshot {data_snapshot()} · commit {commit_curto()} · "
                       f"paridade com o dbt: {int(round(paridade))}%")


def aviso_anonimizacao() -> None:
    n = limites()["tamanho_minimo_amostra"]
    st.caption(
        ":material/info: Dados anonimizados do desafio · escolas e bairros com pseudônimos · lista nominal com "
        f"alunos fictícios · taxas de grupos com menos de {n} alunos ocultadas · detalhes em Sobre os dados"
    )


def secao(titulo: str) -> None:
    st.markdown(f"#### {titulo}")


def conclusao(texto: str) -> None:
    """Título-conclusão do gráfico: a frase que o gráfico demonstra."""
    st.markdown(f"**{texto}**")


def o_que_mostra(texto: str) -> None:
    st.markdown(f"**O que isto mostra.** {texto}")


def decisao(texto: str) -> None:
    """Uma linha visível com a decisão de gestão que o bloco apoia."""
    st.markdown(f"**Decisão de gestão.** {texto}")


def como_ler(rotulo: str = "Como ler"):
    """Botão que abre o texto completo das explicações do bloco."""
    return st.popover(f":material/help: {rotulo}", width="content")


def rodape() -> None:
    st.divider()
    st.caption(
        f"Snapshot de {data_snapshot()} · commit {commit_curto()} · dados anonimizados do desafio · "
        f"[repositório]({REPO_URL})"
    )
