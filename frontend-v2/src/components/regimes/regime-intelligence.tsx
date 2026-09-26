"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DataSourceIndicator, ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { loadOperationalCaseList, REGIME_CLASS_ORDER, type RegimeClass } from "@/lib/operational-case-list";
import { getOperationalDeterministicMetrics, getOperationalRegime, getOperationalRegimeSummary, type OperationalYear } from "@/lib/api/operational";
import { withStaticFallback } from "@/lib/data-source";

const REGIME_LABEL: Record<RegimeClass, string> = {
  ACTIVE_MONSOON: "Active Monsoon", BREAK_WEAK_MONSOON: "Break / Weak Monsoon", LOW_DEPRESSION_INFLUENCED: "Low / Depression Influenced",
};
const PREDICTION_ROLE_NOTE: Record<string, string> = {
  OUT_OF_FOLD: "2023 probability comes from the out-of-fold cross-fit pathway.",
  PROSPECTIVE_VALIDATION: "2024 probability is a frozen prospective-validation prediction from the 2023-trained classifier.",
  FINAL_TEST_PREDICTION: "This classifier reproduces a deterministic forecast-only pseudo-label methodology; probabilities are not independent observations of weather regimes.",
};

// Phase 5A.2C: live-API-primary for per-case regime probability, the
// aggregate distribution, and (2025 only) the regime-conditioned RMSE table.
export function RegimeIntelligence({ initialYear }: { initialYear: number }) {
  const [year, setYear] = useState(initialYear);
  const [caseId, setCaseId] = useState("");
  const caseListResult = useQuery({
    queryKey: ["operational-case-list", year],
    queryFn: () => loadOperationalCaseList(year as OperationalYear),
    staleTime: 60_000,
  });
  const cases = useMemo(
    () => (caseListResult.data?.data ?? []).filter((item) => item.regime_source_eligible),
    [caseListResult.data],
  );
  const selectedCase = cases.find((item) => item.case_id === caseId) ?? cases[0];
  const regimeResult = useQuery({
    queryKey: ["operational-regime", year, selectedCase?.case_id],
    queryFn: () => withStaticFallback(() => getOperationalRegime(year as OperationalYear, selectedCase!.case_id), null),
    enabled: Boolean(selectedCase),
  });
  const summaryResult = useQuery({
    queryKey: ["operational-regime-summary", year],
    queryFn: () => withStaticFallback(() => getOperationalRegimeSummary(year as OperationalYear), null),
  });
  const deterministicResult = useQuery({
    queryKey: ["operational-deterministic", 2025],
    queryFn: () => withStaticFallback(() => getOperationalDeterministicMetrics(2025 as OperationalYear), null),
    enabled: year === 2025,
  });

  if (caseListResult.isPending) return <div className="page-content"><LoadingState /></div>;
  if (caseListResult.isError || !caseListResult.data || caseListResult.data.mode === "UNAVAILABLE") {
    return <div className="page-content"><ErrorState message={caseListResult.data?.message ?? "Frozen pseudo-regime catalogue unavailable."} /></div>;
  }
  if (caseListResult.data.mode === "INTEGRITY_FAILURE") {
    return <div className="page-content"><ErrorState message={`Scientific artifact integrity check failed: ${caseListResult.data.message}. This is a hard failure and is not masked by cached data.`} /></div>;
  }

  const regime = regimeResult.data?.data;
  const summary = summaryResult.data?.data;
  const distribution = summary?.distribution as
    | { paired_case_counts?: Record<string, number>; predicted_class_counts?: Record<string, number>; case_count?: number }
    | undefined;
  const pairedCounts = distribution?.paired_case_counts ?? distribution?.predicted_class_counts;
  const pairedTotal = pairedCounts ? Object.values(pairedCounts).reduce((sum, v) => sum + v, 0) : 0;
  const det = deterministicResult.data?.data?.metrics as Record<string, { continuous: { rmse_mm: number } }> | undefined;

  return <div className="page-content"><PageHeading title="Regime Intelligence" subtitle="Forecast-only pseudo-regime classifier output · not observed meteorological truth" action={<span style={{ display: "flex", gap: 8, alignItems: "center" }}>{regimeResult.data ? <DataSourceIndicator mode={regimeResult.data.mode} /> : null}<PrototypeNote /></span>} />
    <div className="phase5-context-strip"><strong>{year} {year === 2023 ? "CROSS-FIT / OOF" : year === 2024 ? "VALIDATION" : "FINAL TEST COMPLETED"}</strong><span>Three mutually exclusive pseudo-label classes</span><span>Forecast-time atmosphere only</span></div>
    <div className="phase5-controls"><label>Year<select value={year} onChange={(event) => { setYear(Number(event.target.value)); setCaseId(""); }}><option value={2023}>2023 cross-fit</option><option value={2024}>2024 validation</option><option value={2025}>2025 final</option></select></label><label>Historical case<select value={selectedCase?.case_id ?? ""} onChange={(event) => setCaseId(event.target.value)}>{cases.map((item) => <option value={item.case_id} key={item.case_id}>{item.initialization_utc.slice(0, 10)} · {item.lead_label}</option>)}</select></label></div>
    <div className="phase5-regime-layout"><section className="phase5-analysis-block"><h2>Selected case · classifier probabilities</h2>
      {regimeResult.isPending ? <LoadingState /> : !regime ? <ErrorState message="Regime probabilities are unavailable for the selected case." /> : REGIME_CLASS_ORDER.map((name) => <div className="phase5-regime-line" key={name}><span>{REGIME_LABEL[name]}</span><div aria-label={`${REGIME_LABEL[name]}: ${(100 * regime.probabilities[name]).toFixed(1)} percent`}><i style={{ width: `${100 * regime.probabilities[name]}%` }} /></div><strong>{(100 * regime.probabilities[name]).toFixed(1)}%</strong></div>)}
      <p className="phase5-caveat">{regime ? PREDICTION_ROLE_NOTE[regime.prediction_role] : PREDICTION_ROLE_NOTE.FINAL_TEST_PREDICTION}</p>
      {selectedCase ? <Link className="text-link" href={`/forecast?experiment=operational&year=${year}&case=${selectedCase.case_id}`}>Open this forecast case →</Link> : null}
    </section><section className="phase5-analysis-block"><h2>Forecast-to-routing pathway</h2><ol className="phase5-pipeline"><li>Frozen atmospheric forecast fields</li><li>Forecast-only diagnostics and pseudo-label rules</li><li>Three-class classifier probabilities</li><li>M3 hard expert routing / M4 soft expert blending</li></ol><p>No IMD observation enters the forecast-time regime classifier.</p></section></div>
    {pairedCounts ? <section className="phase5-analysis-block"><h2>{year} paired-case distribution</h2>{REGIME_CLASS_ORDER.map((name) => <div className="phase5-regime-line" key={name}><span>{REGIME_LABEL[name]}</span><div><i style={{ width: `${pairedTotal ? 100 * (pairedCounts[name] ?? 0) / pairedTotal : 0}%` }} /></div><strong>{pairedCounts[name] ?? 0} / {pairedTotal}</strong></div>)}
      {year === 2025 ? <p className="phase5-caveat small-label">Per-case attribution for 2025 is validated by reproducing both the full-375 classifier counts and this 232-case paired count from frozen eligibility ordering, not an explicit dedicated case-ID array — see Provenance for details.</p> : null}
    </section> : null}
    {year === 2025 ? <section className="phase5-analysis-block"><h2>2025 deterministic model consequence</h2>{deterministicResult.isPending ? <LoadingState /> : !det ? <ErrorState message="Deterministic metrics are unavailable." /> : <div className="phase5-metric-strip"><span><small>M2 Global</small><strong>{det.M2.continuous.rmse_mm.toFixed(4)} mm</strong></span><span><small>M3 Hard</small><strong>{det.M3.continuous.rmse_mm.toFixed(4)} mm</strong></span><span><small>M4 Soft</small><strong>{det.M4.continuous.rmse_mm.toFixed(4)} mm</strong></span></div>}<p className="phase5-caveat">Soft routing beat hard routing overall. Neither regime-aware model beat global M2 overall. M1 Ridge remains the preselected primary final-test model.</p></section> : null}
  </div>;
}
