"""Página Qualidade do dado: a fila de pendências como ciclo de retorno à origem."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

import graficos  # noqa: E402
from componentes import como_ler, conclusao, decisao, o_que_mostra  # noqa: E402
from dados import carregar, f_int, f_pct  # noqa: E402

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
    st.altair_chart(graficos.pendencias_tipo(pend, 300), width="stretch", theme=None)
with dir_.container(border=True):
    st.markdown("**Top 10 escolas (pseudônimo)**")
    st.altair_chart(graficos.pendencias(escolas, 300), width="stretch", theme=None)

decisao("A Secretaria distribui a lista às escolas, começando pelas do topo, e acompanha a correção pelo mesmo "
        "ranking a cada carga.")
with como_ler():
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
