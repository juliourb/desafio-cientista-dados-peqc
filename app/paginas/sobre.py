"""Página Sobre os dados: privacidade, origem do snapshot, real x fictício e conferência das regras."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from componentes import secao  # noqa: E402
from dados import REPO_URL, commit_curto, data_snapshot, f_dec, f_int, f_pct, limites, metadados  # noqa: E402

v = limites()
meta = metadados()
par = meta["paridade"]["mart"]
det = par["acumulado_frequencia_detalhe"]
ut = meta["paridade"]["unit_tests"]
minimo = v["tamanho_minimo_amostra"]

secao("1 · Aviso de privacidade")
st.markdown(
    "Os dados do desafio são anonimizados: ids de aluno e de escola e o bairro (em hash com salt) não identificam "
    "ninguém, e nenhuma tentativa de reidentificação ou de cruzamento com fontes externas foi feita. Este app vai "
    "além: **não exibe nenhum id nem hash**, nem de aluno, nem de escola, nem de bairro. Escolas e bairros reais "
    "aparecem com pseudônimo (“Escola 0001”, “Bairro 001”), o mapeamento entre pseudônimo e identificador não é "
    "guardado em lugar nenhum, e nenhuma linha individual real é publicada."
)

secao("2 · Real agregado e fictício")
st.markdown(
    "| O que aparece | Origem |\n|---|---|\n"
    "| Curva de frequência x nota baixa, correlações, alertas por nível, ranking de bairros e escolas, fila de "
    "pendências | **Real e agregado**, vindo dos marts do projeto dbt, com pseudônimos |\n"
    "| Lista nominal e ficha do aluno | **Fictício** (120 alunos, semente fixa), gerado a partir das distribuições "
    "reais e classificado pelas mesmas regras do mart |"
)
st.caption("Os alunos fictícios têm escolas e bairros fictícios (“Escola Demonstração A”, “Bairro Demonstração 1”) "
           "sem relação com os pseudônimos reais. A coluna `ficticio` é verdadeira em todas as linhas.")
st.caption("A evolução dos fictícios foi calibrada para não contradizer a tendência agregada observada; "
           "não representa efeito de intervenção.")

secao("3 · Supressão de amostras pequenas")
st.markdown(
    f"Linhas com menos de **{minimo} alunos** (limite `tamanho_minimo_amostra` do projeto) aparecem como "
    "“amostra pequena”: as taxas, os percentuais e as contagens de alunos da linha ficam em branco. Nos marts do "
    "dbt a taxa continua visível para uso interno; neste snapshot aberto ela é suprimida."
)
st.markdown(
    "**Exceção, e por quê.** A fila de pendências por escola não é suprimida: suas contagens são de **registros com "
    "problema de dado**, não de atributos de alunos, e o ranking só cumpre o papel de apontar por onde começar a "
    "correção se mostrar todas as escolas."
)

secao("4 · Como o snapshot é gerado")
st.markdown("O snapshot é gerado por um script que só lê (SELECT) os marts do BigQuery e grava arquivos pequenos "
            "em `app/data/`. A partir da raiz do repositório, no ambiente do dbt:")
st.code("python scripts/exportar_snapshot.py", language="bash")
st.markdown(
    f"O snapshot atual é de **{data_snapshot()}**, gerado sobre o commit `{commit_curto()}`. As regras do alerta "
    "são lidas das `vars` do `dbt_project.yml`; não há limite de política fixo no código do app."
)

secao("5 · Concordância entre as regras em Python e o dbt")
st.markdown(
    "O app reproduz em Python as regras do mart de alerta e o cálculo acumulado da frequência. A cada exportação, "
    "o script compara a réplica com o mart e **não grava nada se a concordância cair**."
)
st.markdown(
    f"- Nível de alerta, flag do Conselho Tutelar, sinais e motivos: **{f_pct(par['classificacao_nivel_pct'], 0)}** "
    f"de concordância em {f_int(par['linhas_comparadas'])} linhas de aluno e bimestre.\n"
    f"- Faltas estimadas acumuladas: **{f_pct(par['acumulado_faltas_pct'], 0)}**. Variação de frequência: "
    f"**{f_pct(par['acumulado_variacao_pct'], 0)}**.\n"
    f"- Casos de borda dos unit tests do dbt: **{ut['ok']} de {ut['casos']}**."
)
pct_empate = det["n_divergentes_em_empate"] / det["n_linhas"] * 100
st.markdown(
    f"A frequência acumulada coincide com a do dbt em todas as linhas, exceto em {f_pct(pct_empate, 2)} "
    f"({f_int(det['n_divergentes_em_empate'])} de {f_int(det['n_linhas'])}) de empates de arredondamento "
    "(diferença de 0,1 p.p. causada pela ordem de soma em ponto flutuante); "
    f"nenhum deles muda o nível de alerta ({f_int(det['n_cruzam_limite'])} cruzam os limites de "
    f"{f_dec(v['limite_frequencia_legal'], 0)}% ou {f_dec(v['limite_frequencia_atendimento'], 0)}%)."
)

secao("6 · Limitações")
st.markdown(
    "- A avaliação é quase toda de alunos de 15 a 17 anos, e os resultados descrevem sobretudo essa faixa.\n"
    "- A evasão não pode ser medida, porque a falta de registro no fim do ano é recorte da extração.\n"
    "- As faltas são estimadas a partir do percentual de frequência, sem separar as justificadas. A flag do "
    "Conselho Tutelar é um teto.\n"
    "- Sem registro diário, não dá para calcular faltas consecutivas, critério que a SME-Rio usa para acionar o "
    "Agente de Frequência.\n"
    "- 18,7% dos registros de avaliação ficam sem escola. Esses alunos saem do mart por escola, mas continuam no "
    "alerta e no mart por bairro.\n"
    "- O bairro vem em hash com salt: dá para comparar bairros entre si, mas não nomeá-los nem mapeá-los.\n"
    "- A relação entre frequência e desempenho é associação, não causa.\n"
    "- Este é um protótipo (prova de conceito): os alunos da lista nominal são fictícios."
)

secao("7 · Para quem e para quê")
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

secao("8 · Links")
st.markdown(f"- [README do projeto]({REPO_URL}#readme)\n- [Repositório]({REPO_URL})")
