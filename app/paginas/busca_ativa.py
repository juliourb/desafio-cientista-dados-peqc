"""Página Busca ativa: simulador do técnico.

Bloco 1 usa dados reais agregados (com pseudônimos). Bloco 2 usa alunos FICTÍCIOS.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import graficos  # noqa: E402
from componentes import conclusao, decisao, o_que_mostra, secao  # noqa: E402
from dados import NIVEIS, ROTULO, carregar, f_dec, f_int, f_pct, limites, rotulo_bimestre  # noqa: E402

v = limites()
STATUS = ["Pendente", "Contatado", "Não localizado", "Retornou"]
ROTULO_PARA_NIVEL = {r: n for n, r in ROTULO.items()}

# ----------------------------------------------------------------------------
# barra lateral
# ----------------------------------------------------------------------------
st.sidebar.header("Filtros")
bim = st.sidebar.selectbox("Bimestre", [1, 2, 3, 4], format_func=rotulo_bimestre, key="ba_bimestre")
recorte = st.sidebar.radio("Recorte", ["Bairro", "Escola"], key="ba_recorte")
nivel_sel = st.sidebar.selectbox("Nível", ["Todos"] + [ROTULO[n] for n in NIVEIS], key="ba_nivel")
nivel = None if nivel_sel == "Todos" else ROTULO_PARA_NIVEL[nivel_sel]

st.markdown("### Fila de prioridade e lista de trabalho do técnico")

# ----------------------------------------------------------------------------
# bloco 1: fila de prioridade (dados reais agregados)
# ----------------------------------------------------------------------------
secao(1, "Fila de prioridade (dados reais agregados)")
AMOSTRA = "amostra pequena"

if recorte == "Bairro":
    d = carregar("alerta_bairro")
    d = d[d["bimestre"] == bim].copy()
    d["qtd_alunos_sem_alerta"] = d["qtd_alunos_avaliados"] - d["qtd_alunos_alto"] - d["qtd_alunos_medio"] - d["qtd_alunos_atencao"]
    col_nivel = {"alto": "qtd_alunos_alto", "medio": "qtd_alunos_medio", "atencao": "qtd_alunos_atencao",
                 "sem_alerta": "qtd_alunos_sem_alerta"}
    if nivel is None:
        d = d.sort_values(["ranking_prioridade", "bairro"])
    else:
        c = col_nivel[nivel]
        d = d[d["suprimido"] | (d[c].fillna(0) > 0)]
        d = d.sort_values([c, "bairro"], ascending=[False, True], na_position="last")
    d = d[d["bairro_informado"] | d["suprimido"]]
    tabela = pd.DataFrame({
        "Posição": d["ranking_prioridade"].map(f_int),
        "Bairro": d["bairro"],
        "Alunos avaliados": [AMOSTRA if s else f_int(x) for s, x in zip(d["suprimido"], d["qtd_alunos_avaliados"])],
        "Alto": d["qtd_alunos_alto"].map(f_int),
        "Médio": d["qtd_alunos_medio"].map(f_int),
        "Atenção": d["qtd_alunos_atencao"].map(f_int),
        "% alto": d["pct_alunos_alto"].map(f_pct),
        "Alto sem escola": d["qtd_alunos_alto_sem_escola"].map(f_int),
        "Comunicar Conselho Tutelar": d["qtd_alunos_comunicar_conselho_tutelar"].map(f_int),
    })
    legenda = ("Posição 1 = bairro com mais alunos em nível alto (empates desfeitos por médio e atenção). "
               "Bairros em pseudônimo: só a Secretaria sabe qual é qual.")
else:
    d = carregar("absenteismo_escola")
    d = d[d["bimestre"] == bim].copy()
    d["_ordem"] = d["qtd_alunos_abaixo_minimo_legal"].astype(float)
    d = d.sort_values(["_ordem", "escola"], ascending=[False, True], na_position="last").reset_index(drop=True)
    tabela = pd.DataFrame({
        "Posição": (d.index + 1).astype(str),
        "Escola": d["escola"],
        "Alunos avaliados": [AMOSTRA if s else f_int(x) for s, x in zip(d["suprimido"], d["qtd_alunos_avaliados"])],
        "Frequência média": d["frequencia_media_pct"].map(f_pct),
        f"Abaixo de {f_dec(v['limite_frequencia_legal'], 0)}%": d["pct_alunos_abaixo_minimo_legal"].map(f_pct),
        f"Abaixo de {f_dec(v['limite_absenteismo_cronico'], 0)}% (crônico)": d["pct_alunos_absenteismo_cronico"].map(f_pct),
        "% de 15 a 17 anos": d["pct_alunos_15_17"].map(f_pct),
    })
    legenda = ("Posição pela quantidade de alunos abaixo do mínimo legal de frequência no bimestre. O recorte por "
               "escola usa a frequência do bimestre; o nível de alerta é por aluno e não se aplica aqui. "
               "Escolas em pseudônimo; registros sem escola identificada ficam fora desta tabela.")

if nivel == "atencao" and bim == 1 and recorte == "Bairro":
    st.info("O nível Atenção compara com o bimestre anterior e não se aplica ao 1º bimestre.")
elif tabela.empty:
    st.info("Nenhuma linha para este filtro.")
else:
    st.dataframe(tabela, hide_index=True, width="stretch", height=380)
st.caption(f"{legenda} Linhas com menos de {v['tamanho_minimo_amostra']} alunos aparecem como "
           f"“{AMOSTRA}” e não mostram taxas.")
o_que_mostra("A fila ordena quem merece esforço primeiro. Ela mostra a posição relativa; não identifica pessoas.")
decisao("Comece pelos primeiros da fila e leve a lista nominal da própria escola, que só a escola e a Secretaria têm.")

# ----------------------------------------------------------------------------
# bloco 2: lista nominal (demonstração)
# ----------------------------------------------------------------------------
secao(2, "Lista nominal (demonstração)")
st.warning("Alunos fictícios, gerados a partir das distribuições reais e classificados pelas mesmas regras do mart. "
           "Nenhum dado individual real é exibido.")

fic = carregar("alunos_ficticios")
coluna_entidade = "bairro" if recorte == "Bairro" else "escola"
opcoes = ["Todos"] + sorted(fic[coluna_entidade].unique())
entidade = st.selectbox(f"{recorte} (fictício)", opcoes, key=f"ba_entidade_{coluna_entidade}")

lista = fic[fic["bimestre"] == bim].copy()
if entidade != "Todos":
    lista = lista[lista[coluna_entidade] == entidade]
if nivel is not None:
    lista = lista[lista["nivel_alerta"] == nivel]
lista = lista.sort_values(["ordem_nivel_alerta", "frequencia_acumulada_pct", "aluno"]).reset_index(drop=True)

if "status_alunos" not in st.session_state:
    st.session_state["status_alunos"] = {}
estado: dict[str, str] = st.session_state["status_alunos"]

if lista.empty:
    st.info("Nenhum aluno fictício neste filtro.")
else:
    exibir = pd.DataFrame({
        "Aluno": lista["aluno"],
        "Escola": lista["escola"],
        "Bairro": lista["bairro"],
        "Nível": lista["nivel_alerta"].map(ROTULO),
        "Motivos": lista["motivos"].replace("", "nenhum sinal"),
        "Frequência acumulada": lista["frequencia_acumulada_pct"].map(f_pct),
        "Faltas estimadas": lista["faltas_estimadas_acumuladas"].map(lambda x: f_dec(x, 1)),
        "Conselho Tutelar": lista["comunicar_conselho_tutelar"].map({True: "Comunicar", False: "Não"}),
        "Status": lista["aluno"].map(lambda a: estado.get(a, STATUS[0])),
    })
    st.caption("Ação do técnico: altere o status de cada aluno na última coluna. O status fica salvo nesta sessão.")
    editado = st.data_editor(
        exibir, hide_index=True, width="stretch", height=380,
        disabled=[c for c in exibir.columns if c != "Status"],
        column_config={"Status": st.column_config.SelectboxColumn("Status", options=STATUS, required=True)},
        key=f"ba_editor_{bim}_{nivel}_{coluna_entidade}_{entidade}",
    )
    for aluno, status in zip(editado["Aluno"], editado["Status"]):
        estado[aluno] = status
    final = editado.copy()

    contagem = final["Status"].value_counts()
    cols = st.columns(len(STATUS))
    for col, s in zip(cols, STATUS):
        col.metric(s, f_int(contagem.get(s, 0)))

    csv = final.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    st.download_button("Baixar a lista filtrada (CSV)", csv, file_name=f"lista_ficticia_bimestre_{bim}.csv",
                       mime="text/csv", key="ba_download")

    o_que_mostra("A lista junta o nível de alerta, os motivos em texto e a flag legal do Conselho Tutelar. "
                 "O nível vem das mesmas regras do mart; a flag é independente do nível.")
    decisao("Use o status para registrar o retorno de cada aluno e reordene a fila a cada bimestre.")

    # ------------------------------------------------------------------------
    # ficha do aluno fictício
    # ------------------------------------------------------------------------
    secao(3, "Ficha do aluno fictício")
    escolhido = st.selectbox("Aluno", list(lista["aluno"]), key="ba_ficha")
    traj = fic[fic["aluno"] == escolhido].sort_values("bimestre")
    pior = traj[traj["nivel_alerta"].isin(["alto", "medio"])]
    if len(pior):
        p = pior.iloc[0]
        titulo_ficha = (f"{escolhido} entra em nível {ROTULO[p['nivel_alerta']].lower()} no {rotulo_bimestre(p['bimestre'])}, "
                        f"com frequência acumulada de {f_pct(p['frequencia_acumulada_pct'])}")
    else:
        titulo_ficha = f"{escolhido} fica fora dos níveis alto e médio nos quatro bimestres"
    conclusao(titulo_ficha)
    st.altair_chart(graficos.ficha(traj, v["limite_frequencia_legal"], v["limite_frequencia_atendimento"]),
                    width="stretch", theme=None)
    resumo_ficha = traj[["bimestre", "nivel_alerta", "motivos", "frequencia_bimestre_pct",
                         "frequencia_acumulada_pct", "nota_media_bimestre"]].copy()
    st.dataframe(pd.DataFrame({
        "Bimestre": resumo_ficha["bimestre"].map(rotulo_bimestre),
        "Nível": resumo_ficha["nivel_alerta"].map(ROTULO),
        "Frequência no bimestre": resumo_ficha["frequencia_bimestre_pct"].map(f_pct),
        "Frequência acumulada": resumo_ficha["frequencia_acumulada_pct"].map(f_pct),
        "Média do bimestre": resumo_ficha["nota_media_bimestre"].map(lambda x: f_dec(x, 1)),
        "Motivos": resumo_ficha["motivos"].replace("", "nenhum sinal"),
    }), hide_index=True, width="stretch")
    st.caption("A linha tracejada é a frequência do bimestre; a linha cheia, a acumulada, que é a usada pelas regras.")
