"""Testes das páginas do app com streamlit.testing.v1.AppTest.

Rodar a partir da raiz do repositório:  python app/testes/testar_paginas.py

Falha se alguma das 4 páginas levantar exceção; se faltar o título, o aviso de anonimização ou o rodapé;
se faltar o aviso de alunos fictícios na Busca ativa; se qualquer texto renderizado (inclusive células de
tabela) parecer um identificador hexadecimal longo; ou se um trecho explicativo do inventário de textos da
versão anterior (arquivo indicado em RMI_INVENTARIO, padrão %TEMP%/rmi_guard2/textos_antes.json) deixar de
existir em alguma página.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.stdout.reconfigure(encoding="utf-8")
APP = Path(__file__).resolve().parents[1]
ENTRADA = str(APP / "streamlit_app.py")
HEX = re.compile(r"^[0-9a-fA-F]{16,}$")
AVISO = ("Alunos fictícios, gerados a partir das distribuições reais e classificados pelas mesmas regras do mart. "
         "Nenhum dado individual real é exibido.")
AVISO_ANON = "Dados anonimizados do desafio · escolas e bairros com pseudônimos · lista nominal com alunos fictícios"
PAGINAS = [
    ("Resultados", "paginas/resultados.py"),
    ("Busca ativa", "paginas/busca_ativa.py"),
    ("Qualidade do dado", "paginas/qualidade.py"),
    ("Sobre os dados", "paginas/sobre.py"),
]
# Trechos do inventário que mudaram de propósito: o status deixou de ser editado na tabela e passou a ser
# registrado na ficha do aluno, então a instrução antiga ficaria falsa. Antigo -> novo.
EXCECOES = {
    "Ação do técnico: altere o status de cada aluno na última coluna. O status fica salvo nesta sessão.":
        "Ação do técnico: clique numa linha da tabela para abrir a ficha do aluno e registrar o status. "
        "O status fica salvo nesta sessão.",
}

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
        saida += [str(m.label), str(m.value), str(getattr(m, "delta", "") or ""), str(getattr(m, "help", "") or "")]
    for tipo in ("selectbox", "radio", "segmented_control"):
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
    if hasattr(df, "data"):  # Styler
        df = df.data
    cel = [str(c) for c in df.columns]
    for c in df.columns:
        cel += [str(x) for x in df[c].tolist()]
    return cel


def sem_hex(at: AppTest) -> bool:
    return not any(HEX.match(t.strip()) for t in textos(at))


def rodar(pagina: str | None, estado: dict | None = None) -> AppTest:
    at = AppTest.from_file(ENTRADA, default_timeout=120)
    at.run()
    if pagina:
        at.switch_page(pagina)
        at.run()
    if estado:
        for k, val in estado.items():
            at.session_state[k] = val
        at.run()
    return at


def explicativos(brutos: list[str]) -> set[str]:
    """Linhas com 60 caracteres ou mais, sem marcas de markdown nem numeração de seção."""
    saida: set[str] = set()
    for t in brutos:
        for linha in str(t).split("\n"):
            linha = re.sub(r"^\s*(#+|[-*]\s)\s*", "", linha.strip()).replace("**", "").strip()
            linha = re.sub(r"^\d+ · ", "", linha)
            if len(linha) >= 60 and not re.fullmatch(r"[|\-\s:]+", linha):
                saida.add(linha)
    return saida


corpus: set[str] = set()
for nome, arquivo in PAGINAS:
    print(f"[{nome}]")
    at = rodar(None if arquivo.endswith("resultados.py") else arquivo)
    verificar(len(at.exception) == 0, f"{nome}: sem exceção ({[e.value for e in at.exception][:1]})")
    verificar(any(str(m.value).strip() == "# Radar da Busca Ativa" for m in at.markdown),
              f"{nome}: título 'Radar da Busca Ativa' uma única vez no cabeçalho")
    verificar(sum("# Radar da Busca Ativa" in str(m.value) for m in at.markdown) == 1,
              f"{nome}: o título não se repete dentro da página")
    verificar(len([c for c in at.caption if AVISO_ANON in str(c.value)]) == 1,
              f"{nome}: aviso de anonimização compacto no topo")
    verificar(len([c for c in at.caption if "Snapshot" in str(c.value) and "paridade com o dbt: 100%" in str(c.value)]) == 1,
              f"{nome}: cabeçalho com snapshot, commit e paridade")
    rodape = [c.value for c in at.caption if "Snapshot de" in str(c.value) and "commit" in str(c.value)]
    verificar(len(rodape) == 1, f"{nome}: rodapé com data do snapshot e commit")
    verificar(sem_hex(at), f"{nome}: nenhum texto bate com ^[0-9a-fA-F]{{16,}}$")
    if nome == "Busca ativa":
        verificar(any(AVISO == w.value for w in at.warning), "Busca ativa: aviso de dados fictícios")
        verificar(len(at.dataframe) >= 2, "Busca ativa: fila de prioridade e lista nominal exibidas")
        verificar(len(at.metric) == 4, "Busca ativa: contadores de status (Pendente, Contatado, Não localizado, Retornou)")
    corpus |= explicativos(textos(at))

# variante por escola e ficha do aluno: textos que só aparecem nesses estados
print("[Busca ativa: recorte por escola]")
at = rodar("paginas/busca_ativa.py", {"ba_recorte": "Escola"})
verificar(len(at.exception) == 0, "Busca ativa por escola: sem exceção")
corpus |= explicativos(textos(at))

print("[Ficha do aluno (janela)]")
fic = pd.read_parquet(APP / "data" / "alunos_ficticios.parquet")
primeiro = fic[fic["bimestre"] == 1].sort_values(["ordem_nivel_alerta", "frequencia_acumulada_pct", "aluno"]).iloc[0]["aluno"]
codigo = (f"import sys\nsys.path.insert(0, r'{APP}')\nimport graficos\nfrom ficha import corpo_ficha\n"
          f"corpo_ficha({primeiro!r}, 1)\n")
at = AppTest.from_string(codigo, default_timeout=120)
at.run()
verificar(len(at.exception) == 0, f"Ficha de {primeiro}: sem exceção ({[e.value for e in at.exception][:1]})")
verificar(sem_hex(at), "Ficha: nenhum texto bate com a regex de identificador")
verificar(len(at.radio) == 1 and list(at.radio[0].options) == ["Pendente", "Contatado", "Não localizado", "Retornou"],
          "Ficha: radio com os 4 status")
verificar(len(at.text_area) == 1 and any(b.label == "Registrar" for b in at.button), "Ficha: observação e botão Registrar")
corpus |= explicativos(textos(at))

# filtros da Busca ativa: bimestre, recorte e nível (nenhuma combinação pode quebrar)
print("[Busca ativa: filtros]")
for bim in (1, 4):
    for recorte in ("Bairro", "Escola"):
        for nivel in ("todos", "alto", "atencao", "sem_alerta"):
            at = rodar("paginas/busca_ativa.py", {"ba_bimestre": bim, "ba_recorte": recorte, "ba_nivel": nivel})
            ok = len(at.exception) == 0 and sem_hex(at) and any(AVISO == w.value for w in at.warning)
            verificar(ok, f"Busca ativa: bimestre {bim}, {recorte}, nível {nivel}")

# controles dos Resultados: grupo da correlação, modo do alerta e bimestre do território
print("[Resultados: controles]")
for chave, valores in (("corr_grupo", ["15-17", "demais", "todos"]),
                       ("alerta_modo", ["% dos avaliados no bimestre", "Número de alunos"]),
                       ("terr_bim", [1, 2, 3, 4])):
    for valor in valores:
        at = rodar(None, {chave: valor})
        verificar(len(at.exception) == 0 and sem_hex(at), f"Resultados: {chave} = {valor}")

# preservação de texto: nada do inventário da versão anterior pode ter sumido (G6)
print("[Inventário de textos]")
caminho = Path(os.environ.get("RMI_INVENTARIO", Path(tempfile.gettempdir()) / "rmi_guard2" / "textos_antes.json"))
if caminho.exists():
    antes = json.loads(caminho.read_text(encoding="utf-8"))
    unicos = {t for lista in antes.values() for t in lista}
    ausentes = []
    for t in sorted(unicos):
        t_norm = re.sub(r"^\d+ · ", "", t)
        if t_norm in corpus:
            continue
        if t in EXCECOES and EXCECOES[t] in corpus:
            continue
        ausentes.append(t)
    print(f"  {len(unicos) - len(ausentes)} de {len(unicos)} trechos únicos encontrados "
          f"({len(EXCECOES)} troca(s) deliberada(s) conferida(s))")
    for t in ausentes:
        print("    ausente:", t[:110])
    verificar(not ausentes, "inventário de textos preservado")
else:
    print(f"  inventário não encontrado em {caminho}; conferência ignorada")

print()
if falhas:
    print(f"{len(falhas)} FALHA(S)")
    sys.exit(1)
print("TODOS OS TESTES PASSARAM")
