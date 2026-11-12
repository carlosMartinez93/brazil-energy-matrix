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

Data comes from ONS open data ("Balanço de Energia nos Subsistemas", hourly), loaded into BigQuery and aggregated to monthly GWh by the companion project [ons-energy-pipeline](https://github.com/carlosMartinez93/ons-energy-pipeline).

```bash
gcloud auth application-default login
python src/ingestao.py
```

> **Note:** There is no synthetic fallback. If BigQuery or the source table is unavailable, `src/ingestao.py` stops with an error. `python src/ingestao.py --synthetic` writes random development data to `data/dev/` (file suffix `__SYNTHETIC`); the dashboard never reads it.

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

Differences are reported, not corrected. A gap can come from scope (SIN vs. SEB), source (ONS vs. CCEE data) and method (MMGD is an ONS estimate). The scope column records what the official source states; no further explanation is asserted. Only 2024 is reconciled externally; other years have no verified official reference yet.

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
