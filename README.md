# ⚡ Brazilian Energy Matrix — Analysis and Interactive Dashboard

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Plotly Dash](https://img.shields.io/badge/Plotly_Dash-2.14+-purple?logo=plotly)
![SQL](https://img.shields.io/badge/SQL-PostgreSQL-blue?logo=postgresql)
![Status](https://img.shields.io/badge/Status-Active-green)
![Sources](https://img.shields.io/badge/Data-ONS_%7C_ANEEL-orange)

## 📌 Overview

Interactive dashboard that analyzes the evolution of Brazil's electricity generation matrix between **2015 and 2024**, focusing on the energy transition and the growth of renewable sources — especially solar and wind.

The project answers questions such as:
- How has each source's share in the matrix changed over the last decade?
- Have solar and wind already surpassed any traditional source?
- What is the renewable percentage of the matrix in each year?
- How does seasonality (dry/rainy season) affect hydro generation?

---

## 🗂️ Project Structure

```
energia-brasil/
├── data/
│   ├── raw/                  # Raw data (ONS, ANEEL)
│   └── processed/            # Cleaned data ready for analysis
├── src/
│   ├── ingestao.py           # Data collection via public APIs
│   └── transformacao.py      # Cleaning, enrichment and aggregations
├── dashboard/
│   └── app.py                # Plotly Dash dashboard
├── sql/
│   └── queries_energia.sql   # Annotated SQL analyses
├── docs/
│   └── arquitetura.png       # Pipeline diagram
├── requirements.txt
└── README.md
```

---

## 🔌 Data Sources

| Source | Data | Access |
|--------|------|--------|
| **ONS** (National Electric System Operator) | Generation by plant and subsystem | [dados.ons.org.br](https://dados.ons.org.br) |
| **ANEEL** | Installed capacity — SIGA | [dadosabertos.aneel.gov.br](https://dadosabertos.aneel.gov.br) |
| **ANEEL** | Distributed generation (solar / mini generation) | [dadosabertos.aneel.gov.br](https://dadosabertos.aneel.gov.br) |

> Open data, free of charge, and regularly updated by the federal government.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Ingestion | Python + Requests + REST API |
| Transformation | Pandas, NumPy |
| Storage | Parquet (local) / Azure Blob Storage |
| SQL Analysis | PostgreSQL / DuckDB |
| Visualization | Plotly Dash + Bootstrap |
| Deploy (optional) | Azure Container Apps |

---

## 🚀 How to Run

### 1. Clone and install dependencies

```bash
git clone https://github.com/carlosMartinez93/brazil-energy-matrix.git
cd brazil-energy-matrix
pip install -r requirements.txt
```

### 2. Collect data

```bash
python src/ingestao.py
```

> **Note:** If the ONS API is unavailable, the script automatically generates realistic synthetic data for development.

### 3. Transform and process

```bash
python src/transformacao.py
```

### 4. Launch the dashboard

```bash
python dashboard/app.py
```

Access: [http://localhost:8050](http://localhost:8050)

---

## 📊 Dashboard Features

- **Interactive filters** by period (2015–2024) and energy source
- **4 dynamic KPIs**: total generation, renewable mix, solar and wind growth
- **Line chart** showing generation evolution by source over time
- **Pie chart** with composition for the last selected year
- **Stacked area chart** with percentage share of each source
- **Renewable mix indicator** with year-over-year percentage
- **Automatic insights** generated from filtered data

---

## 💡 Key Findings

1. **Solar energy was the fastest-growing source**: over 1,000% expansion between 2015 and 2024, driven by the falling cost of photovoltaic panels.

2. **Wind already surpasses thermal power** in matrix share — a crossover that occurred around 2021.

3. **Brazil maintains over 80% renewable generation**, a world-leading position that places the country in a favorable spot on the global ESG agenda.

4. **Hydro seasonality is critical**: drought years (such as 2021) force thermal plants into operation, raising energy costs and CO₂ emissions.

5. **Northeast and Center-West lead** the expansion of new renewables — solar and wind —, while the South concentrates biomass.

---

## 🗃️ Included SQL Analyses

- Total generation by source and year with percentage share
- Evolution of the renewable mix over time
- Year-over-year (YoY) growth by source
- Source ranking for the latest available year
- Hydro vs. new renewables comparison (trend crossover)
- Monthly seasonality analysis by source

---

## 📁 Generated Data

| File | Description |
|------|-------------|
| `geracao_completa.parquet` | Full monthly base by source and subsystem |
| `geracao_anual_por_fonte.parquet` | Annual aggregate with % share |
| `crescimento_solar_eolica.parquet` | Monthly series + YoY variation |
| `mix_renovavel_anual.csv` | Renewable mix by year (Power BI compatible) |

---

## 📌 Next Steps

- [ ] Integrate climate data (precipitation) to correlate with hydro variation
- [ ] Add projections through 2030 based on PNE (National Energy Plan) targets
- [ ] Deploy on Azure Container Apps with automatic data updates
- [ ] Power BI version of the dashboard for corporate context

---

## 👤 Author

**Carlos Henrique**  
Analytics Engineer | ML Engineer  
[![LinkedIn](https://img.shields.io/badge/LinkedIn-blue?logo=linkedin)](https://linkedin.com/in/carloshenrique)
[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github)](https://github.com/carloshenrique)

---

## 📄 License

MIT License — free to use, adapt, and distribute with attribution.
