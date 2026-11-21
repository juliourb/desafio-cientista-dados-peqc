"""Página Busca ativa: simulador do técnico.

Esquerda: fila de prioridade com dados reais agregados (pseudônimos). Direita: lista nominal com alunos
FICTÍCIOS; clicar numa linha abre a ficha, onde o técnico registra status e observação.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from componentes import como_ler, decisao, o_que_mostra, secao  # noqa: E402
from dados import COR, NIVEIS, ROTULO, carregar, f_dec, f_int, f_pct, limites, rotulo_bimestre  # noqa: E402
from ficha import STATUS, abrir_ficha, status_de, ultima_observacao  # noqa: E402

v = limites()
AMOSTRA = "amostra pequena"
AVISO_FICTICIOS = ("Alunos fictícios, gerados a partir das distribuições reais e classificados pelas mesmas regras do mart. "
                   "Nenhum dado individual real é exibido.")

if "toast_ficha" in st.session_state:
    st.toast(st.session_state.pop("toast_ficha"), icon=":material/check_circle:")

# ----------------------------------------------------------------------------
# filtros (uma linha)
# ----------------------------------------------------------------------------
f1, f2, f3 = st.columns([3, 2, 4])
with f1:
    bim = st.segmented_control("Bimestre", [1, 2, 3, 4], format_func=rotulo_bimestre, default=1, required=True,
                               key="ba_bimestre", label_visibility="collapsed")
with f2:
    recorte = st.segmented_control("Recorte", ["Bairro", "Escola"], format_func=lambda r: f"Por {r.lower()}",
                                default="Bairro", required=True, key="ba_recorte", label_visibility="collapsed")
with f3:
    nivel_sel = st.segmented_control("Nível", ["todos"] + NIVEIS,
                                     format_func=lambda n: "Todos os níveis" if n == "todos" else ROTULO[n],
                                     default="todos", required=True, key="ba_nivel", label_visibility="collapsed")
    nivel = None if nivel_sel == "todos" else nivel_sel

esq, dir_ = st.columns([2, 3])

# ----------------------------------------------------------------------------
# esquerda: fila de prioridade (dados reais agregados)
# ----------------------------------------------------------------------------
with esq:
    secao("Fila de prioridade (dados reais agregados)")

    if recorte == "Bairro":
        d = carregar("alerta_bairro")
        d = d[d["bimestre"] == bim].copy()
        d["qtd_alunos_sem_alerta"] = (d["qtd_alunos_avaliados"] - d["qtd_alunos_alto"] - d["qtd_alunos_medio"]
                                      - d["qtd_alunos_atencao"])
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
            "Posição": d["ranking_prioridade"].astype(float),
            "Bairro": d["bairro"],
            "Alunos avaliados": [AMOSTRA if s else f_int(x) for s, x in zip(d["suprimido"], d["qtd_alunos_avaliados"])],
            "Alto": d["qtd_alunos_alto"].astype(float),
            "Médio": d["qtd_alunos_medio"].astype(float),
            "Atenção": d["qtd_alunos_atencao"].astype(float),
            "% alto": d["pct_alunos_alto"].astype(float),
            "Alto sem escola": d["qtd_alunos_alto_sem_escola"].astype(float),
            "Comunicar Conselho Tutelar": d["qtd_alunos_comunicar_conselho_tutelar"].astype(float),
        })
        legenda = ("Posição 1 = bairro com mais alunos em nível alto (empates desfeitos por médio e atenção). "
                   "Bairros em pseudônimo: só a Secretaria sabe qual é qual.")
        zeraveis = ["Alto", "Médio", "Atenção", "Alto sem escola", "Comunicar Conselho Tutelar"]
        compactas = ["Posição", "Bairro", "Alto", "% alto", "Alto sem escola"]
        config = {
            "Posição": st.column_config.NumberColumn("Posição", format="%d", width="small"),
            "Alto": st.column_config.ProgressColumn("Alto", format="%d", min_value=0,
                                                    max_value=float(max(tabela["Alto"].max(), 1) if len(tabela) else 1)),
            "% alto": st.column_config.ProgressColumn("% alto", format="%.1f%%", min_value=0, max_value=100),
            "Médio": st.column_config.NumberColumn("Médio", format="%d"),
            "Atenção": st.column_config.NumberColumn("Atenção", format="%d"),
            "Alto sem escola": st.column_config.NumberColumn("Alto sem escola", format="%d"),
            "Comunicar Conselho Tutelar": st.column_config.NumberColumn("Comunicar Conselho Tutelar", format="%d"),
        }
    else:
        d = carregar("absenteismo_escola")
        d = d[d["bimestre"] == bim].copy()
        d["_ordem"] = d["qtd_alunos_abaixo_minimo_legal"].astype(float)
        d = d.sort_values(["_ordem", "escola"], ascending=[False, True], na_position="last").reset_index(drop=True)
        c_legal = f"Abaixo de {f_dec(v['limite_frequencia_legal'], 0)}%"
        c_cronico = f"Abaixo de {f_dec(v['limite_absenteismo_cronico'], 0)}% (crônico)"
        tabela = pd.DataFrame({
            "Posição": (d.index + 1).astype(float),
            "Escola": d["escola"],
            "Alunos avaliados": [AMOSTRA if s else f_int(x) for s, x in zip(d["suprimido"], d["qtd_alunos_avaliados"])],
            "Frequência média": d["frequencia_media_pct"].astype(float),
            c_legal: d["pct_alunos_abaixo_minimo_legal"].astype(float),
            c_cronico: d["pct_alunos_absenteismo_cronico"].astype(float),
            "% de 15 a 17 anos": d["pct_alunos_15_17"].astype(float),
        })
        legenda = ("Posição pela quantidade de alunos abaixo do mínimo legal de frequência no bimestre. O recorte por "
                   "escola usa a frequência do bimestre; o nível de alerta é por aluno e não se aplica aqui. "
                   "Escolas em pseudônimo; registros sem escola identificada ficam fora desta tabela.")
        zeraveis = []
        compactas = ["Posição", "Escola", "Alunos avaliados", "Frequência média", c_legal]
        config = {
            "Posição": st.column_config.NumberColumn("Posição", format="%d", width="small"),
            "Frequência média": st.column_config.NumberColumn("Frequência média", format="%.1f%%"),
            c_legal: st.column_config.ProgressColumn(c_legal, format="%.1f%%", min_value=0, max_value=100),
            c_cronico: st.column_config.NumberColumn(c_cronico, format="%.1f%%"),
            "% de 15 a 17 anos": st.column_config.NumberColumn("% de 15 a 17 anos", format="%.1f%%"),
        }

    ocultas = [c for c in zeraveis if (tabela[c].fillna(0) == 0).all()] if len(tabela) else []
    visiveis = [c for c in tabela.columns if c not in ocultas]
    resumidas = [c for c in compactas if c in visiveis]

    if nivel == "atencao" and bim == 1 and recorte == "Bairro":
        st.info("O nível Atenção compara com o bimestre anterior e não se aplica ao 1º bimestre.")
    elif tabela.empty:
        st.info("Nenhuma linha para este filtro.")
    else:
        st.dataframe(tabela.head(10), hide_index=True, width="stretch", height=310, row_height=28, column_order=resumidas,
                     column_config=config)
        if ocultas:
            st.caption("Colunas sem valores neste filtro, ocultadas: " + ", ".join(ocultas) + ".")
        with st.expander(f"Ver fila completa ({f_int(len(tabela))} linhas)"):
            st.dataframe(tabela, hide_index=True, width="stretch", height=300, column_order=visiveis,
                         column_config=config)
    decisao("Comece pelos primeiros da fila e leve a lista nominal da própria escola, que só a escola e a Secretaria têm.")
    with como_ler():
        st.caption(f"{legenda} Linhas com menos de {v['tamanho_minimo_amostra']} alunos aparecem como "
                   f"“{AMOSTRA}” e não mostram taxas.")
        o_que_mostra("A fila ordena quem merece esforço primeiro. Ela mostra a posição relativa; não identifica pessoas.")

# ----------------------------------------------------------------------------
# direita: lista nominal (demonstração com alunos fictícios)
# ----------------------------------------------------------------------------
with dir_:
    secao("Lista nominal · demonstração com alunos fictícios")
    st.warning(AVISO_FICTICIOS)

    fic = carregar("alunos_ficticios")
    coluna_entidade = "bairro" if recorte == "Bairro" else "escola"
    lista = fic[fic["bimestre"] == bim].copy()
    cabeca = st.columns([2.4, 1, 1, 1.2, 1])
    with cabeca[0]:
        entidade = st.selectbox(f"{recorte} (fictício)", ["Todos"] + sorted(fic[coluna_entidade].unique()),
                                key=f"ba_entidade_{coluna_entidade}")
    if entidade != "Todos":
        lista = lista[lista[coluna_entidade] == entidade]
    if nivel is not None:
        lista = lista[lista["nivel_alerta"] == nivel]
    lista = lista.sort_values(["ordem_nivel_alerta", "frequencia_acumulada_pct", "aluno"]).reset_index(drop=True)

    status_atual = lista["aluno"].map(status_de)
    contagem = status_atual.value_counts()
    for col, s in zip(cabeca[1:], STATUS):
        col.metric(s, f_int(contagem.get(s, 0)))

    if lista.empty:
        st.info("Nenhum aluno fictício neste filtro.")
    else:
        exibir = pd.DataFrame({
            "Aluno": lista["aluno"],
            ("Escola" if recorte == "Bairro" else "Bairro"): lista["escola" if recorte == "Bairro" else "bairro"],
            "Nível": lista["nivel_alerta"].map(ROTULO),
            "Motivos": lista["motivos"].replace("", "nenhum sinal"),
            "Status": status_atual,
            "Frequência acumulada": lista["frequencia_acumulada_pct"].map(f_pct),
            "Faltas estimadas": lista["faltas_estimadas_acumuladas"].map(lambda x: f_dec(x, 1)),
            "Conselho Tutelar": lista["comunicar_conselho_tutelar"].map({True: "Comunicar", False: "Não"}),
        })
        cor = {ROTULO[n]: COR[n] for n in NIVEIS}
        claro = {ROTULO["alto"], ROTULO["medio"]}

        def pintar(rotulo: str) -> str:
            texto = "#FFFFFF" if rotulo in claro else "#1F2A37"
            return f"background-color: {cor[rotulo]}; color: {texto}; font-weight: 600"

        st.caption("Ação do técnico: clique numa linha da tabela para abrir a ficha do aluno e registrar o status. "
                   "O status fica salvo nesta sessão.")
        chave = (f"ba_lista_{st.session_state.get('ba_tabela_versao', 0)}_{bim}_{nivel}_{coluna_entidade}_{entidade}")
        evento = st.dataframe(exibir.style.map(pintar, subset=["Nível"]), hide_index=True, width="stretch",
                              height=310, row_height=28, key=chave, on_select="rerun", selection_mode="single-row",
                              column_order=[c for c in exibir.columns if c != "Motivos"] + ["Motivos"])
        linhas = evento.selection.rows
        if linhas:
            aluno = str(lista.iloc[linhas[0]]["aluno"])
            if st.session_state.get("ba_ficha_aberta") != f"{chave}:{aluno}":
                st.session_state["ba_ficha_aberta"] = f"{chave}:{aluno}"
                abrir_ficha(aluno, int(bim))
        else:
            st.session_state["ba_ficha_aberta"] = None

        final = exibir.assign(Observação=lista["aluno"].map(ultima_observacao))
        csv = final.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        base = st.columns([1, 1, 3])
        base[0].download_button("Baixar lista (CSV)", csv, file_name=f"lista_ficticia_bimestre_{bim}.csv",
                                mime="text/csv", key="ba_download", icon=":material/download:")
        with base[1]:
            with como_ler():
                o_que_mostra("A lista junta o nível de alerta, os motivos em texto e a flag legal do Conselho Tutelar. "
                             "O nível vem das mesmas regras do mart; a flag é independente do nível.")
        with base[2]:
            decisao("Use o status para registrar o retorno de cada aluno e reordene a fila a cada bimestre.")
