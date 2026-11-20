"""Radar da Busca Ativa: entrypoint (config da página, navegação, tema dos gráficos e rodapé).

Executar a partir da raiz do repositório:  streamlit run app/streamlit_app.py
"""

import streamlit as st

st.set_page_config(page_title="Radar da Busca Ativa", layout="wide", initial_sidebar_state="expanded")

import graficos  # noqa: E402,F401  (registra o tema Altair único)
from componentes import rodape  # noqa: E402

st.title("Radar da Busca Ativa")
st.markdown(
    "Frequência, desempenho e prioridade territorial na rede municipal do Rio · "
    "prova de conceito com dados anonimizados"
)

navegacao = st.navigation([
    st.Page("paginas/resultados.py", title="Resultados", default=True),
    st.Page("paginas/busca_ativa.py", title="Busca ativa"),
    st.Page("paginas/sobre.py", title="Sobre os dados"),
])
navegacao.run()
rodape()
