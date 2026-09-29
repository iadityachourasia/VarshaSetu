import { RegimeIntelligence } from "@/components/regimes/regime-intelligence";
import { RegimeWorkInProgress } from "@/components/regimes/regime-work-in-progress";

export default async function RegimesPage({ searchParams }: { searchParams: Promise<{ experiment?: string; year?: string }> }) {
  const query = await searchParams;
  if (query.experiment !== "operational") return <RegimeWorkInProgress />;
  return <RegimeIntelligence initialYear={[2023, 2024, 2025].includes(Number(query.year)) ? Number(query.year) : 2025} />;
}
