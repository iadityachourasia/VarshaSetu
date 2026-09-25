# Phase 3A Scientific UI Data Contract

The UI consumes only frozen Phase 2B/2C `GET /api/science` endpoints. It
never invokes legacy `/api/forecast`, `/api/metrics/*` or prediction routes.
The browser calls same-origin paths through the Next rewrite; runtime JSON
is checked with Zod in `frontend-v2/src/lib/api/science.ts`.

| UI | Endpoints | Required meaning |
|---|---|---|
| Overview | `/status`, `/model-comparison`, `/verification`, `/demo-cases` | 2019 9.73% is computed from M0 and M2 RMSE returned by API |
| Forecast Explorer | `/cases`, `/demo-cases`, `/cases/{id}`, `/rainfall`, `/regime`, `/fss`, `/geometry/districts` | three paired fields use one mask, grid and rainfall legend |
| Extreme Rain | `/cases`, `/demo-cases`, `/probabilities`, `/rainfall`, `/geometry/districts`, `/verification` | event probability is not deterministic rainfall; IMD used only in historical verification |
| District Intelligence | `/cases`, `/demo-cases`, `/districts`, `/geometry/districts` | actual area-overlap product; polygon source and license shown |
| Verification | `/model-comparison`, `/verification` | M0–M4 same paired deterministic population; FSS raw/corrected denominator case counts are shown separately |
| Methodology | `/status` | source, split, limitations and hashes |

The rainfall API includes `raw`, `corrected`, `observed`, `valid_mask`,
`unit=mm/24h`, and `grid`. The probability API includes separate Heavy and
Very Heavy matrices, thresholds, and the same grid orientation. Null/masked
values remain absent on maps; they are not converted to zeros. Selection
uses manifest-allow-listed case IDs. Links preserve a valid case query
parameter between exploration views. Advanced provenance shows corpus,
model and manifest identity, never a local absolute path.

M2 Global XGBoost is the frozen primary deterministic product. Regime
probabilities are forecast-only pseudo-label classifier outputs, not
independently verified meteorological accuracy. The UI must not imply
that M3 or M4 beat M2, or that M2 improves heavy-event CSI/ETS/FSS.
Reliability upper bins with no samples are explicitly undefined.
