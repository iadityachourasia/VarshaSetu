import type { CaseSummary } from "@/lib/api/science";

// Official Phase 2C catalogue entry; this is a presentation default, not a scientific result.
export const PRIMARY_DEMO_CASE_ID = "20190802T000000Z_day3_24h";

export function defaultDemoCase(cases: CaseSummary[], demos: CaseSummary[]): string | undefined {
  const official = demos.find((item) => item.case_id === PRIMARY_DEMO_CASE_ID);
  return official?.case_id ?? demos[0]?.case_id ?? cases[0]?.case_id;
}

// Phase 5B: the Track-B (2025) equivalents. Selected for complete data
// availability (full model ladder, ensemble, probability, regime,
// atmosphere) and a near-neutral case-level M1-minus-Raw delta, explicitly
// not because either is the best-performing case -- see
// docs/presentation/OFFICIAL_DEMO_CASES.md for the full selection record.
export const OFFICIAL_OPERATIONAL_CASE_ID = "20250714_day2_24h";
export const BACKUP_OPERATIONAL_CASE_ID = "20250903_day2_24h";
export const OFFICIAL_OPERATIONAL_YEAR = 2025;
export const OFFICIAL_OPERATIONAL_LEAD_HOURS = 48;
