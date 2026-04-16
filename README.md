# ⚡ Matriz Energética Brasileira — Análise e Dashboard Interativo

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Plotly Dash](https://img.shields.io/badge/Plotly_Dash-2.14+-purple?logo=plotly)
![SQL](https://img.shields.io/badge/SQL-PostgreSQL-blue?logo=postgresql)
![Status](https://img.shields.io/badge/Status-Ativo-green)
![Fontes](https://img.shields.io/badge/Dados-ONS_%7C_ANEEL-orange)

## 📌 Visão Geral

Dashboard interativo que analisa a evolução da matriz de geração elétrica brasileira entre **2015 e 2024**, com foco na transição energética e no crescimento das fontes renováveis — especialmente solar e eólica.

O projeto responde perguntas como:
- Como a participação das fontes na matriz mudou ao longo da última década?
- A energia solar e eólica já superaram alguma fonte tradicional?
- Qual o percentual renovável da matriz em cada ano?
- Como a sazonalidade (seca/chuva) afeta a geração hídrica?

---

## 🗂️ Estrutura do Projeto

```
energia-brasil/
├── data/
│   ├── raw/                  # Dados brutos (ONS, ANEEL)
│   └── processed/            # Dados tratados prontos para análise
├── src/
│   ├── ingestao.py           # Coleta de dados via APIs públicas
│   └── transformacao.py      # Limpeza, enriquecimento e agregações
├── dashboard/
│   └── app.py                # Dashboard Plotly Dash
├── sql/
│   └── queries_energia.sql   # Análises SQL comentadas
├── docs/
│   └── arquitetura.png       # Diagrama do pipeline
├── requirements.txt
└── README.md
```

---

## 🔌 Fontes de Dados

| Fonte | Dado | Acesso |
|-------|------|--------|
| **ONS** (Operador Nacional do Sistema Elétrico) | Geração por usina e subsistema | [dados.ons.org.br](https://dados.ons.org.br) |
| **ANEEL** | Capacidade instalada — SIGA | [dadosabertos.aneel.gov.br](https://dadosabertos.aneel.gov.br) |
| **ANEEL** | Geração distribuída (solar / mini geração) | [dadosabertos.aneel.gov.br](https://dadosabertos.aneel.gov.br) |

> Dados abertos, gratuitos e com atualização regular pelo governo federal.

---

## 🛠️ Stack Técnica

| Camada | Tecnologia |
|--------|-----------|
| Ingestão | Python + Requests + API REST |
| Transformação | Pandas, NumPy |
| Armazenamento | Parquet (local) / Azure Blob Storage |
| Análise SQL | PostgreSQL / DuckDB |
| Visualização | Plotly Dash + Bootstrap |
| Deploy (opcional) | Azure Container Apps |

---

## 🚀 Como Executar

### 1. Clone e instale dependências

```bash
git clone https://github.com/carloshenrique/energia-brasil.git
cd energia-brasil
pip install -r requirements.txt
```

### 2. Coleta os dados

```bash
python src/ingestao.py
```

> **Nota:** Se a API do ONS estiver indisponível, o script gera automaticamente dados sintéticos realistas para desenvolvimento.

### 3. Transforma e processa

```bash
python src/transformacao.py
```

### 4. Sobe o dashboard

```bash
python dashboard/app.py
```

Acesse: [http://localhost:8050](http://localhost:8050)

---

## 📊 Funcionalidades do Dashboard

- **Filtros interativos** por período (2015–2024) e fonte de energia
- **4 KPIs dinâmicos**: geração total, mix renovável, crescimento solar e eólica
- **Gráfico de linha** com evolução da geração por fonte ao longo do tempo
- **Gráfico de pizza** com composição do último ano selecionado
- **Gráfico de área empilhada** com participação percentual de cada fonte
- **Indicador de mix renovável** com percentual ano a ano
- **Insights automáticos** gerados a partir dos dados filtrados

---

## 💡 Principais Insights Encontrados

1. **A energia solar foi a fonte de maior crescimento**: expansão superior a 1.000% entre 2015 e 2024, impulsionada pela queda de custos dos painéis fotovoltaicos.

2. **A eólica já supera a termelétrica** em participação na matriz — uma inversão ocorrida por volta de 2021.

3. **O Brasil mantém mais de 80% de geração renovável**, liderança mundial que coloca o país em posição favorável na agenda ESG global.

4. **A sazonalidade hídrica é crítica**: anos de seca (como 2021) forçam acionamento de termelétricas, elevando o custo da energia e as emissões de CO₂.

5. **Nordeste e Centro-Oeste lideram** a expansão de novas renováveis — solar e eólica —, enquanto o Sul concentra a biomassa.

---

## 🗃️ Análises SQL Incluídas

- Geração total por fonte e ano com participação percentual
- Evolução do mix renovável ao longo do tempo
- Crescimento YoY (year-over-year) por fonte
- Ranking de fontes no último ano disponível
- Comparativo hídrica × novas renováveis (inversão de tendência)
- Análise de sazonalidade mensal por fonte

---

## 📁 Dados Gerados

| Arquivo | Descrição |
|---------|-----------|
| `geracao_completa.parquet` | Base completa mensal por fonte e subsistema |
| `geracao_anual_por_fonte.parquet` | Agregado anual com participação % |
| `crescimento_solar_eolica.parquet` | Série mensal + variação YoY |
| `mix_renovavel_anual.csv` | Mix renovável por ano (compatível com Power BI) |

---

## 📌 Próximos Passos

- [ ] Integrar dados climáticos (precipitação) para correlacionar com variação hídrica
- [ ] Adicionar projeções até 2030 com base nas metas do PNE (Plano Nacional de Energia)
- [ ] Deploy no Azure Container Apps com atualização automática dos dados
- [ ] Versão Power BI do dashboard para contexto corporativo

---

## 👤 Autor

**Carlos Henrique**  
Analytics Engineer | ML Engineer  
[![LinkedIn](https://img.shields.io/badge/LinkedIn-blue?logo=linkedin)]([https://linkedin.com/in/carloshenrique](https://www.linkedin.com/in/carlos-henrique-calvo-martinez-044ab9124/))
[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github)]([https://github.com/carloshenrique](https://github.com/carlosMartinez93))

---

## 📄 Licença

MIT License — livre para uso, adaptação e distribuição com atribuição.
