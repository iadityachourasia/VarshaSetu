import type { CaseSummary } from "@/lib/api/science";

// Official Phase 2C catalogue entry; this is a presentation default, not a scientific result.
export const PRIMARY_DEMO_CASE_ID = "20190802T000000Z_day3_24h";

export function defaultDemoCase(cases: CaseSummary[], demos: CaseSummary[]): string | undefined {
  const official = demos.find((item) => item.case_id === PRIMARY_DEMO_CASE_ID);
  return official?.case_id ?? demos[0]?.case_id ?? cases[0]?.case_id;
}
