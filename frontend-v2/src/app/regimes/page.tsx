import { RegimeIntelligence } from "@/components/regimes/regime-intelligence";
import { ErrorState } from "@/components/science/common";

export default async function RegimesPage({ searchParams }: { searchParams: Promise<{ experiment?: string; year?: string }> }) {
  const query = await searchParams;
  if (query.experiment !== "operational") return <div className="page-content"><ErrorState message="This operational-era pseudo-regime view is separate from the 2019 reforecast classifier. Select Historical Operational GEFS." /></div>;
  return <RegimeIntelligence initialYear={[2023, 2024, 2025].includes(Number(query.year)) ? Number(query.year) : 2025} />;
}
