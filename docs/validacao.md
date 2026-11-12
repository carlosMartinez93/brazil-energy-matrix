## Validation

Project data source: ONS - Balanço de Energia nos Subsistemas (horário), dataset balanco_energia_subsistema_ho - table `ons-energy-pipeline.dbt_dev.mart_ons__monthly_generation_by_source`, extracted on 2026-11-12T20:32:28+00:00 (UTC), months 2015-01 to 2026-11.

### Internal reconciliation

| Check | Result |
|---|---|
| Months compared (sum of the 4 subsystems vs. ONS national total, SIN) | 143 |
| Maximum absolute deviation | 0.5098% |
| Mean absolute deviation | 0.0038% |
| Years included (complete) | 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025 |
| Years excluded | 2015 (mês com horas incompletas); 2026 (menos de 12 meses em algum subsistema) |

### External reconciliation

| Source | Period | Metric | Official | This project | Difference | Difference % | Official source scope |
|---|---|---|---|---|---|---|---|
| [MME - Boletim Anual de Monitoramento do Sistema Elétrico Brasileiro, consolidação 2024 (publicado em 21/05/2025)](https://www.gov.br/mme/pt-br/assuntos/secretarias/secretaria-nacional-energia-eletrica/publicacoes/boletim-anual-de-monitoramento-do-sistema-eletrico/consolidacao-2024/boletim-especial-consolidacao-2024_snee-ddos-vfinal.docx) | 2024 | geracao_total | 687.7 TWh | 695.0 TWh | 7.3 TWh | +1.06% | Geração verificada no SEB (Sistema Elétrico Brasileiro) em 2024, incluindo MMGD (valores de MMGD estimados pelo ONS); valores com base nos dados abertos da CCEE; fontes do boletim: CCEE e ONS |

Differences are reported, not corrected. When the official source covers a wider scope than ONS operational data, a gap is expected and must be read together with the scope column.
