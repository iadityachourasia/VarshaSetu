import { redirect } from "next/navigation";
import { ForecastWorkspace } from "@/components/forecast/forecast-workspace";
import { OperationalForecastWorkspace } from "@/components/forecast/operational-workspace";
import { ErrorState } from "@/components/science/common";
import { casesSchema, demoCasesSchema, getScience } from "@/lib/api/science";
import { defaultDemoCase, OFFICIAL_OPERATIONAL_CASE_ID, OFFICIAL_OPERATIONAL_YEAR } from "@/lib/demo";

export default async function ForecastPage({ searchParams }: { searchParams: Promise<{ case?: string; experiment?: string; year?: string; demo?: string }> }) {
  const query = await searchParams;
  // Phase 5B: a safe presentation preset -- redirects to the exact same
  // real query params a presenter would type by hand, then falls through
  // to the ordinary live/static-fallback data loading below. Never
  // constructs a result object itself.
  if (query.demo === "official") redirect(`/forecast?experiment=operational&year=${OFFICIAL_OPERATIONAL_YEAR}&case=${OFFICIAL_OPERATIONAL_CASE_ID}`);
  if (query.experiment === "operational") {
    const year = [2023, 2024, 2025].includes(Number(query.year)) ? Number(query.year) : 2025;
    return <OperationalForecastWorkspace initialYear={year} initialCase={query.case} />;
  }
  if (query.year && query.year !== "2019") return <div className="page-content"><ErrorState message="Interactive reforecast maps are available for the frozen 2019 final test. 2017 and 2018 are training/validation context, not independent case maps in this presentation." /></div>;
  const result = await Promise.all([
      getScience("/cases", casesSchema, true), getScience("/demo-cases", demoCasesSchema, true),
    ]).catch(() => null);
  if (!result) return <div className="page-content"><ErrorState /></div>;
  const [all, demos] = result;
  const selected = all.cases.some((item) => item.case_id === query.case) ? query.case! : defaultDemoCase(all.cases, demos.cases);
  if (!selected) return <ErrorState message="No verified historical cases are available." />;
  return <ForecastWorkspace cases={all.cases} demos={demos.cases} initialCase={selected} />;
}
