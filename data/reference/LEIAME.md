# Valores oficiais de referência

`referencia_oficial.csv` (criado por você, a partir de `referencia_oficial.TEMPLATE.csv`) é a
única entrada externa de `src/validacao.py`. Regras:

- Uma linha por valor. Todos os campos são obrigatórios: `fonte_oficial`, `url`, `ano`,
  `metrica`, `valor`, `unidade`, `escopo_oficial`.
- `url` aponta para o documento ou tabela de onde o valor foi lido (não para notícia que o cita).
- `escopo_oficial` diz o que a fonte cobre (ex.: se inclui geração fora do SIN). É isso que
  explica diferenças esperadas; o script não corrige nada.
- `metrica`: `geracao_total`, `geracao_hidraulica`, `geracao_eolica`, `geracao_solar`,
  `geracao_termica`. `unidade`: `GWh` ou `TWh`.
- Nunca preencha com valor de memória ou de estimativa.
