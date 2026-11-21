"""Comunicação com as escolas: catálogo de pendências, mensagem para a direção e janela de registro.

Simulação: o acompanhamento fica em st.session_state e vale só para a sessão do navegador. As escolas
aparecem com pseudônimo; na operação real, a Secretaria (que tem a chave) faz a correspondência.
Rótulo, dimensão, responsável e ação sugerida de cada tipo vêm do catálogo do mart
(app/data/pendencias_tipos.parquet); nada disso é digitado aqui.
"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from dados import carregar, f_int
from graficos import TIPOS_PENDENCIA

STATUS_COM = ["Não comunicada", "Direção contatada", "Em correção", "Corrigida — aguarda nova carga"]
PREFIXO = "qtd_"


# ----------------------------------------------------------------------------
# catálogo (vem do mart)
# ----------------------------------------------------------------------------
def catalogo() -> pd.DataFrame:
    """Uma linha por tipo: tipo_pendencia, dimensao_qualidade, responsavel_correcao, acao_sugerida."""
    return carregar("pendencias_tipos")


def colunas_tipo() -> dict[str, str]:
    """{coluna qtd_<tipo> do parquet de pendências -> tipo_pendencia do catálogo}."""
    return {c: c[len(PREFIXO):] for c in TIPOS_PENDENCIA}


def tipos_da_linha(linha: pd.Series) -> list[str]:
    """Colunas de tipo com pendência nesta linha (escola)."""
    return [c for c in TIPOS_PENDENCIA if c in linha.index and float(linha[c]) > 0]


def pendencias_da_escola(linha: pd.Series) -> pd.DataFrame:
    """Tabela por tipo: quantidade (do parquet) + dimensão, responsável e ação (do catálogo)."""
    cat = catalogo().set_index("tipo_pendencia")
    mapa = colunas_tipo()
    linhas = []
    for col in tipos_da_linha(linha):
        tipo = mapa[col]
        info = cat.loc[tipo] if tipo in cat.index else None
        linhas.append({
            "Tipo": TIPOS_PENDENCIA[col],
            "Pendências": float(linha[col]),
            "Dimensão de qualidade": str(info["dimensao_qualidade"]).capitalize() if info is not None else "—",
            "Responsável": str(info["responsavel_correcao"]).capitalize() if info is not None else "—",
            "Ação sugerida": str(info["acao_sugerida"]) if info is not None else "—",
        })
    return pd.DataFrame(linhas, columns=["Tipo", "Pendências", "Dimensão de qualidade", "Responsável", "Ação sugerida"])


def faltam_acoes(pend: pd.DataFrame) -> list[str]:
    """Tipos com pendência em alguma escola que não têm ação sugerida no catálogo (deve ser vazio)."""
    cat = catalogo().set_index("tipo_pendencia")
    faltas = []
    for col, tipo in colunas_tipo().items():
        if col in pend.columns and pend[col].sum() > 0:
            if tipo not in cat.index or not str(cat.loc[tipo, "acao_sugerida"]).strip():
                faltas.append(tipo)
    return faltas


# ----------------------------------------------------------------------------
# mensagem para a direção
# ----------------------------------------------------------------------------
def mensagem(linha: pd.Series, prazo: date | None) -> str:
    escola = str(linha["escola"])
    identificada = bool(linha.get("escola_identificada", True))
    tabela = pendencias_da_escola(linha)
    itens = "\n".join(f"-{r['Tipo']}: {f_int(r['Pendências'])} (ação sugerida: {r['Ação sugerida']})"
                      for _, r in tabela.iterrows())
    texto_prazo = prazo.strftime("%d/%m/%Y") if prazo else "a combinar"
    if identificada:
        abertura = f"Prezada direção — {escola},"
        corpo = (f"A última carga de dados de frequência e avaliação encontrou {f_int(linha['qtd_pendencias'])} "
                 f"registros com pendência de qualidade nesta escola, em {f_int(len(tabela))} tipo(s):")
        pedido = f"Pedimos a correção na origem, no sistema da escola, e o retorno até {texto_prazo}. "
    else:
        abertura = f"Prezada coordenação responsável — {escola},"
        corpo = (f"A última carga de dados encontrou {f_int(linha['qtd_pendencias'])} registros com pendência "
                 f"de qualidade sem escola identificada, em {f_int(len(tabela))} tipo(s):")
        pedido = f"Pedimos a correção na origem e o retorno até {texto_prazo}. "
    return (
        f"Assunto: pendências de qualidade de dados — {escola}\n\n"
        f"{abertura}\n\n{corpo}\n\n{itens}\n\n"
        f"{pedido}Na próxima carga, a pendência corrigida deixa de aparecer na fila.\n\n"
        "Atenciosamente,\nSecretaria\n"
    )


# ----------------------------------------------------------------------------
# estado da sessão (simulação)
# ----------------------------------------------------------------------------
def _estado() -> tuple[dict, dict]:
    st.session_state.setdefault("status_escolas", {})
    st.session_state.setdefault("historico_escolas", {})
    return st.session_state["status_escolas"], st.session_state["historico_escolas"]


def status_de(escola: str) -> str:
    return _estado()[0].get(escola, STATUS_COM[0])


def ultima_observacao(escola: str) -> str:
    hist = _estado()[1].get(escola, [])
    return hist[-1]["Observação"] if hist else ""


def registrar(escola: str, status: str, observacao: str) -> None:
    atual, hist = _estado()
    atual[escola] = status
    hist.setdefault(escola, []).append({
        "Data e hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Status": status,
        "Observação": observacao.strip(),
    })


# ----------------------------------------------------------------------------
# janela
# ----------------------------------------------------------------------------
def corpo_comunicacao(linha: pd.Series) -> None:
    """Conteúdo da janela (separado do st.dialog para poder ser testado)."""
    escola = str(linha["escola"])
    tabela = pendencias_da_escola(linha)
    st.markdown(f"**{escola}** · {f_int(linha['qtd_pendencias'])} pendências em {f_int(len(tabela))} tipo(s)")
    aba_reg, aba_msg = st.tabs(["Pendências e registro", "Mensagem para a direção"])

    with aba_reg:
        esq, dir_ = st.columns([5, 3])
        with esq:
            st.dataframe(tabela, hide_index=True, width="stretch", height=230, column_config={
                "Pendências": st.column_config.NumberColumn("Pendências", format="%d"),
                "Ação sugerida": st.column_config.TextColumn("Ação sugerida", width="large"),
            })
        with dir_:
            status = st.radio("Status da comunicação", STATUS_COM, index=STATUS_COM.index(status_de(escola)),
                              key=f"com_status_{escola}")
            observacao = st.text_area("Observação", key=f"com_obs_{escola}", height=70,
                                      placeholder="Ex.: direção avisou por e-mail; correção prevista na semana.")
            if st.button("Registrar", type="primary", key=f"com_registrar_{escola}"):
                registrar(escola, status, observacao)
                st.session_state["toast_escola"] = f"Registro salvo: {escola} · {status}"
                st.session_state["qc_versao"] = st.session_state.get("qc_versao", 0) + 1
                st.rerun()
        st.markdown("**Histórico de registros**")
        hist = _estado()[1].get(escola, [])
        if hist:
            st.dataframe(pd.DataFrame(hist[::-1]), hide_index=True, width="stretch", height=110)
        else:
            st.caption("Nenhum registro ainda para esta escola.")

    with aba_msg:
        prazo = st.date_input("Prazo para o retorno da escola", value=None, format="DD/MM/YYYY",
                              key=f"com_prazo_{escola}")
        texto = mensagem(linha, prazo)
        st.code(texto, language=None, wrap_lines=True, height=260)
        st.download_button("Baixar mensagem (.txt)", texto.encode("utf-8"),
                           file_name=f"mensagem_{escola.lower().replace(' ', '_')}.txt", mime="text/plain",
                           key=f"com_baixar_{escola}", icon=":material/download:")


@st.dialog("Comunicação com a escola", width="large")
def abrir_comunicacao(linha: pd.Series) -> None:
    corpo_comunicacao(linha)
