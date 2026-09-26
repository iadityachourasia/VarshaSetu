import Link from "next/link";
import { DistrictWorkspace } from "@/components/districts/district-workspace";
import { ErrorState, PageHeading, PrototypeNote } from "@/components/science/common";
import { casesSchema, demoCasesSchema, geometrySchema, getScience } from "@/lib/api/science";
import { defaultDemoCase } from "@/lib/demo";

function OperationalDistrictsUnavailable({ year }: { year: number }) {
  return <div className="page-content">
    <PageHeading title="District Intelligence" subtitle="Historical operational GEFS · 2023-2025" action={<PrototypeNote />} />
    <div className="phase5-context-strip"><strong>Historical operational GEFS</strong><span>Year {year}</span></div>
    <div className="state-message" role="status">
      <strong>District aggregation is not part of the frozen operational-era presentation dataset</strong>
      <p>
        The 2023-2025 historical operational GEFS corpus was frozen without a district polygon-overlap
        aggregation step (unlike the 2019 GEFSv12 reforecast track, which has one). This page will not
        fabricate a district table from unaggregated grid cells.
      </p>
      <p className="phase5-caveat">
        To inspect this year&rsquo;s frozen grids and error evidence directly, use{" "}
        <Link href={`/forecast?experiment=operational&year=${year}`}>Forecast &amp; Atmosphere</Link>
        {" "}or{" "}
        <Link href={`/casebook?experiment=operational&year=${year}`}>the Extreme Event Casebook</Link>.
      </p>
    </div>
  </div>;
}

export default async function DistrictsPage({ searchParams }: { searchParams: Promise<{ case?: string; experiment?: string; year?: string }> }) {
  const query = await searchParams;
  if (query.experiment === "operational") {
    return <OperationalDistrictsUnavailable year={[2023, 2024, 2025].includes(Number(query.year)) ? Number(query.year) : 2025} />;
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
