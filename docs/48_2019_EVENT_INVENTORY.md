# 2019 JJAS Event Inventory

Status: descriptive IMD observation inventory only. It is not model evaluation.

## Scope

The inventory covers the 124 unique observation dates needed by 122 JJAS 00 UTC
initializations and their Day-1/Day-2/Day-3 products: 2019-06-02 through
2019-10-03. Each date uses the official cached IMD 0.25-degree daily rainfall
field and the frozen 03 UTC to 03 UTC interpretation.

The machine-readable daily table is
`data/manifests/phase1e/2019-JJAS/event_inventory_daily.csv`.

## Domain statistics

| Statistic | Value |
|---|---:|
| mean of daily domain means | 8.8713 mm |
| season maximum cell rainfall | 476.9726 mm |
| mean of daily p90 values | 26.1673 mm |
| mean of daily p95 values | 42.6161 mm |
| valid cells per date | 1,301 |
| masked cells per date | 1,100 |
| masked fraction | 45.8142% |

The p90 and p95 values above are means of the independently calculated daily
spatial quantiles; they are not pooled season-wide quantiles.

## Threshold inventory

| Threshold | Days with at least one event cell | Grid-cell events | Maximum valid-area fraction |
|---|---:|---:|---:|
| Heavy, >=64.5 mm/24 h | 111 | 4,128 | 15.4157% |
| Very heavy, >=115.6 mm/24 h | 70 | 1,179 | 8.2098% |
| Extremely heavy, >=204.5 mm/24 h | 29 | 209 | 2.2744% |

Area fractions use latitude-dependent grid-cell areas over valid IMD cells, not
an unweighted count fraction. The extremely-heavy inventory is descriptive;
no classifier or probability model was trained.

## Prototype catalogue

`data/manifests/phase1e/2019-JJAS/prototype_case_catalogue.csv` contains 366
deterministic initialization/product cases. Each row stores valid date, observed
maximum, heavy and very-heavy cell fractions, raw c00 RMSE/bias when the control
pair is eligible, eligibility flags, and quarantine reason. It does not label a
"best VarshaSetu case" and contains no corrected-model result.

