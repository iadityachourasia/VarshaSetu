import { DistrictWorkspace } from "@/components/districts/district-workspace";
import { OperationalDistrictWorkspace } from "@/components/districts/operational-districts";
import { ErrorState } from "@/components/science/common";
import { casesSchema, demoCasesSchema, geometrySchema, getScience } from "@/lib/api/science";
import { operationalYearSchema } from "@/lib/api/operational";
import { defaultDemoCase } from "@/lib/demo";

export default async function DistrictsPage({ searchParams }: { searchParams: Promise<{ case?: string; experiment?: string; year?: string }> }) {
  const query = await searchParams;
  if (query.experiment === "operational") {
    const year = operationalYearSchema.safeParse(Number(query.year));
    return <OperationalDistrictWorkspace initialYear={year.success ? year.data : 2025} initialCase={query.case} />;
  }
  const result = await Promise.all([
      getScience("/cases", casesSchema, true), getScience("/demo-cases", demoCasesSchema, true),
      getScience("/geometry/districts", geometrySchema, true),
    ]).catch(() => null);
  if (!result) return <div className="page-content"><ErrorState /></div>;
  const [all, demos, geometry] = result;
  const selected = all.cases.some((item) => item.case_id === query.case) ? query.case! : defaultDemoCase(all.cases, demos.cases);
  if (!selected) return <ErrorState message="No verified historical cases are available." />;
  return <DistrictWorkspace cases={all.cases} demos={demos.cases} initialCase={selected} geometry={geometry} />;
}
