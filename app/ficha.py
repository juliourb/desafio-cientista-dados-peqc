"""Ficha do aluno fictício: janela (st.dialog) com a trajetória, o status e o histórico de registros.

Tudo fica em st.session_state (some ao fechar a sessão). Só alunos fictícios chegam até aqui.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import graficos
from componentes import conclusao
from dados import ROTULO, carregar, f_dec, f_pct, limites, rotulo_bimestre

STATUS = ["Pendente", "Contatado", "Não localizado", "Retornou"]


def _estado() -> tuple[dict, dict]:
    """(status atual por aluno, histórico de registros por aluno)."""
    st.session_state.setdefault("status_alunos", {})
    st.session_state.setdefault("historico_alunos", {})
    return st.session_state["status_alunos"], st.session_state["historico_alunos"]


def status_de(aluno: str) -> str:
    return _estado()[0].get(aluno, STATUS[0])


def ultima_observacao(aluno: str) -> str:
    historico = _estado()[1].get(aluno, [])
    return historico[-1]["Observação"] if historico else ""


def registrar(aluno: str, status: str, observacao: str) -> None:
    atual, historico = _estado()
    atual[aluno] = status
    historico.setdefault(aluno, []).append({
        "Data e hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Status": status,
        "Observação": observacao.strip(),
    })


def corpo_ficha(aluno: str, bimestre: int) -> None:
    """Conteúdo da ficha (separado do st.dialog para poder ser testado)."""
    v = limites()
    fic = carregar("alunos_ficticios")
    traj = fic[fic["aluno"] == aluno].sort_values("bimestre")
    atual = traj[traj["bimestre"] == bimestre]
    linha = atual.iloc[0] if len(atual) else traj.iloc[-1]

    pior = traj[traj["nivel_alerta"].isin(["alto", "medio"])]
    if len(pior):
        p = pior.iloc[0]
        titulo = (f"{aluno} entra em nível {ROTULO[p['nivel_alerta']].lower()} no {rotulo_bimestre(p['bimestre'])}, "
                  f"com frequência acumulada de {f_pct(p['frequencia_acumulada_pct'])}")
    else:
        titulo = f"{aluno} fica fora dos níveis alto e médio nos quatro bimestres"
    conclusao(titulo)

    esq, dir_ = st.columns([3, 2])
    with esq:
        st.altair_chart(graficos.ficha(traj, v["limite_frequencia_legal"], v["limite_frequencia_atendimento"], 230),
                        width="stretch", theme=None)
        st.caption("A linha tracejada é a frequência do bimestre; a linha cheia, a acumulada, que é a usada pelas regras.")
        st.dataframe(pd.DataFrame({
            "Bimestre": traj["bimestre"].map(rotulo_bimestre),
            "Nível": traj["nivel_alerta"].map(ROTULO),
            "Frequência no bimestre": traj["frequencia_bimestre_pct"].map(f_pct),
            "Frequência acumulada": traj["frequencia_acumulada_pct"].map(f_pct),
            "Média do bimestre": traj["nota_media_bimestre"].map(lambda x: f_dec(x, 1)),
            "Motivos": traj["motivos"].replace("", "nenhum sinal"),
        }), hide_index=True, width="stretch", height=185)
    with dir_:
        st.markdown(f"**{rotulo_bimestre(linha['bimestre'])}** · nível **{ROTULO[linha['nivel_alerta']]}** · "
                    f"{linha['motivos'] or 'nenhum sinal'}")
        st.caption(f"{linha['escola']} · {linha['bairro']}")
        status = st.radio("Status", STATUS, index=STATUS.index(status_de(aluno)), horizontal=True,
                          key=f"ficha_status_{aluno}")
        observacao = st.text_area("Observação do técnico", key=f"ficha_obs_{aluno}", height=80,
                                  placeholder="Ex.: família contatada por telefone; retorno combinado.")
        if st.button("Registrar", type="primary", key=f"ficha_registrar_{aluno}"):
            registrar(aluno, status, observacao)
            st.session_state["toast_ficha"] = f"Registro salvo: {aluno} · {status}"
            st.session_state["ba_tabela_versao"] = st.session_state.get("ba_tabela_versao", 0) + 1
            st.rerun()
        st.markdown("**Histórico de registros**")
        historico = _estado()[1].get(aluno, [])
        if historico:
            st.dataframe(pd.DataFrame(historico[::-1]), hide_index=True, width="stretch", height=140)
        else:
            st.caption("Nenhum registro ainda para este aluno.")


@st.dialog("Ficha do aluno (fictício)", width="large")
def abrir_ficha(aluno: str, bimestre: int) -> None:
    corpo_ficha(aluno, bimestre)
