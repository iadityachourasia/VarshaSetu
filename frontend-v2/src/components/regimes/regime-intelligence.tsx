"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { getOperationalIndex } from "@/science/frozen/operational";
import { final2025, regimeNames } from "@/science/frozen/results";

export function RegimeIntelligence({ initialYear }: { initialYear: number }) {
  const [year, setYear] = useState(initialYear);
  const [caseId, setCaseId] = useState("");
  const index = useQuery({ queryKey: ["operational-index"], queryFn: getOperationalIndex, staleTime: Infinity });
  if (index.isPending) return <div className="page-content"><LoadingState /></div>;
  if (index.isError) return <div className="page-content"><ErrorState message="Frozen pseudo-regime catalogue unavailable." /></div>;
  const cases = index.data.cases.filter((item) => item.year === year);
  const selected = cases.find((item) => item.case_id === caseId) ?? cases[0];
  const counts = year === 2025 ? Object.values(final2025.regime.paired_case_counts) : null;
  return <div className="page-content"><PageHeading title="Regime Intelligence" subtitle="Forecast-only pseudo-regime classifier output · not observed meteorological truth" action={<PrototypeNote />} />
    <div className="phase5-context-strip"><strong>{year} {year === 2023 ? "CROSS-FIT / OOF" : year === 2024 ? "VALIDATION" : "FINAL TEST COMPLETED"}</strong><span>Three mutually exclusive pseudo-label classes</span><span>Forecast-time atmosphere only</span></div>
    <div className="phase5-controls"><label>Year<select value={year} onChange={(event) => { setYear(Number(event.target.value)); setCaseId(""); }}><option value={2023}>2023 cross-fit</option><option value={2024}>2024 validation</option><option value={2025}>2025 final</option></select></label><label>Historical case<select value={selected?.case_id ?? ""} onChange={(event) => setCaseId(event.target.value)}>{cases.map((item) => <option value={item.case_id} key={item.case_id}>{item.initialization_utc.slice(0, 10)} · Day {item.lead_hours / 24}</option>)}</select></label></div>
    <div className="phase5-regime-layout"><section className="phase5-analysis-block"><h2>Selected case · classifier probabilities</h2>{selected ? regimeNames.map((name, position) => <div className="phase5-regime-line" key={name}><span>{name}</span><div aria-label={`${name}: ${(100 * selected.regime_probabilities[position]).toFixed(1)} percent`}><i style={{ width: `${100 * selected.regime_probabilities[position]}%` }} /></div><strong>{(100 * selected.regime_probabilities[position]).toFixed(1)}%</strong></div>) : null}<p className="phase5-caveat">{year === 2023 ? "2023 probability comes from the out-of-fold cross-fit pathway." : "This classifier reproduces a deterministic forecast-only pseudo-label methodology; probabilities are not independent observations of weather regimes."}</p>{selected ? <Link className="text-link" href={`/forecast?experiment=operational&year=${year}&case=${selected.case_id}`}>Open this forecast case →</Link> : null}</section><section className="phase5-analysis-block"><h2>Forecast-to-routing pathway</h2><ol className="phase5-pipeline"><li>Frozen atmospheric forecast fields</li><li>Forecast-only diagnostics and pseudo-label rules</li><li>Three-class classifier probabilities</li><li>M3 hard expert routing / M4 soft expert blending</li></ol><p>No IMD observation enters the forecast-time regime classifier.</p></section></div>
    {counts ? <section className="phase5-analysis-block"><h2>2025 paired-case distribution</h2>{regimeNames.map((name, position) => <div className="phase5-regime-line" key={name}><span>{name}</span><div><i style={{ width: `${100 * counts[position] / 232}%` }} /></div><strong>{counts[position]} / 232</strong></div>)}</section> : null}
    <section className="phase5-analysis-block"><h2>2025 deterministic model consequence</h2><div className="phase5-metric-strip"><span><small>M2 Global</small><strong>{final2025.deterministic.M2.continuous.rmse_mm.toFixed(4)} mm</strong></span><span><small>M3 Hard</small><strong>{final2025.deterministic.M3.continuous.rmse_mm.toFixed(4)} mm</strong></span><span><small>M4 Soft</small><strong>{final2025.deterministic.M4.continuous.rmse_mm.toFixed(4)} mm</strong></span></div><p className="phase5-caveat">Soft routing beat hard routing overall. Neither regime-aware model beat global M2 overall. M1 Ridge remains the preselected primary final-test model.</p></section>
  </div>;
}
