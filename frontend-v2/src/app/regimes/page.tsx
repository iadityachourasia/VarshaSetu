import { RegimeIntelligence } from "@/components/regimes/regime-intelligence";
import { RegimeTrackA } from "@/components/regimes/regime-track-a";

export default async function RegimesPage({ searchParams }: { searchParams: Promise<{ experiment?: string; year?: string }> }) {
  const query = await searchParams;
  const year = Number(query.year);
  if (query.experiment === "operational") return <RegimeIntelligence initialYear={[2023, 2024, 2025].includes(year) ? year : 2025} />;
  return <RegimeTrackA initialYear={[2017, 2018, 2019].includes(year) ? year : 2019} />;
}
