"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { RegimeBars } from "@/components/science/regime-bars";
import { RegimeEvidencePanel } from "@/components/regimes/regime-evidence-panel";
import { casesSchema, getScience } from "@/lib/api/science";
import { EVIDENCE_REGIMES } from "@/lib/api/evidence";
import { leadName, regimeName, utc } from "@/lib/format";

const YEARS = [2017, 2018, 2019] as const;
const ROLE: Record<number, string> = { 2017: "TRAINING YEAR", 2018: "VALIDATION YEAR", 2019: "FINAL TEST COMPLETED" };

// Track A (GEFSv12 reforecast 2017-2019): per-case forecast-only regime probabilities exist for 2019 only
// (the published case API); regime-stratified verification evidence exists for 2018 and 2019 (docs/108).
export function RegimeTrackA({ initialYear }: { initialYear: number }) {
  const [year, setYear] = useState<number>(initialYear);
  const [caseId, setCaseId] = useState("");
  const cases = useQuery({ queryKey: ["track-a-cases"], queryFn: () => getScience("/cases", casesSchema), staleTime: 5 * 60_000 });
  const list = useMemo(() => cases.data?.cases ?? [], [cases.data]);
  const selected = list.find((item) => item.case_id === caseId) ?? list.find((item) => item.observed_very_heavy_cells > 0) ?? list[0];
  const counts = useMemo(() => {
    const tally: Record<string, number> = Object.fromEntries(EVIDENCE_REGIMES.map((name) => [name, 0]));
    for (const item of list) tally[item.dominant_regime] = (tally[item.dominant_regime] ?? 0) + 1;
    return tally;
  }, [list]);

  return <div className="page-content"><PageHeading title="Regime Intelligence" subtitle="Forecast-only pseudo-regime classifier output · not observed meteorological truth" action={<PrototypeNote />} />
    <div className="phase5-context-strip"><strong>{year} · {ROLE[year]}</strong><span>GEFSv12 reforecast (Track A)</span><span>Three mutually exclusive pseudo-label classes</span><span>Coastal, orographic and western-disturbance regimes are not yet part of the classifier</span></div>
    <div className="phase5-controls"><label>Year<select value={year} onChange={(event) => setYear(Number(event.target.value))}>{YEARS.map((item) => <option key={item} value={item}>{item} · {ROLE[item].toLowerCase()}</option>)}</select></label></div>

    {year === 2019 ? (cases.isPending ? <LoadingState /> : cases.isError || !selected ? <ErrorState message="The 2019 case catalogue is unavailable." /> : <div className="phase5-regime-layout">
      <section className="phase5-analysis-block"><h2>Selected case · classifier probabilities</h2>
        <div className="phase5-controls"><label>Historical case<select value={selected.case_id} onChange={(event) => setCaseId(event.target.value)}>{list.map((item) => <option key={item.case_id} value={item.case_id}>{utc(item.initialization_utc).replace(" UTC", "")} · {leadName(item.lead_hours)}{item.observed_very_heavy_cells > 0 ? " · Very Heavy event" : item.observed_heavy_cells > 0 ? " · Heavy event" : ""}</option>)}</select></label></div>
        <RegimeBars probabilities={selected.regime_probabilities} dominant={selected.dominant_regime} />
        <p className="phase5-caveat">The classifier reproduces a deterministic forecast-only pseudo-label methodology; probabilities are not independent observations of weather regimes.</p>
        <Link className="text-link" href={`/forecast?experiment=reforecast&year=2019&case=${encodeURIComponent(selected.case_id)}`}>Open this forecast case →</Link>
      </section>
      <section className="phase5-analysis-block"><h2>2019 case distribution by dominant pseudo-regime</h2>
        {EVIDENCE_REGIMES.map((name) => <div className="phase5-regime-line" key={name}><span>{regimeName(name)}</span><div><i style={{ width: `${list.length ? (counts[name] / list.length) * 100 : 0}%` }} /></div><strong>{counts[name]} of {list.length}</strong></div>)}
        <p className="phase5-caveat">Counts are the published {list.length} control-model-eligible final-test cases, classified from forecast fields only.</p>
      </section>
    </div>) : <section className="phase5-analysis-block"><h2>Per-case regime probabilities</h2><p>{year === 2018 ? "Per-case forecast-only regime probabilities are published for the 2019 final-test cases only. The 2018 validation-year evidence below is aggregated by regime and lead." : "2017 is the classifier training year; models were fitted on it, so no case or verification view is published for it."}</p></section>}

    <section className="phase5-analysis-block"><h2>Forecast-to-routing pathway</h2><ol className="phase5-pipeline"><li>Frozen atmospheric forecast fields</li><li>Forecast-only diagnostics and pseudo-label rules</li><li>Three-class logistic classifier → regime probabilities</li><li>Hard routing (M3) or probability-weighted mixture (M4) of regime specialists</li><li>Corrected rainfall, then verification against IMD</li></ol>
      <p className="phase5-caveat">Classifier agreement with its own pseudo-labels is not meteorological accuracy. No independent expert validation exists yet.</p></section>

    <RegimeEvidencePanel track="A" year={year} />
  </div>;
}
