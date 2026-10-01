"use client";

import { useState } from "react";
import { RegimeEvidencePanel } from "@/components/regimes/regime-evidence-panel";

// Track A (GEFSv12 reforecast) regime-aware verification. Independent of the server-side Track A fetches on
// this page: the evidence is read from the hash-verified evidence API, so it stays available on its own.
export function TrackARegimeVerification() {
  const [year, setYear] = useState<2018 | 2019>(2019);
  return <div className="phase5-analysis-block">
    <div className="phase5-controls"><label>Population<select value={year} onChange={(event) => setYear(Number(event.target.value) as 2018 | 2019)}><option value={2019}>2019 completed final test</option><option value={2018}>2018 validation year</option></select></label></div>
    <RegimeEvidencePanel track="A" year={year} />
  </div>;
}
