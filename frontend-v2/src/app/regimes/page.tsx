import { RegimeIntelligence } from "@/components/regimes/regime-intelligence";
import { RegimeTrackA } from "@/components/regimes/regime-track-a";
import { IndependentRegimeValidation } from "@/components/regimes/independent-regime-validation";
import { CoastalRegimePanel } from "@/components/regimes/coastal-regime-panel";
import { WdIndicatorPanel } from "@/components/regimes/wd-indicator-panel";
import { PageToc } from "@/components/science/common";
import { RegimeTaskValidation } from "@/components/regimes/regime-task-validation";

export default async function RegimesPage({ searchParams }: { searchParams: Promise<{ experiment?: string; year?: string }> }) {
  const query = await searchParams;
  const year = Number(query.year);
  const toc = <div className="page-content page-content-toc"><PageToc items={[{ id: "r-classifier", label: "Classifier and correction" }, { id: "r-detection", label: "Sealed-year detection" }, { id: "r-coastal", label: "Coastal / orographic" }, { id: "r-wd", label: "Western disturbance" }, { id: "r-independent", label: "Independent check" }]} /></div>;
  const validation = <div className="page-content"><div id="r-detection"><RegimeTaskValidation /></div><div id="r-coastal"><CoastalRegimePanel /></div><div id="r-wd"><WdIndicatorPanel /></div><div id="r-independent"><IndependentRegimeValidation /></div></div>;
  if (query.experiment === "operational") return <>{toc}<div id="r-classifier"><RegimeIntelligence initialYear={[2023, 2024, 2025].includes(year) ? year : 2025} /></div>{validation}</>;
  return <>{toc}<div id="r-classifier"><RegimeTrackA initialYear={[2017, 2018, 2019].includes(year) ? year : 2019} /></div>{validation}</>;
}
