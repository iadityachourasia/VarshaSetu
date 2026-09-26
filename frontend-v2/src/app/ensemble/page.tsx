import { OperationalEnsemble } from "@/components/ensemble/operational-ensemble";
import { ErrorState } from "@/components/science/common";

export default async function EnsemblePage({ searchParams }: { searchParams: Promise<{ experiment?: string; year?: string; case?: string }> }) {
  const query = await searchParams;
  if (query.experiment !== "operational" || query.year && query.year !== "2025") return <div className="page-content"><ErrorState message="The matched, frozen five-member versus calibrated-ML comparison is available for the 2025 operational-era final-test subset. Select Historical Operational GEFS · 2025." /></div>;
  return <OperationalEnsemble initialCase={query.case} />;
}
