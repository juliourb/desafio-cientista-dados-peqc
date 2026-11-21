"""Página Resultados: os quatro achados em uma grade compacta, com todos os números lidos dos parquets."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import graficos  # noqa: E402
from componentes import como_ler, conclusao, decisao, o_que_mostra  # noqa: E402
from dados import (  # noqa: E402
    GRUPOS, carregar, f_dec, f_int, f_pct, limites, rotulo_bimestre,
)

ALTURA = 270  # altura dos gráficos nos cards (px)

v = limites()
resumo = carregar("alerta_resumo")
curva = carregar("curva")
corr = carregar("correlacao")
bairro = carregar("alerta_bairro")

# ----------------------------------------------------------------------------
# números-base (tudo vem do snapshot)
# ----------------------------------------------------------------------------
resumo_num = resumo.assign(
    qtd_alunos=resumo["qtd_alunos"].fillna(0).astype(float),
    qtd_alunos_15_17=resumo["qtd_alunos_15_17"].fillna(0).astype(float),
    qtd_comunicar_conselho_tutelar=resumo["qtd_comunicar_conselho_tutelar"].fillna(0).astype(float),
    qtd_sem_escola=resumo["qtd_sem_escola"].fillna(0).astype(float),
)
tot = resumo_num.groupby("bimestre")["qtd_alunos"].sum()
p1517 = resumo_num.groupby("bimestre")["qtd_alunos_15_17"].sum() / tot * 100
ct_tot = resumo_num.groupby("bimestre")["qtd_comunicar_conselho_tutelar"].sum()
sem_alerta = resumo_num[resumo_num["nivel_alerta"] == "sem_alerta"].set_index("bimestre")
alto = resumo_num[resumo_num["nivel_alerta"] == "alto"].set_index("bimestre")
ct_sem = sem_alerta["qtd_comunicar_conselho_tutelar"]

lim_legal, lim_atend = v["limite_frequencia_legal"], v["limite_frequencia_atendimento"]
faixa_atend = int(lim_atend // 5 * 5)   # faixa que começa no limite de atendimento (85 a 90)
faixa_legal = int(lim_legal // 5 * 5)   # faixa que começa no limite legal (75 a 80)
c = curva[(curva["grupo_etario"] == "15-17") & (~curva["suprimido"])].set_index("faixa_frequencia_inicio")
ano = corr[(corr["bimestre"].isna()) & (corr["grupo_etario"] == "todos")].iloc[0]

# ----------------------------------------------------------------------------
# indicadores
# ----------------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Alunos em nível alto · 1º bim.", f_int(alto.loc[1, "qtd_alunos"]),
          delta=f"{f_pct(alto.loc[1, 'qtd_alunos'] / tot[1] * 100)} dos avaliados", delta_color="off", delta_arrow="off",
          help=f"{f_pct(alto.loc[1, 'qtd_alunos'] / tot[1] * 100)} dos alunos avaliados no 1º bimestre "
               f"({f_int(tot[1])} avaliados).")
k2.metric(f"Risco de nota baixa · {faixa_legal}–{faixa_legal + 5}%",
          f"{f_dec(c.loc[faixa_legal, 'risco_relativo_nota_baixa'])}×",
          delta="o dos mais assíduos", delta_color="off", delta_arrow="off",
          help=f"Risco relativo de nota baixa na faixa de {faixa_legal}% a {faixa_legal + 5}% de frequência, "
               "em relação aos alunos mais assíduos (15 a 17 anos).")
k3.metric(f"Com {v['limite_faltas_conselho_tutelar']} faltas · 4º bim.", f_pct(ct_tot[4] / tot[4] * 100, 0),
          delta="dos avaliados", delta_color="off", delta_arrow="off",
          help="Faltas estimadas acumuladas: teto, pois os dados não separam as justificadas.")
k4.metric("Correlação no ano (Pearson)", f_dec(ano["pearson"], 2),
          delta=str(ano["classificacao"]), delta_color="off", delta_arrow="off",
          help=f"Spearman {f_dec(ano['spearman'], 2)}; r² de {f_pct(ano['r2'] * 100, 0)}.")

linha1 = st.columns(2)
linha2 = st.columns(2)

# ----------------------------------------------------------------------------
# card 1: a rampa
# ----------------------------------------------------------------------------
with linha1[0].container(border=True):
    topo_f, base_f = 95, 60
    conclusao(
        f"Quanto menor a frequência, maior a chance de nota baixa: de {f_pct(c.loc[topo_f, 'pct_registros_nota_baixa'])} "
        f"entre {topo_f}% e 100% de frequência para {f_pct(c.loc[base_f, 'pct_registros_nota_baixa'])} "
        f"entre {base_f}% e {base_f + 5}% (15 a 17 anos)"
    )
    st.altair_chart(graficos.curva(curva, lim_legal, lim_atend, ALTURA), width="stretch", theme=None)
    decisao(
        f"Os cortes de {f_dec(lim_atend, 0)}% e {f_dec(lim_legal, 0)}% das normas coincidem com marcos da curva. "
        "Escolher o corte é decidir quantos alunos a rede consegue atender."
    )
    with como_ler():
        o_que_mostra(
            f"A chance de nota baixa cresce de forma contínua conforme a frequência cai, sem um ponto em que salte. "
            f"Na faixa de {faixa_atend}% a {faixa_atend + 5}% ela é {f_dec(c.loc[faixa_atend, 'risco_relativo_nota_baixa'])} "
            f"vez a dos alunos mais assíduos; na de {faixa_legal}% a {faixa_legal + 5}%, "
            f"{f_dec(c.loc[faixa_legal, 'risco_relativo_nota_baixa'])} vezes. É associação, não causa."
        )

# ----------------------------------------------------------------------------
# card 2: correlação por bimestre
# ----------------------------------------------------------------------------
with linha1[1].container(border=True):
    conclusao(
        f"No ano, a correlação entre frequência e nota é {ano['classificacao']} "
        f"(Pearson {f_dec(ano['pearson'], 2)}, Spearman {f_dec(ano['spearman'], 2)}): "
        f"a frequência explica {f_pct(ano['r2'] * 100, 0)} da variação da nota"
    )
    grupo = st.segmented_control("Grupo etário", ["todos", "15-17", "demais"], format_func=lambda g: GRUPOS[g],
                                 default="todos", required=True, key="corr_grupo", label_visibility="collapsed")
    st.altair_chart(graficos.correlacao(corr[corr["grupo_etario"] == grupo], ALTURA - 30), width="stretch", theme=None)
    decisao("Frequência sozinha não identifica quem precisa de ajuda. Por isso o alerta combina frequência acumulada e "
            "nota do bimestre.")
    with como_ler():
        o_que_mostra(
            "O Pearson mede o quanto frequência e nota crescem juntas em linha reta. O Spearman usa só a ordem dos "
            "alunos e não se deixa levar por valores extremos. Régua usada: abaixo de 0,3 a relação é fraca; de 0,3 até "
            "0,5, moderada; a partir de 0,5, forte. O r² é a parcela da variação da nota que a frequência explica. "
            f"No conjunto do ano, {f_pct(ano['r2'] * 100, 0)}: a relação é nítida no grupo (a rampa acima), mas "
            "insuficiente para decidir caso a caso."
        )
        tabela = corr.copy()
        tabela["Período"] = tabela["rotulo_bimestre"]
        tabela["Grupo"] = tabela["grupo_etario"].map(GRUPOS)
        tabela["Registros"] = tabela["n"].map(f_int)
        tabela["Pearson"] = tabela["pearson"].map(lambda x: f_dec(x, 2))
        tabela["Spearman"] = tabela["spearman"].map(lambda x: f_dec(x, 2))
        tabela["r²"] = tabela["r2"].map(lambda x: f_dec(x, 2))
        tabela["Classificação"] = tabela["classificacao"].fillna("amostra pequena")
        with st.expander("Ver a tabela completa"):
            st.dataframe(tabela[["Período", "Grupo", "Registros", "Pearson", "Spearman", "r²", "Classificação"]],
                         hide_index=True, width="stretch", height=300)

# ----------------------------------------------------------------------------
# card 3: alerta por nível + regra das 15 faltas
# ----------------------------------------------------------------------------
with linha2[0].container(border=True):
    regra = pd.DataFrame({
        "bimestre": tot.index,
        "rotulo": [rotulo_bimestre(b) for b in tot.index],
        "qtd_total": ct_tot.reindex(tot.index).to_numpy(),
        "qtd_sem_outro_sinal": ct_sem.reindex(tot.index).fillna(0).to_numpy(),
    })
    regra["qtd_com_alerta"] = regra["qtd_total"] - regra["qtd_sem_outro_sinal"]
    regra["pct_total"] = regra["qtd_total"] / tot.to_numpy() * 100
    regra["pct_sem_outro_sinal"] = regra["qtd_sem_outro_sinal"] / tot.to_numpy() * 100
    regra["pct_com_alerta"] = regra["qtd_com_alerta"] / tot.to_numpy() * 100

    conclusao(
        f"O nível alto cai de {f_int(alto.loc[1, 'qtd_alunos'])} alunos no 1º bimestre para "
        f"{f_int(alto.loc[4, 'qtd_alunos'])} no 4º, mas a base avaliada também muda"
    )
    modo = st.segmented_control("Mostrar", ["Número de alunos", "% dos avaliados no bimestre"], default="Número de alunos",
                                required=True, key="alerta_modo", label_visibility="collapsed")
    esq, dir_ = st.columns([2, 3])
    with esq:
        st.altair_chart(graficos.alerta_barras(resumo, modo.startswith("%"), ALTURA - 40, compacto=True), width="stretch", theme=None)
    with dir_:
        st.altair_chart(graficos.faltas_regra(regra, ALTURA - 40, compacto=True), width="stretch", theme=None)
    decisao("Use o nível para decidir por onde começar a busca, não para medir melhora entre bimestres.")
    with como_ler():
        o_que_mostra(
            "Cada aluno recebe o primeiro nível em que se encaixa: alto (busca ativa), médio (atendimento "
            "individualizado), atenção (queda de frequência) ou sem alerta. O nível atenção compara com o bimestre "
            "anterior e por isso não existe no 1º bimestre."
        )
        st.caption(
            f"Efeito composição: a parcela de 15 a 17 anos entre os avaliados sobe de {f_pct(p1517[1])} no 1º bimestre "
            f"para {f_pct(p1517[4])} no 4º. A queda do nível alto mistura melhora, mudança da população avaliada e o "
            "efeito suavizador da frequência acumulada. A queda de alunos entre bimestres é recorte da extração, não evasão."
        )
        with st.expander("Ver a tabela de alunos por nível e bimestre"):
            pivo = resumo_num.pivot(index="bimestre", columns="nivel_alerta", values="qtd_alunos").reindex(
                columns=["alto", "medio", "atencao", "sem_alerta"])
            pivo.index = [rotulo_bimestre(b) for b in pivo.index]
            pivo.columns = ["Alto", "Médio", "Atenção", "Sem alerta"]
            pivo = pivo.map(lambda x: "não se aplica" if pd.isna(x) or x == 0 else f_int(x))
            st.dataframe(pivo, width="stretch")
        st.divider()
        st.markdown("**A regra das 15 faltas** (gráfico à direita)")
        conclusao(
            f"No 4º bimestre, {f_pct(regra.loc[3, 'pct_total'], 0)} dos avaliados somam "
            f"{v['limite_faltas_conselho_tutelar']} faltas estimadas e "
            f"{f_pct(regra.loc[3, 'qtd_sem_outro_sinal'] / regra.loc[3, 'qtd_total'] * 100, 0)} "
            "deles não têm nenhum outro sinal: a lei sozinha não prioriza; o alerta prioriza"
        )
        o_que_mostra(
            f"No 4º bimestre, {f_int(regra.loc[3, 'qtd_total'])} alunos acumulam {v['limite_faltas_conselho_tutelar']} faltas "
            f"estimadas ou mais, e {f_int(regra.loc[3, 'qtd_sem_outro_sinal'])} deles estão sem alerta por outros critérios. "
            "O número é um teto, porque os dados não separam faltas justificadas."
        )
        decisao("A comunicação ao Conselho Tutelar é obrigação legal e fica em coluna própria. A ordem de atuação da escola "
                "vem dos níveis de alerta.")

# ----------------------------------------------------------------------------
# card 4: território
# ----------------------------------------------------------------------------
with linha2[1].container(border=True):
    b_sel = st.segmented_control("Bimestre", [1, 2, 3, 4], format_func=rotulo_bimestre, default=1, required=True,
                                 key="terr_bim", label_visibility="collapsed")
    d = bairro[(bairro["bimestre"] == b_sel) & (bairro["bairro_informado"]) & (~bairro["suprimido"])]
    d = d.sort_values(["ranking_prioridade", "bairro"]).head(10)
    top = pd.DataFrame({
        "bairro": d["bairro"],
        "qtd_alto": d["qtd_alunos_alto"].astype(float),
        "qtd_alto_sem_escola": d["qtd_alunos_alto_sem_escola"].astype(float),
    })
    primeiro = top.iloc[0]
    conclusao(
        f"No {rotulo_bimestre(b_sel)}, {primeiro['bairro']} lidera com {f_int(primeiro['qtd_alto'])} alunos em nível alto, "
        f"{f_pct(primeiro['qtd_alto_sem_escola'] / primeiro['qtd_alto'] * 100, 0)} deles sem escola identificada: "
        "para esses alunos, o território é o único caminho"
    )
    st.altair_chart(graficos.territorio(top, ALTURA), width="stretch", theme=None)
    decisao("Direcione a rede territorial (Conselho Escola-Comunidade, lideranças, associações de moradores e "
            "Conselhos Tutelares) primeiro aos bairros do topo do ranking.")
    with como_ler():
        topos = {b: set(bairro[(bairro["bimestre"] == b) & (bairro["ranking_prioridade"] <= 4)]["bairro"])
                 for b in [1, 2, 3, 4]}
        mantem = [len(topos[1] & topos[b]) for b in [2, 3, 4]]
        o_que_mostra(
            f"{f_pct(alto.loc[b_sel, 'qtd_sem_escola'] / alto.loc[b_sel, 'qtd_alunos'] * 100, 0)} de todos os alunos em "
            f"nível alto no {rotulo_bimestre(b_sel)} não têm escola identificada. Dos {len(topos[1])} bairros no topo "
            f"(posição 4 ou melhor) no 1º bimestre, {mantem[0]} seguem no topo no 2º, {mantem[1]} no 3º e {mantem[2]} no 4º: "
            "a concentração é persistente. Os bairros aparecem com pseudônimo; só a Secretaria sabe qual é qual."
        )

# ----------------------------------------------------------------------------
# limites da leitura
# ----------------------------------------------------------------------------
with st.expander("Limites desta leitura"):
    st.markdown(
        "- A avaliação é quase toda de alunos de 15 a 17 anos; os resultados descrevem sobretudo essa faixa.\n"
        "- A evasão não pode ser medida: a falta de registro no fim do ano é recorte da extração.\n"
        "- As faltas são estimadas a partir do percentual de frequência, sem separar as justificadas.\n"
        "- Frequência e desempenho se relacionam por associação, não por causa.\n"
        "- Nenhuma tentativa de reidentificação foi feita; bairros e escolas aparecem com pseudônimo."
    )
    st.caption("A lista completa de limitações, o aviso de privacidade e a conferência das regras estão em Sobre os dados.")
