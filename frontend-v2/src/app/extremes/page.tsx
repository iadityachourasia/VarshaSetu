import { ExtremesWorkspace } from "@/components/extremes/extremes-workspace";
import { OperationalExtremes } from "@/components/extremes/operational-extremes";
import { ErrorState } from "@/components/science/common";
import { casesSchema, demoCasesSchema, getScience, verificationSchema } from "@/lib/api/science";
import { defaultDemoCase } from "@/lib/demo";

export default async function ExtremesPage({ searchParams }: { searchParams: Promise<{ case?: string; experiment?: string; year?: string }> }) {
  const query = await searchParams;
  if (query.experiment === "operational") {
    const initialYear = [2023, 2024, 2025].includes(Number(query.year)) ? (Number(query.year) as 2023 | 2024 | 2025) : 2025;
    return <OperationalExtremes initialCase={query.case} initialYear={initialYear} />;
  }
  if (query.year && query.year !== "2019") return <div className="page-content"><ErrorState message="Interactive reforecast probability maps are available for the frozen 2019 final test only." /></div>;
  const result = await Promise.all([
      getScience("/cases", casesSchema, true), getScience("/demo-cases", demoCasesSchema, true),
      getScience("/verification", verificationSchema, true),
    ]).catch(() => null);
  if (!result) return <div className="page-content"><ErrorState /></div>;
  const [all, demos, verification] = result;
  const selected = all.cases.some((item) => item.case_id === query.case) ? query.case! : defaultDemoCase(all.cases, demos.cases);
  if (!selected) return <ErrorState message="No verified historical cases are available." />;
  return <ExtremesWorkspace cases={all.cases} demos={demos.cases} initialCase={selected} verification={verification} />;
}
