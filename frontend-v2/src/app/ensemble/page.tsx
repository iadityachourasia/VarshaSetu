import { OperationalEnsemble } from "@/components/ensemble/operational-ensemble";
import { redirect } from "next/navigation";

export default async function EnsemblePage({ searchParams }: { searchParams: Promise<{ experiment?: string; year?: string; case?: string }> }) {
  const query = await searchParams;
  if (query.experiment !== "operational" || query.year !== "2025") redirect("/ensemble?experiment=operational&year=2025");
  return <OperationalEnsemble initialCase={query.case} />;
}
