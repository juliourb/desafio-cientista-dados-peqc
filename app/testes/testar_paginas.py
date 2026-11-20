"""Testes das páginas do app com streamlit.testing.v1.AppTest.

Rodar a partir da raiz do repositório:  python app/testes/testar_paginas.py

Falha se alguma página levantar exceção, se faltar o título, o rodapé ou a faixa de dados fictícios
na Busca ativa, ou se qualquer texto renderizado (inclusive células de tabela) parecer um identificador
hexadecimal longo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.stdout.reconfigure(encoding="utf-8")
APP = Path(__file__).resolve().parents[1]
ENTRADA = str(APP / "streamlit_app.py")
HEX = re.compile(r"^[0-9a-fA-F]{16,}$")
AVISO = ("Alunos fictícios, gerados a partir das distribuições reais e classificados pelas mesmas regras do mart. "
         "Nenhum dado individual real é exibido.")
PAGINAS = [
    ("Resultados", "paginas/resultados.py"),
    ("Busca ativa", "paginas/busca_ativa.py"),
    ("Sobre os dados", "paginas/sobre.py"),
]

falhas: list[str] = []


def verificar(condicao: bool, mensagem: str) -> None:
    print(("  ok    " if condicao else "  FALHA ") + mensagem)
    if not condicao:
        falhas.append(mensagem)


def textos(at: AppTest) -> list[str]:
    """Todo texto renderizado: markdown, legendas, avisos, métricas, tabelas e opções de seleção."""
    saida: list[str] = []
    for tipo in ("title", "header", "subheader", "markdown", "caption", "warning", "info", "success", "error", "text"):
        saida += [str(e.value) for e in getattr(at, tipo)]
    for m in at.metric:
        saida += [str(m.label), str(m.value)]
    for tipo in ("selectbox", "radio"):
        for w in getattr(at, tipo):
            saida += [str(o) for o in w.options]
    for df in at.dataframe:
        saida += tabela_para_textos(df.value)
    for nome in ("arrow_data_frame", "data_editor"):
        try:
            for e in at.get(nome):
                valor = getattr(e, "value", None)
                if isinstance(valor, pd.DataFrame):
                    saida += tabela_para_textos(valor)
        except Exception:
            pass
    return saida


def tabela_para_textos(df: pd.DataFrame) -> list[str]:
    cel = [str(c) for c in df.columns]
    for c in df.columns:
        cel += [str(x) for x in df[c].tolist()]
    return cel


def sem_hex(at: AppTest) -> bool:
    return not any(HEX.match(t.strip()) for t in textos(at))


def rodar(pagina: str | None) -> AppTest:
    at = AppTest.from_file(ENTRADA, default_timeout=120)
    at.run()
    if pagina:
        at.switch_page(pagina)
        at.run()
    return at


for nome, arquivo in PAGINAS:
    print(f"[{nome}]")
    at = rodar(None if arquivo.endswith("resultados.py") else arquivo)
    verificar(len(at.exception) == 0, f"{nome}: sem exceção ({[e.value for e in at.exception][:1]})")
    verificar(any(t.value == "Radar da Busca Ativa" for t in at.title), f"{nome}: título 'Radar da Busca Ativa'")
    rodape = [c.value for c in at.caption if "Snapshot de" in str(c.value) and "commit" in str(c.value)]
    verificar(len(rodape) == 1, f"{nome}: rodapé com data do snapshot e commit")
    verificar(sem_hex(at), f"{nome}: nenhum texto bate com ^[0-9a-fA-F]{{16,}}$")
    if nome == "Busca ativa":
        verificar(any(AVISO == w.value for w in at.warning), "Busca ativa: faixa de dados fictícios")
        verificar(len(at.get("arrow_data_frame")) + len(at.dataframe) >= 1, "Busca ativa: fila de prioridade exibida")

# interações da Busca ativa: bimestre, recorte e nível (nenhuma combinação pode quebrar)
print("[Busca ativa: filtros]")
at = rodar("paginas/busca_ativa.py")
for bim in (1, 4):
    for recorte in ("Bairro", "Escola"):
        for nivel in ("Todos", "Alto", "Atenção", "Sem alerta"):
            at.sidebar.selectbox(key="ba_bimestre").select(bim)
            at.sidebar.radio(key="ba_recorte").set_value(recorte)
            at.sidebar.selectbox(key="ba_nivel").select(nivel)
            at.run()
            ok = len(at.exception) == 0 and sem_hex(at) and any(AVISO == w.value for w in at.warning)
            verificar(ok, f"Busca ativa: bimestre {bim}, {recorte}, nível {nivel}")

# interações dos Resultados: grupo da correlação, modo do alerta e bimestre do território
print("[Resultados: controles]")
at = rodar(None)
for chave, valores in (("corr_grupo", ["15-17", "demais", "todos"]),
                       ("alerta_modo", ["% dos avaliados no bimestre", "Número de alunos"]),
                       ("terr_bim", [1, 2, 3, 4])):
    for valor in valores:
        at.radio(key=chave).set_value(valor)
        at.run()
        verificar(len(at.exception) == 0 and sem_hex(at), f"Resultados: {chave} = {valor}")

print()
if falhas:
    print(f"{len(falhas)} FALHA(S)")
    sys.exit(1)
print("TODOS OS TESTES PASSARAM")
