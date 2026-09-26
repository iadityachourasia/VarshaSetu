import Link from "next/link";
import { OperationalCasebook } from "@/components/casebook/operational-casebook";
import { ErrorState, PageHeading } from "@/components/science/common";
import { casesSchema, getScience } from "@/lib/api/science";

export default async function CasebookPage({ searchParams }: { searchParams: Promise<{ experiment?: string; year?: string; case?: string }> }) {
  const query = await searchParams;
  if (query.experiment === "operational") return <OperationalCasebook initialYear={[2023, 2024, 2025].includes(Number(query.year)) ? Number(query.year) : 2025} />;
  if (query.year && query.year !== "2019") return <div className="page-content"><ErrorState message="No independent reforecast casebook is published for this training or validation year. The 2019 final historical test has all eligible case records." /></div>;
  const result = await getScience("/cases", casesSchema, true).catch(() => null);
  if (!result) return <div className="page-content"><ErrorState /></div>;
  return <div className="page-content"><PageHeading title="Event Casebook" subtitle="2019 GEFSv12 reforecast · all 255 control-model-eligible cases" /><p className="phase5-caveat">Cases are examples for inspection, not a selected proof of overall superiority. Open a case to see the frozen Raw / M2 / IMD comparison.</p><div className="phase5-case-list">{result.cases.map((item) => <Link key={item.case_id} href={`/forecast?experiment=reforecast&year=2019&case=${encodeURIComponent(item.case_id)}`} className="phase5-case-row"><strong>{item.initialization_utc.slice(0, 10)} · Day {item.lead_hours / 24}</strong><span>{item.observed_heavy_cells} Heavy · {item.observed_very_heavy_cells} Very Heavy observed cells</span><span>Raw {item.raw_rmse_mm.toFixed(2)} → M2 {item.corrected_rmse_mm.toFixed(2)} mm RMSE</span></Link>)}</div></div>;
}
