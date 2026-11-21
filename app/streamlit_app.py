"""Radar da Busca Ativa: entrypoint (config da página, navegação em abas, cabeçalho, aviso e rodapé).

Executar a partir da raiz do repositório:  streamlit run app/streamlit_app.py
"""

import streamlit as st

st.set_page_config(page_title="Radar da Busca Ativa", layout="wide", initial_sidebar_state="collapsed")

import graficos  # noqa: E402,F401  (registra o tema Altair único)
from componentes import aviso_anonimizacao, cabecalho, estilo, rodape  # noqa: E402

navegacao = st.navigation([
    st.Page("paginas/resultados.py", title="Resultados", default=True),
    st.Page("paginas/busca_ativa.py", title="Busca ativa"),
    st.Page("paginas/qualidade.py", title="Qualidade do dado"),
    st.Page("paginas/sobre.py", title="Sobre os dados"),
], position="top")

estilo()
cabecalho()
aviso_anonimizacao()
navegacao.run()
rodape()
