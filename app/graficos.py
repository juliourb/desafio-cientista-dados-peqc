"""Tema Altair único e funções de gráfico do app.

Regras visuais: sem grade vertical, grade horizontal leve, sem bordas, linhas de referência tracejadas com rótulo direto e tooltips com vírgula decimal (formatados no pandas).
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from dados import COR, GRUPOS, NIVEIS, ROTULO, f_dec, f_int, f_pct

TEXTO = "#1F2A37"
PRIMARIA = "#0B5C7A"
GRADE = "#E3E1DA"
MUDO = "#5F6B77"
FUNDO = "#FAFAF7"
CINZA_GRUPO = "#7A8794"

TIPOS_PENDENCIA = {
    "qtd_avaliado_fora_da_turma_matricula": "Avaliado fora da turma de matrícula",
    "qtd_faltas_acima_dias_letivos": "Faltas acima dos dias letivos",
    "qtd_frequencia_versoes_conflitantes": "Frequência com versões conflitantes",
    "qtd_avaliacao_versoes_conflitantes": "Avaliação com versões conflitantes",
    "qtd_nota_com_frequencia_zero": "Nota com frequência zero",
    "qtd_turma_sem_escola": "Turma sem escola no cadastro",
}
CORES_PENDENCIA = ["#0B5C7A", "#3E8DA8", "#8FBFD0", "#5B4B8A", "#8E83B5", "#6B7A8A"]

# rótulos de eixo com vírgula decimal e ponto de milhar
EIXO_MILHAR = "replace(format(datum.value, ','), /,/g, '.')"
EIXO_DECIMAL = "replace(format(datum.value, '.1f'), '.', ',')"


@alt.theme.register("radar", enable=True)
def _tema() -> dict:
    return {
        "config": {
            "background": FUNDO,
            "font": "sans-serif",
            "view": {"stroke": None},
            "title": {
                "anchor": "start", "color": TEXTO, "fontSize": 15, "fontWeight": 600,
                "offset": 14, "font": "sans-serif", "lineHeight": 20,
            },
            "axis": {
                "domain": False, "ticks": False, "grid": False, "gridColor": GRADE,
                "labelColor": MUDO, "titleColor": MUDO, "labelFontSize": 12,
                "titleFontSize": 12, "titleFontWeight": "normal", "labelPadding": 6,
            },
            "axisY": {"grid": True, "gridColor": GRADE},
            "legend": {
                "labelColor": TEXTO, "titleColor": MUDO, "labelFontSize": 12,
                "titleFontSize": 12, "symbolType": "square", "orient": "top", "direction": "horizontal",
            },
            "text": {"color": TEXTO, "fontSize": 12},
        }
    }


def _escala_niveis() -> alt.Scale:
    return alt.Scale(domain=[ROTULO[n] for n in NIVEIS], range=[COR[n] for n in NIVEIS])


# ----------------------------------------------------------------------------
# 2. curva frequência x nota baixa
# ----------------------------------------------------------------------------
def curva(df: pd.DataFrame, limite_legal: float, limite_atend: float) -> alt.Chart:
    d = df[~df["suprimido"]].copy()
    d["x"] = d["faixa_frequencia_inicio"] + 2.5
    d["grupo"] = d["grupo_etario"].map(GRUPOS)
    d["faixa"] = d["faixa_frequencia_inicio"].astype(int).astype(str) + "% a " + d["faixa_frequencia_fim"].astype(int).astype(str) + "%"
    d["pct_baixa"] = d["pct_registros_nota_baixa"].astype(float)
    d["txt_pct"] = d["pct_baixa"].map(f_pct)
    d["txt_risco"] = d["risco_relativo_nota_baixa"].astype(float).map(lambda v: f"{f_dec(v, 2)} vez(es) a dos mais assíduos")
    d["txt_registros"] = d["qtd_registros"].map(f_int)
    d = d[["x", "grupo", "faixa", "pct_baixa", "txt_pct", "txt_risco", "txt_registros"]]

    cor = alt.Color(
        "grupo:N",
        scale=alt.Scale(domain=[GRUPOS["15-17"], GRUPOS["demais"]], range=[PRIMARIA, CINZA_GRUPO]),
        legend=alt.Legend(title=None),
    )
    base = alt.Chart(d).encode(
        x=alt.X("x:Q", title="Frequência no bimestre (%)",
                scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(values=list(range(0, 101, 10)))),
        y=alt.Y("pct_baixa:Q", title="Registros com nota baixa (%)", scale=alt.Scale(domain=[0, 100])),
        color=cor,
    )
    linhas = base.mark_line(strokeWidth=2.5)
    pontos = base.mark_circle(size=60, opacity=1).encode(tooltip=[
        alt.Tooltip("grupo:N", title="Grupo"),
        alt.Tooltip("faixa:N", title="Frequência"),
        alt.Tooltip("txt_pct:N", title="Nota baixa"),
        alt.Tooltip("txt_risco:N", title="Risco relativo"),
        alt.Tooltip("txt_registros:N", title="Registros"),
    ])
    refs = pd.DataFrame({
        "x": [limite_legal, limite_atend],
        "rotulo": [f"{f_dec(limite_legal, 0)}% · mínimo legal", f"{f_dec(limite_atend, 0)}% · atendimento"],
    })
    regua = alt.Chart(refs).mark_rule(strokeDash=[5, 4], color=MUDO, strokeWidth=1.2).encode(x="x:Q")
    def rotulo(linha: int, alinha: str, dx: int) -> alt.Chart:
        return alt.Chart(refs.iloc[[linha]]).mark_text(
            align=alinha, dx=dx, baseline="top", dy=2, color=MUDO, fontWeight=600
        ).encode(x="x:Q", y=alt.value(2), text="rotulo:N")

    return alt.layer(regua, linhas, pontos, rotulo(0, "right", -5), rotulo(1, "left", 5)).properties(
        height=340)


# ----------------------------------------------------------------------------
# 3. correlação por bimestre
# ----------------------------------------------------------------------------
def correlacao(df: pd.DataFrame) -> alt.Chart:
    d = df[~df["suprimido"]].copy()
    longo = d.melt(id_vars=["rotulo_bimestre", "n", "classificacao"], value_vars=["pearson", "spearman"],
                   var_name="medida", value_name="r")
    longo["medida"] = longo["medida"].map({"pearson": "Pearson", "spearman": "Spearman"})
    longo["r"] = longo["r"].astype(float)
    longo["txt_r"] = longo["r"].map(lambda v: f_dec(v, 2))
    longo["txt_n"] = longo["n"].map(f_int)
    ordem = list(dict.fromkeys(d["rotulo_bimestre"]))
    base = alt.Chart(longo).encode(
        x=alt.X("rotulo_bimestre:N", title=None, sort=ordem, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("medida:N", sort=["Pearson", "Spearman"]),
        y=alt.Y("r:Q", title="Correlação (r)", scale=alt.Scale(domain=[0, 0.7]),
                axis=alt.Axis(values=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
                              labelExpr=("datum.value == 0.3 ? '0,3 · moderada' : datum.value == 0.5 ? "
                                         f"'0,5 · forte' : {EIXO_DECIMAL}"))),
        color=alt.Color("medida:N", scale=alt.Scale(domain=["Pearson", "Spearman"], range=[PRIMARIA, "#8FBFD0"]),
                        legend=alt.Legend(title=None)),
    )
    barras = base.mark_bar().encode(tooltip=[
        alt.Tooltip("rotulo_bimestre:N", title="Período"),
        alt.Tooltip("medida:N", title="Medida"),
        alt.Tooltip("txt_r:N", title="r"),
        alt.Tooltip("classificacao:N", title="Classificação"),
        alt.Tooltip("txt_n:N", title="Registros"),
    ])
    valores = base.mark_text(dy=-7, fontSize=11).encode(text="txt_r:N")
    refs = alt.Chart(pd.DataFrame({"y": [0.3, 0.5]})).mark_rule(strokeDash=[5, 4], color=MUDO).encode(y="y:Q")
    return alt.layer(refs, barras, valores).properties(height=320)


# ----------------------------------------------------------------------------
# 4. alerta por nível e bimestre
# ----------------------------------------------------------------------------
def alerta_barras(resumo: pd.DataFrame, modo_pct: bool) -> alt.Chart:
    d = resumo.copy()
    d["qtd"] = d["qtd_alunos"].fillna(0).astype(float)
    d["total"] = d.groupby("bimestre")["qtd"].transform("sum")
    d["pct"] = d["qtd"] / d["total"] * 100
    d["nivel"] = d["nivel_alerta"].map(ROTULO)
    d["acao"] = d["nivel_alerta"].map({"alto": "busca ativa", "medio": "atendimento individualizado",
                                       "atencao": "acompanhamento", "sem_alerta": "sem ação específica"})
    d["bim"] = d["bimestre"].map(lambda b: f"{int(b)}º bimestre")
    d["txt_qtd"] = d["qtd"].map(f_int)
    d["txt_pct"] = d["pct"].map(f_pct)
    d["ordem"] = d["ordem_nivel_alerta"].astype(int)
    campo, titulo_y, eixo = ("pct", "% dos alunos avaliados", alt.Axis(labelExpr="format(datum.value, '.0f') + '%'")) \
        if modo_pct else ("qtd", "Alunos avaliados", alt.Axis(labelExpr=EIXO_MILHAR))
    return (
        alt.Chart(d[["bim", "nivel", "acao", "ordem", "qtd", "pct", "txt_qtd", "txt_pct"]])
        .mark_bar()
        .encode(
            x=alt.X("bim:N", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y(f"{campo}:Q", title=titulo_y, axis=eixo, stack="zero"),
            color=alt.Color("nivel:N", scale=_escala_niveis(), legend=alt.Legend(title=None)),
            order=alt.Order("ordem:Q", sort="ascending"),
            tooltip=[alt.Tooltip("bim:N", title="Período"), alt.Tooltip("nivel:N", title="Nível"),
                     alt.Tooltip("acao:N", title="Ação"), alt.Tooltip("txt_qtd:N", title="Alunos"),
                     alt.Tooltip("txt_pct:N", title="Parcela")],
        )
        .properties(height=340)
    )


# ----------------------------------------------------------------------------
# 5. a regra das 15 faltas
# ----------------------------------------------------------------------------
def faltas_regra(df: pd.DataFrame) -> alt.Chart:
    """df: bimestre, rotulo, pct_com_alerta, pct_sem_outro_sinal, pct_total, qtd_total."""
    longo = df.melt(id_vars=["rotulo", "pct_total", "qtd_com_alerta", "qtd_sem_outro_sinal"],
                    value_vars=["pct_com_alerta", "pct_sem_outro_sinal"], var_name="parte", value_name="pct")
    longo["parte"] = longo["parte"].map({
        "pct_com_alerta": "Já em nível de alerta (alto, médio ou atenção)",
        "pct_sem_outro_sinal": "Sem nenhum outro sinal (só a regra legal)",
    })
    longo["qtd"] = longo.apply(
        lambda r: r["qtd_com_alerta"] if r["parte"].startswith("Já") else r["qtd_sem_outro_sinal"], axis=1)
    longo["txt_pct"] = longo["pct"].map(f_pct)
    longo["txt_qtd"] = longo["qtd"].map(f_int)
    topo = df[["rotulo", "pct_total"]].copy()
    topo["txt_total"] = topo["pct_total"].map(f_pct)
    barras = alt.Chart(longo).mark_bar().encode(
        x=alt.X("rotulo:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("pct:Q", title="% dos alunos avaliados", stack="zero",
                axis=alt.Axis(labelExpr="format(datum.value, '.0f') + '%'")),
        color=alt.Color("parte:N", scale=alt.Scale(
            domain=["Já em nível de alerta (alto, médio ou atenção)", "Sem nenhum outro sinal (só a regra legal)"],
            range=["#8FBFD0", PRIMARIA]), legend=alt.Legend(title=None, direction="vertical")),
        tooltip=[alt.Tooltip("rotulo:N", title="Período"), alt.Tooltip("parte:N", title="Grupo"),
                 alt.Tooltip("txt_qtd:N", title="Alunos"), alt.Tooltip("txt_pct:N", title="Parcela")],
    )
    totais = alt.Chart(topo).mark_text(dy=-8, fontWeight=600).encode(
        x=alt.X("rotulo:N"), y=alt.Y("pct_total:Q"), text="txt_total:N")
    return alt.layer(barras, totais).properties(height=340)


# ----------------------------------------------------------------------------
# 6. território
# ----------------------------------------------------------------------------
def territorio(top: pd.DataFrame) -> alt.Chart:
    """top: bairro, qtd_alto, qtd_alto_sem_escola (já ordenado por ranking)."""
    d = top.copy()
    d["Com escola identificada"] = d["qtd_alto"] - d["qtd_alto_sem_escola"]
    d["Sem escola identificada"] = d["qtd_alto_sem_escola"]
    longo = d.melt(id_vars=["bairro", "qtd_alto"], value_vars=["Com escola identificada", "Sem escola identificada"],
                   var_name="parte", value_name="qtd")
    longo["qtd"] = longo["qtd"].astype(float)
    longo["txt_qtd"] = longo["qtd"].map(f_int)
    ordem = list(d["bairro"])
    d["txt_total"] = d["qtd_alto"].map(f_int)
    barras = alt.Chart(longo).mark_bar().encode(
        y=alt.Y("bairro:N", sort=ordem, title=None, axis=alt.Axis(grid=False)),
        x=alt.X("qtd:Q", title="Alunos em nível alto", axis=alt.Axis(grid=True, labelExpr=EIXO_MILHAR), stack="zero"),
        color=alt.Color("parte:N", scale=alt.Scale(domain=["Com escola identificada", "Sem escola identificada"],
                                                  range=[COR["alto"], "#E8A29B"]), legend=alt.Legend(title="Nível alto")),
        order=alt.Order("parte:N", sort="ascending"),
        tooltip=[alt.Tooltip("bairro:N", title="Bairro"), alt.Tooltip("parte:N", title="Escola"),
                 alt.Tooltip("txt_qtd:N", title="Alunos")],
    )
    totais = alt.Chart(d).mark_text(align="left", dx=4).encode(
        y=alt.Y("bairro:N", sort=ordem), x=alt.X("qtd_alto:Q"), text="txt_total:N")
    return alt.layer(barras, totais).properties(height=max(260, 24 * len(d) + 80))


# ----------------------------------------------------------------------------
# 7. pendências de qualidade por escola
# ----------------------------------------------------------------------------
def pendencias(top: pd.DataFrame) -> alt.Chart:
    colunas = [c for c in TIPOS_PENDENCIA if c in top.columns and top[c].sum() > 0]
    longo = top.melt(id_vars=["escola", "qtd_pendencias"], value_vars=colunas, var_name="tipo", value_name="qtd")
    longo["tipo"] = longo["tipo"].map(TIPOS_PENDENCIA)
    longo["qtd"] = longo["qtd"].astype(float)
    longo["txt_qtd"] = longo["qtd"].map(f_int)
    ordem = list(top["escola"])
    totais = top[["escola", "qtd_pendencias"]].copy()
    totais["txt_total"] = totais["qtd_pendencias"].map(f_int)
    dominio = [TIPOS_PENDENCIA[c] for c in colunas]
    barras = alt.Chart(longo).mark_bar().encode(
        y=alt.Y("escola:N", sort=ordem, title=None, axis=alt.Axis(grid=False)),
        x=alt.X("qtd:Q", title="Pendências", axis=alt.Axis(grid=True, labelExpr=EIXO_MILHAR), stack="zero"),
        color=alt.Color("tipo:N", scale=alt.Scale(domain=dominio, range=CORES_PENDENCIA[:len(dominio)]),
                        legend=alt.Legend(title=None, direction="vertical")),
        tooltip=[alt.Tooltip("escola:N", title="Escola"), alt.Tooltip("tipo:N", title="Tipo"),
                 alt.Tooltip("txt_qtd:N", title="Pendências")],
    )
    rotulos = alt.Chart(totais).mark_text(align="left", dx=4).encode(
        y=alt.Y("escola:N", sort=ordem), x=alt.X("qtd_pendencias:Q"), text="txt_total:N")
    return alt.layer(barras, rotulos).properties(height=max(260, 24 * len(top) + 80))


# ----------------------------------------------------------------------------
# ficha do aluno fictício
# ----------------------------------------------------------------------------
def ficha(aluno: pd.DataFrame, limite_legal: float, limite_atend: float) -> alt.Chart:
    d = aluno.sort_values("bimestre").copy()
    d["bim"] = d["bimestre"].astype(int)
    d["nivel"] = d["nivel_alerta"].map(ROTULO)
    d["freq_bim"] = d["frequencia_bimestre_pct"].astype(float)
    d["freq_acum"] = d["frequencia_acumulada_pct"].astype(float)
    d["txt_bim"] = d["freq_bim"].map(f_pct)
    d["txt_acum"] = d["freq_acum"].map(f_pct)
    d["txt_faltas"] = d["faltas_estimadas_acumuladas"].astype(float).map(lambda v: f_dec(v, 1))
    d["txt_nota"] = d["nota_media_bimestre"].astype(float).map(lambda v: f_dec(v, 1))
    d["motivos_txt"] = d["motivos"].replace("", "nenhum sinal")
    piso = max(0, int(min(d["freq_bim"].min(), d["freq_acum"].min(), limite_legal) // 5 * 5 - 5))
    x = alt.X("bim:O", title=None, axis=alt.Axis(labelExpr="datum.value + 'º bimestre'", labelAngle=0))
    y_dom = alt.Scale(domain=[piso, 100])
    bimestral = alt.Chart(d).mark_line(strokeDash=[2, 3], color=CINZA_GRUPO, strokeWidth=1.8).encode(
        x=x, y=alt.Y("freq_bim:Q", scale=y_dom, title="Frequência (%)"))
    acumulada = alt.Chart(d).mark_line(color=PRIMARIA, strokeWidth=2.8).encode(
        x=x, y=alt.Y("freq_acum:Q", scale=y_dom))
    pontos = alt.Chart(d).mark_circle(size=130, opacity=1).encode(
        x=x, y=alt.Y("freq_acum:Q", scale=y_dom),
        color=alt.Color("nivel:N", scale=_escala_niveis(), legend=alt.Legend(title="Nível no bimestre")),
        tooltip=[alt.Tooltip("bim:O", title="Bimestre"), alt.Tooltip("nivel:N", title="Nível"),
                 alt.Tooltip("txt_bim:N", title="Frequência no bimestre"),
                 alt.Tooltip("txt_acum:N", title="Frequência acumulada"),
                 alt.Tooltip("txt_faltas:N", title="Faltas estimadas acumuladas"),
                 alt.Tooltip("txt_nota:N", title="Média do bimestre"),
                 alt.Tooltip("motivos_txt:N", title="Motivos")],
    )
    refs = pd.DataFrame({"y": [limite_legal, limite_atend],
                         "rotulo": [f"{f_dec(limite_legal, 0)}% · mínimo legal", f"{f_dec(limite_atend, 0)}% · atendimento"]})
    regua = alt.Chart(refs).mark_rule(strokeDash=[5, 4], color=MUDO, strokeWidth=1.2).encode(y=alt.Y("y:Q", scale=y_dom))
    rotulos = alt.Chart(refs).mark_text(align="left", baseline="bottom", dy=-4, dx=2, color=MUDO, fontWeight=600).encode(
        y=alt.Y("y:Q", scale=y_dom), x=alt.value(0), text="rotulo:N")
    return alt.layer(regua, rotulos, bimestral, acumulada, pontos).properties(height=320)
