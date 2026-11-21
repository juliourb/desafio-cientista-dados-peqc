"""Página Qualidade do dado: a fila de pendências como ciclo de retorno à origem."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import graficos  # noqa: E402
from componentes import como_ler, conclusao, decisao, o_que_mostra, secao  # noqa: E402
from dados import carregar, f_int, f_pct  # noqa: E402
from escola_comunicacao import (  # noqa: E402
    STATUS_COM, abrir_comunicacao, status_de, tipos_da_linha, ultima_observacao,
)
from graficos import TIPOS_PENDENCIA  # noqa: E402

pend = carregar("pendencias_escola")
total_pend = float(pend["qtd_pendencias"].sum())
central = pend[~pend["escola_identificada"]]
escolas = pend[pend["escola_identificada"]].sort_values(["ranking_pendencias", "escola"]).head(10)
top10 = float(escolas["qtd_pendencias"].sum())
central_qtd = float(central["qtd_pendencias"].sum())

st.markdown("#### Qualidade: a fila de pendências como ciclo de retorno à origem")

k1, k2, k3 = st.columns(3)
k1.metric("Pendências na fila", f_int(total_pend),
          help="Pendências de qualidade de dado para correção na origem.")
k2.metric("Nas 10 escolas do topo", f_pct(top10 / total_pend * 100, 0))
k3.metric("Dependem da Secretaria", f_pct(central_qtd / total_pend * 100, 0))

conclusao(
    f"As 10 escolas com mais pendências concentram {f_pct(top10 / total_pend * 100, 0)} da fila; "
    f"{f_pct(central_qtd / total_pend * 100, 0)} dependem da Secretaria"
)
esq, dir_ = st.columns([2, 3])
with esq.container(border=True):
    st.markdown("**Pendências por tipo**")
    st.altair_chart(graficos.pendencias_tipo(pend, 210), width="stretch", theme=None)
with dir_.container(border=True):
    st.markdown("**Top 10 escolas (pseudônimo)**")
    st.altair_chart(graficos.pendencias(escolas, 210), width="stretch", theme=None)

linha_dec = st.columns([6, 1.3], vertical_alignment="center")
with linha_dec[0]:
    decisao("A Secretaria distribui a lista às escolas, começando pelas do topo, e acompanha a correção pelo mesmo "
            "ranking a cada carga.")
with linha_dec[1], como_ler():
    o_que_mostra(
        f"São {f_int(total_pend)} pendências, cada uma com tipo, dimensão de qualidade e responsável. As "
        f"{f_int(central_qtd)} da linha central ({central['escola'].iloc[0] if len(central) else 'Secretaria'}) são turmas "
        "sem escola no cadastro. O aluno continua no alerta enquanto o dado é corrigido: o problema volta a quem "
        "pode corrigi-lo."
    )
    st.markdown(
        "**Exceção, e por quê.** A fila de pendências por escola não é suprimida: suas contagens são de **registros com "
        "problema de dado**, não de atributos de alunos, e o ranking só cumpre o papel de apontar por onde começar a "
        "correção se mostrar todas as escolas."
    )

# ----------------------------------------------------------------------------
# comunicação com as escolas (simulação; acompanhamento só na sessão do navegador)
# ----------------------------------------------------------------------------
if "toast_escola" in st.session_state:
    st.toast(st.session_state.pop("toast_escola"), icon=":material/check_circle:")

secao("Comunicação com as escolas")
st.info("As escolas aparecem com pseudônimo; na operação real, a Secretaria, que tem a chave, faz a correspondência. "
        "O acompanhamento é uma simulação e vale só para a sessão do navegador.")

lista_escolas = pend[pend["escola_identificada"]].sort_values(["ranking_pendencias", "escola"]).reset_index(drop=True)
status_escolas = lista_escolas["escola"].map(status_de)
contagem = status_escolas.value_counts()

cont = st.columns([1, 1, 1, 1.5, 2.2])
for col, s in zip(cont[:4], STATUS_COM):
    col.metric(s, f_int(contagem.get(s, 0)))
with cont[4].container(border=True):
    if len(central):
        linha_central = central.iloc[0]
        st.markdown(f"**{linha_central['escola']}** · {f_int(linha_central['qtd_pendencias'])} pendências · "
                    f"{status_de(linha_central['escola']).lower()}")
        if st.button("Registrar comunicação", key="qc_central"):
            abrir_comunicacao(linha_central)

f1, f2, f3 = st.columns([5, 2.2, 1.8], vertical_alignment="center")
with f1:
    filtro = st.segmented_control("Status da comunicação", ["Todos"] + STATUS_COM, default="Todos", required=True,
                                  key="qc_filtro", label_visibility="collapsed")
tipos_txt = lista_escolas.apply(
    lambda r: ", ".join(TIPOS_PENDENCIA[c] for c in tipos_da_linha(r)), axis=1)
tabela_esc = pd.DataFrame({
    "Posição": lista_escolas["ranking_pendencias"].astype(float),
    "Escola": lista_escolas["escola"],
    "Pendências": lista_escolas["qtd_pendencias"].astype(float),
    "Status": status_escolas,
    "Tipos com pendência": tipos_txt,
})
acompanhamento = tabela_esc.assign(Observação=lista_escolas["escola"].map(ultima_observacao))
if len(central):
    linha_c = pd.DataFrame([{
        "Posição": None, "Escola": linha_central["escola"], "Pendências": float(linha_central["qtd_pendencias"]),
        "Status": status_de(linha_central["escola"]),
        "Tipos com pendência": ", ".join(TIPOS_PENDENCIA[c] for c in tipos_da_linha(linha_central)),
        "Observação": ultima_observacao(linha_central["escola"]),
    }])
    acompanhamento = pd.concat([linha_c, acompanhamento], ignore_index=True)
csv = acompanhamento.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
f2.download_button("Baixar acompanhamento (CSV)", csv, file_name="acompanhamento_escolas.csv", mime="text/csv",
                   key="qc_download", icon=":material/download:")

visivel = lista_escolas if filtro == "Todos" else lista_escolas[status_escolas == filtro]
tabela_vis = tabela_esc.loc[visivel.index].reset_index(drop=True)
visivel = visivel.reset_index(drop=True)
if visivel.empty:
    st.info("Nenhuma escola com este status.")
else:
    st.caption("Clique numa linha da tabela para abrir a comunicação com a escola.")
    chave = f"qc_lista_{st.session_state.get('qc_versao', 0)}_{filtro}"
    evento = st.dataframe(
        tabela_vis, hide_index=True, width="stretch", height=252, row_height=28, key=chave,
        on_select="rerun", selection_mode="single-row",
        column_config={
            "Posição": st.column_config.NumberColumn("Posição", format="%d", width="small"),
            "Pendências": st.column_config.ProgressColumn("Pendências", format="%d", min_value=0,
                                                          max_value=float(tabela_esc["Pendências"].max())),
        },
    )
    linhas = evento.selection.rows
    if linhas:
        escolhida = visivel.iloc[linhas[0]]
        token = f"{chave}:{escolhida['escola']}"
        if st.session_state.get("qc_aberta") != token:
            st.session_state["qc_aberta"] = token
            abrir_comunicacao(escolhida)
    else:
        st.session_state["qc_aberta"] = None

with f3, como_ler("Como ler"):
    st.markdown(
        "**Ciclo de retorno.** O teste de qualidade do projeto encontra o problema, que vira uma pendência na fila. "
        "A escola corrige na origem, no sistema onde o dado nasce. A nova carga traz o dado corrigido e a pendência "
        "sai da fila. Por isso o último status é “Corrigida — aguarda nova carga”: só a carga seguinte confirma."
    )
    st.markdown(
        "A lista segue o ranking de pendências. A linha da Secretaria reúne as pendências sem escola identificada e "
        "aparece à parte: o responsável por elas é a própria Secretaria, e não uma escola."
    )
