// Phase 5A.2C: makes the live paginated case-index endpoint the primary
// source for case *listing* (selectors, Casebook), replacing the static
// bundle's index.json for that purpose. Only presentation-safe metadata is
// fetched here -- never a full grid -- so switching years/pages stays cheap.
// Falls back to the static index only on a genuine network failure (see
// lib/data-source.ts); every other outcome is a hard, visible result.
import { getOperationalCases, type OperationalYear } from "./api/operational";
import { getOperationalIndex as getStaticOperationalIndex } from "../science/frozen/operational";
import { withStaticFallback, type DataSourceResult } from "./data-source";

export const REGIME_CLASS_ORDER = ["ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED"] as const;
export type RegimeClass = (typeof REGIME_CLASS_ORDER)[number];

/** Normalized case-list item consumed by both the Forecast case selector and
 * the Casebook -- one shape regardless of whether it came from the live API
 * or the static fallback, so page components never branch on source. */
export type CaseListItem = {
  case_id: string;
  year: number;
  initialization_utc: string;
  lead_hours: number;
  lead_label: string;
  valid_date: string | null;
  year_role: string;
  month: number;
  event_heavy: boolean | null;
  event_very_heavy: boolean | null;
  pseudo_regime_class: RegimeClass | null;
  deterministic_source_eligible: boolean;
  probability_source_eligible: boolean;
  regime_source_eligible: boolean;
  ensemble_source_eligible: boolean;
  full_5_member_rainfall_qc_pass: boolean;
  m1_minus_raw_rmse_mm: number | null;
  selected_model_improved_vs_raw: boolean | null;
};

/** Deterministic display label per section 6 of the brief: date, lead, and an
 * event marker where one is known -- never the raw case_id as the primary label. */
export function caseDisplayLabel(item: CaseListItem): string {
  const date = new Date(`${item.initialization_utc.slice(0, 10)}T00:00:00Z`);
  const formatted = date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });
  const marker = item.event_very_heavy ? " · Very Heavy event" : item.event_heavy ? " · Heavy event" : "";
  return `${formatted} · ${item.lead_label}${marker}`;
}

async function fetchLiveCaseList(year: OperationalYear): Promise<CaseListItem[]> {
  const response = await getOperationalCases(year, { pageSize: 400 });
  return response.cases.map((c) => ({
    case_id: c.case_id,
    year: c.year,
    initialization_utc: c.initialization_utc,
    lead_hours: c.lead_hours,
    lead_label: c.lead_label,
    valid_date: c.valid_date,
    year_role: c.year_role,
    month: c.month,
    event_heavy: c.event_heavy,
    event_very_heavy: c.event_very_heavy,
    pseudo_regime_class: c.pseudo_regime_class,
    deterministic_source_eligible: c.deterministic_source_eligible,
    probability_source_eligible: c.probability_source_eligible,
    regime_source_eligible: c.regime_source_eligible,
    ensemble_source_eligible: c.ensemble_source_eligible,
    full_5_member_rainfall_qc_pass: c.full_5_member_rainfall_qc_pass,
    m1_minus_raw_rmse_mm: c.m1_minus_raw_rmse_mm,
    selected_model_improved_vs_raw: c.selected_model_improved_vs_raw,
  }));
}

async function fetchStaticCaseList(year: OperationalYear): Promise<CaseListItem[]> {
  const index = await getStaticOperationalIndex();
  return index.cases.filter((item) => item.year === year).map((item) => {
    const regimeIndex = item.regime_probabilities.indexOf(Math.max(...item.regime_probabilities));
    const metrics = item.frozen_case_metrics;
    return {
      case_id: item.case_id,
      year: item.year,
      initialization_utc: item.initialization_utc,
      lead_hours: item.lead_hours,
      lead_label: `Day ${item.lead_hours / 24}`,
      valid_date: item.valid_observation_date,
      year_role: item.role,
      month: Number(item.initialization_utc.slice(5, 7)),
      event_heavy: item.heavy_cells > 0,
      event_very_heavy: item.very_heavy_cells > 0,
      pseudo_regime_class: REGIME_CLASS_ORDER[regimeIndex] ?? null,
      // The static bundle doesn't carry the explicit eligibility booleans;
      // best-effort approximation from what it does carry, only ever used
      // while the live API is unreachable.
      deterministic_source_eligible: item.models.length > 0,
      probability_source_eligible: item.has_probabilities,
      regime_source_eligible: true,
      ensemble_source_eligible: item.has_ensemble,
      full_5_member_rainfall_qc_pass: item.has_ensemble,
      m1_minus_raw_rmse_mm: metrics?.M1_minus_raw_rmse_mm ?? null,
      selected_model_improved_vs_raw: metrics ? metrics.M1_minus_raw_rmse_mm < 0 : null,
    };
  });
}

export async function loadOperationalCaseList(year: OperationalYear): Promise<DataSourceResult<CaseListItem[]>> {
  return withStaticFallback(() => fetchLiveCaseList(year), () => fetchStaticCaseList(year));
}
