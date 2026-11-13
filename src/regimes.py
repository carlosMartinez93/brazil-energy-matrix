"""
regimes.py
----------
Regra de comparabilidade entre anos, por causa de uma quebra na série de geração solar.

O que os dados mostram (calculado em transformacao.py, gravado no manifest):
  a geração solar nacional salta de um mês para o outro em mai/2023, enquanto a razão
  maio/abril nos demais anos fica numa faixa estreita. Eólica não mostra o mesmo salto.

Hipótese (NÃO confirmada no dicionário do dataset): a ONS passou a incluir uma estimativa de
geração distribuída (MMGD) na série a partir desse período. Fontes secundárias apontam nessa
direção. Até confirmar, o projeto trata a causa como hipótese e a quebra como fato.

Regra adotada (conservadora, por ano):
  - 2016–2022 é um regime; 2024 em diante é outro; 2023 é ano de transição.
  - Variação de Solar, da geração total e das participações (%) só vale entre dois anos
    do MESMO regime. Fora disso, o resultado é "n/d" (não comparável), nunca um número.
  - Hidráulica, Térmica e Eólica comparam em níveis (GWh) sem restrição.
"""

ULTIMO_ANO_REGIME_A = 2022
PRIMEIRO_ANO_REGIME_B = 2024
ANO_TRANSICAO = 2023
MES_QUEBRA = "2023-05"          # primeiro mês com o salto observado
FONTES_COM_QUEBRA = {"Solar"}   # fontes cujo nível muda de definição entre regimes

TEXTO_QUEBRA_CURTO = (
    "Quebra na série solar a partir de mai/2023 (possível inclusão de geração distribuída "
    "pela ONS; hipótese não confirmada). Variações que cruzam 2023 não são comparáveis."
)


def regime(ano: int) -> str:
    """'A' (<=2022), 'T' (2023, transição) ou 'B' (>=2024)."""
    if ano <= ULTIMO_ANO_REGIME_A:
        return "A"
    if ano >= PRIMEIRO_ANO_REGIME_B:
        return "B"
    return "T"


def comparacao_valida(ano_ini: int, ano_fim: int, fonte: str | None = None) -> bool:
    """
    True se comparar `ano_ini` com `ano_fim` é legítimo.

    fonte=None  -> geração total e participações (%): sempre afetadas pela quebra.
    fonte="Solar" -> afetada. Qualquer outra fonte -> compara em nível, sempre válido.
    """
    if fonte is not None and fonte not in FONTES_COM_QUEBRA:
        return True
    a, b = regime(ano_ini), regime(ano_fim)
    return a == b and a != "T"


def janela_comparavel(ano_ini: int, ano_fim: int, fonte: str | None = None):
    """
    Maior janela legítima que termina em `ano_fim` dentro de [ano_ini, ano_fim].

    Devolve (ini, fim) ou None. Se o intervalo pedido já é comparável, devolve ele mesmo.
    Se `ano_fim` está no regime B (>=2024) e o início cruza a quebra, encurta o início para 2024.
    Em 2023 (transição) não há janela: None.
    """
    if ano_fim <= ano_ini:
        return None
    if comparacao_valida(ano_ini, ano_fim, fonte):
        return ano_ini, ano_fim
    if regime(ano_fim) == "B":
        ini = max(ano_ini, PRIMEIRO_ANO_REGIME_B)
        if ini < ano_fim:
            return ini, ano_fim
    return None
