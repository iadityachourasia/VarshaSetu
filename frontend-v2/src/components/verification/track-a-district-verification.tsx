"use client";

import { useState } from "react";
import { DistrictVerificationPanel } from "@/components/verification/district-verification-panel";

// Track A (GEFSv12 reforecast) district-level verification, protocol A v1 (docs/135). Read from the hash-verified evidence API, so it stays
// available independently of the server-side Track A fetches on this page. The 2019 year is a consumed holdout and is labelled post-hoc by the API.
export function TrackADistrictVerification() {
  const [year, setYear] = useState<2018 | 2019>(2019);
  return <div className="phase5-analysis-block" data-testid="track-a-district-verification">
    <div className="phase5-controls"><label>Population<select value={year} onChange={(event) => setYear(Number(event.target.value) as 2018 | 2019)}><option value={2019}>2019 completed final test (post-hoc)</option><option value={2018}>2018 validation year (development)</option></select></label></div>
    <DistrictVerificationPanel year={year} />
  </div>;
}
