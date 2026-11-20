"""Página Resultados: a narrativa do projeto, com todos os números lidos dos parquets."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import graficos  # noqa: E402
from componentes import conclusao, decisao, o_que_mostra, secao  # noqa: E402
from dados import (  # noqa: E402
    GRUPOS, carregar, f_dec, f_int, f_pct, limites, rotulo_bimestre,
)

v = limites()
resumo = carregar("alerta_resumo")
curva = carregar("curva")
corr = carregar("correlacao")
bairro = carregar("alerta_bairro")
pend = carregar("pendencias_escola")

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
total_pend = float(pend["qtd_pendencias"].sum())

# ----------------------------------------------------------------------------
# abertura
# ----------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Avaliados no 1º bimestre", f_int(tot[1]))
c2.metric("Nível alto no 1º bimestre", f_int(alto.loc[1, "qtd_alunos"]),
          help=f"{f_pct(alto.loc[1, 'qtd_alunos'] / tot[1] * 100)} dos alunos avaliados no 1º bimestre.")
c3.metric("Com 15 faltas no 4º bimestre", f_pct(ct_tot[4] / tot[4] * 100, 0),
          help="Faltas estimadas acumuladas: teto, pois os dados não separam as justificadas.")
c4.metric("Pendências na fila", f_int(total_pend),
          help="Pendências de qualidade de dado para correção na origem.")

# ----------------------------------------------------------------------------
# 1. para quem e para quê
# ----------------------------------------------------------------------------
secao(1, "Para quem e para quê")
st.markdown(
    """
| Produto | Quem usa | Decisão que apoia |
|---|---|---|
| Alerta por aluno e bimestre | direção da escola, Agente de Frequência, CIPE | quem procurar, com quem fazer atendimento, quem comunicar ao Conselho Tutelar |
| Alerta por bairro e bimestre | equipes de busca ativa e parceiros territoriais | em quais bairros concentrar a busca ativa |
| Absenteísmo por escola e bimestre | Coordenadorias Regionais (CRE) | quais escolas acompanhar no próximo bimestre |
| Frequência e desempenho | planejamento | se os cortes de 75% e 85% marcam piora nesta rede |
| Fila de pendências de qualidade | Secretaria, que distribui às escolas | o que corrigir na origem e por onde começar |
"""
)
st.caption("A busca ativa também é territorial: a Circular E/SUBAIR 02/2026 orienta as escolas a planejá-la com "
           "o Conselho Escola-Comunidade, lideranças locais e associações de moradores.")

# ----------------------------------------------------------------------------
# 2. a rampa
# ----------------------------------------------------------------------------
secao(2, "A rampa: frequência e nota baixa")
c = curva[(curva["grupo_etario"] == "15-17") & (~curva["suprimido"])].set_index("faixa_frequencia_inicio")
lim_legal, lim_atend = v["limite_frequencia_legal"], v["limite_frequencia_atendimento"]
topo_f, base_f = 95, 60
faixa_atend = int(lim_atend // 5 * 5)   # faixa que começa no limite de atendimento (85 a 90)
faixa_legal = int(lim_legal // 5 * 5)   # faixa que começa no limite legal (75 a 80)
titulo_curva = (
    f"Quanto menor a frequência, maior a chance de nota baixa: de {f_pct(c.loc[topo_f, 'pct_registros_nota_baixa'])} "
    f"entre {topo_f}% e 100% de frequência para {f_pct(c.loc[base_f, 'pct_registros_nota_baixa'])} "
    f"entre {base_f}% e {base_f + 5}% (15 a 17 anos)"
)
conclusao(titulo_curva)
st.altair_chart(graficos.curva(curva, lim_legal, lim_atend), width="stretch", theme=None)
o_que_mostra(
    f"A chance de nota baixa cresce de forma contínua conforme a frequência cai, sem um ponto em que salte. "
    f"Na faixa de {faixa_atend}% a {faixa_atend + 5}% ela é {f_dec(c.loc[faixa_atend, 'risco_relativo_nota_baixa'])} "
    f"vez a dos alunos mais assíduos; na de {faixa_legal}% a {faixa_legal + 5}%, "
    f"{f_dec(c.loc[faixa_legal, 'risco_relativo_nota_baixa'])} vezes. É associação, não causa."
)
decisao(
    f"Os cortes de {f_dec(lim_atend, 0)}% e {f_dec(lim_legal, 0)}% das normas coincidem com marcos da curva. "
    "Escolher o corte é decidir quantos alunos a rede consegue atender."
)

# ----------------------------------------------------------------------------
# 3. correlação
# ----------------------------------------------------------------------------
secao(3, "Correlação entre frequência e nota, por bimestre")
grupo = st.radio("Grupo etário", ["todos", "15-17", "demais"], format_func=lambda g: GRUPOS[g],
                 horizontal=True, key="corr_grupo")
ano = corr[(corr["bimestre"].isna()) & (corr["grupo_etario"] == "todos")].iloc[0]
titulo_corr = (
    f"No ano, a correlação entre frequência e nota é {ano['classificacao']} "
    f"(Pearson {f_dec(ano['pearson'], 2)}, Spearman {f_dec(ano['spearman'], 2)}): "
    f"a frequência explica {f_pct(ano['r2'] * 100, 0)} da variação da nota"
)
conclusao(titulo_corr)
st.altair_chart(graficos.correlacao(corr[corr["grupo_etario"] == grupo]), width="stretch", theme=None)
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
                 hide_index=True, width="stretch")
o_que_mostra(
    "O Pearson mede o quanto frequência e nota crescem juntas em linha reta. O Spearman usa só a ordem dos "
    "alunos e não se deixa levar por valores extremos. Régua usada: abaixo de 0,3 a relação é fraca; de 0,3 até "
    "0,5, moderada; a partir de 0,5, forte. O r² é a parcela da variação da nota que a frequência explica. "
    f"No conjunto do ano, {f_pct(ano['r2'] * 100, 0)}: a relação é nítida no grupo (a rampa acima), mas "
    "insuficiente para decidir caso a caso."
)
decisao("Frequência sozinha não identifica quem precisa de ajuda. Por isso o alerta combina frequência acumulada e "
        "nota do bimestre.")

# ----------------------------------------------------------------------------
# 4. alerta por nível
# ----------------------------------------------------------------------------
secao(4, "Alerta por nível e bimestre")
modo = st.radio("Mostrar", ["Número de alunos", "% dos avaliados no bimestre"], horizontal=True, key="alerta_modo")
titulo_alerta = (
    f"O nível alto cai de {f_int(alto.loc[1, 'qtd_alunos'])} alunos no 1º bimestre para "
    f"{f_int(alto.loc[4, 'qtd_alunos'])} no 4º, mas a base avaliada também muda"
)
conclusao(titulo_alerta)
st.altair_chart(graficos.alerta_barras(resumo, modo.startswith("%")), width="stretch", theme=None)
with st.expander("Ver a tabela de alunos por nível e bimestre"):
    pivo = resumo_num.pivot(index="bimestre", columns="nivel_alerta", values="qtd_alunos").reindex(
        columns=["alto", "medio", "atencao", "sem_alerta"])
    pivo.index = [rotulo_bimestre(b) for b in pivo.index]
    pivo.columns = ["Alto", "Médio", "Atenção", "Sem alerta"]
    pivo = pivo.map(lambda x: "não se aplica" if pd.isna(x) or x == 0 else f_int(x))
    st.dataframe(pivo, width="stretch")
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
decisao("Use o nível para decidir por onde começar a busca, não para medir melhora entre bimestres.")

# ----------------------------------------------------------------------------
# 5. a regra das 15 faltas
# ----------------------------------------------------------------------------
secao(5, "A regra das 15 faltas")
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
titulo_faltas = (
    f"No 4º bimestre, {f_pct(regra.loc[3, 'pct_total'], 0)} dos avaliados somam "
    f"{v['limite_faltas_conselho_tutelar']} faltas estimadas e {f_pct(regra.loc[3, 'qtd_sem_outro_sinal'] / regra.loc[3, 'qtd_total'] * 100, 0)} "
    "deles não têm nenhum outro sinal: a lei sozinha não prioriza; o alerta prioriza"
)
conclusao(titulo_faltas)
st.altair_chart(graficos.faltas_regra(regra), width="stretch", theme=None)
o_que_mostra(
    f"No 4º bimestre, {f_int(regra.loc[3, 'qtd_total'])} alunos acumulam {v['limite_faltas_conselho_tutelar']} faltas "
    f"estimadas ou mais, e {f_int(regra.loc[3, 'qtd_sem_outro_sinal'])} deles estão sem alerta por outros critérios. "
    "O número é um teto, porque os dados não separam faltas justificadas."
)
decisao("A comunicação ao Conselho Tutelar é obrigação legal e fica em coluna própria. A ordem de atuação da escola "
        "vem dos níveis de alerta.")

# ----------------------------------------------------------------------------
# 6. território
# ----------------------------------------------------------------------------
secao(6, "Território: onde concentrar a busca ativa")
b_sel = st.radio("Bimestre", [1, 2, 3, 4], format_func=rotulo_bimestre, horizontal=True, key="terr_bim")
d = bairro[(bairro["bimestre"] == b_sel) & (bairro["bairro_informado"]) & (~bairro["suprimido"])]
d = d.sort_values(["ranking_prioridade", "bairro"]).head(15)
top = pd.DataFrame({
    "bairro": d["bairro"],
    "qtd_alto": d["qtd_alunos_alto"].astype(float),
    "qtd_alto_sem_escola": d["qtd_alunos_alto_sem_escola"].astype(float),
})
primeiro = top.iloc[0]
titulo_terr = (
    f"No {rotulo_bimestre(b_sel)}, {primeiro['bairro']} lidera com {f_int(primeiro['qtd_alto'])} alunos em nível alto, "
    f"{f_pct(primeiro['qtd_alto_sem_escola'] / primeiro['qtd_alto'] * 100, 0)} deles sem escola identificada: "
    "para esses alunos, o território é o único caminho"
)
conclusao(titulo_terr)
st.altair_chart(graficos.territorio(top), width="stretch", theme=None)
topos = {b: set(bairro[(bairro["bimestre"] == b) & (bairro["ranking_prioridade"] <= 4)]["bairro"]) for b in [1, 2, 3, 4]}
mantem = [len(topos[1] & topos[b]) for b in [2, 3, 4]]
o_que_mostra(
    f"{f_pct(alto.loc[b_sel, 'qtd_sem_escola'] / alto.loc[b_sel, 'qtd_alunos'] * 100, 0)} de todos os alunos em "
    f"nível alto no {rotulo_bimestre(b_sel)} não têm escola identificada. Dos {len(topos[1])} bairros no topo "
    f"(posição 4 ou melhor) no 1º bimestre, {mantem[0]} seguem no topo no 2º, {mantem[1]} no 3º e {mantem[2]} no 4º: "
    "a concentração é persistente. Os bairros aparecem com pseudônimo; só a Secretaria sabe qual é qual."
)
decisao("Direcione a rede territorial (Conselho Escola-Comunidade, lideranças, associações de moradores e "
        "Conselhos Tutelares) primeiro aos bairros do topo do ranking.")

# ----------------------------------------------------------------------------
# 7. qualidade
# ----------------------------------------------------------------------------
secao(7, "Qualidade: a fila de pendências como ciclo de retorno à origem")
central = pend[~pend["escola_identificada"]]
escolas = pend[pend["escola_identificada"]].sort_values(["ranking_pendencias", "escola"]).head(15)
top10 = float(escolas.head(10)["qtd_pendencias"].sum())
central_qtd = float(central["qtd_pendencias"].sum())
titulo_pend = (
    f"As 10 escolas com mais pendências concentram {f_pct(top10 / total_pend * 100, 0)} da fila; "
    f"{f_pct(central_qtd / total_pend * 100, 0)} dependem da Secretaria"
)
conclusao(titulo_pend)
st.altair_chart(graficos.pendencias(escolas), width="stretch", theme=None)
o_que_mostra(
    f"São {f_int(total_pend)} pendências, cada uma com tipo, dimensão de qualidade e responsável. As "
    f"{f_int(central_qtd)} da linha central ({central['escola'].iloc[0] if len(central) else 'Secretaria'}) são turmas "
    "sem escola no cadastro. O aluno continua no alerta enquanto o dado é corrigido: o problema volta a quem "
    "pode corrigi-lo."
)
decisao("A Secretaria distribui a lista às escolas, começando pelas do topo, e acompanha a correção pelo mesmo "
        "ranking a cada carga.")

# ----------------------------------------------------------------------------
# limites da leitura
# ----------------------------------------------------------------------------
secao(8, "Limites desta leitura")
st.markdown(
    "- A avaliação é quase toda de alunos de 15 a 17 anos; os resultados descrevem sobretudo essa faixa.\n"
    "- A evasão não pode ser medida: a falta de registro no fim do ano é recorte da extração.\n"
    "- As faltas são estimadas a partir do percentual de frequência, sem separar as justificadas.\n"
    "- Frequência e desempenho se relacionam por associação, não por causa.\n"
    "- Nenhuma tentativa de reidentificação foi feita; bairros e escolas aparecem com pseudônimo."
)
st.caption("A lista completa de limitações, o aviso de privacidade e a conferência das regras estão em Sobre os dados.")
