"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { getScience, modelComparisonSchema } from "@/lib/api/science";
import { buildStoryFacts, count, mm, rmseChange, signedScore, type StoryFacts } from "@/lib/story-facts";
import { final2025 } from "@/science/frozen/results";
import staticQuality from "../../../public/science/operational-v1/quality.json";

// Phase 5B, sections 12-13: audited against the official 12-scene sequence
// (Problem / Two tracks / Forecast case / Correction vs observation /
// Synoptic context / Pseudo-regime architecture / Extreme probability /
// 2019 benchmark / 2025 final test / Extreme-skill limitation / Data
// quality / Reproducibility) and trimmed to one message, one visual, one
// takeaway per scene, targeting 60-90s at a brisk narrated pace. The prior
// (Phase 5A.3) ordering put the extreme-skill limitation and extreme-
// probability scenes in a different order and included a 13th "Uncertainty"
// (ensemble) scene not in the official sequence -- reordered and dropped
// here, not because that content was wrong, but to match the sequence this
// phase specifies. Every number is one already verified and displayed
// elsewhere in this app. No scientific number is typed in this file: every
// figure is derived in lib/story-facts.ts from the live hash-verified API (2019)
// and the generated frozen presentation bundle (2025, data quality), and a scene
// whose source is unavailable says so instead of showing a number. The product
// remains fully usable without ever opening this.
type Scene = { title: string; body: ReactNode };

const UNAVAILABLE = <p className="phase5-caveat">This figure comes from the verified API, which is not reachable right now, so no number is shown.</p>;

function buildScenes(facts: StoryFacts): Scene[] {
  return [
  { title: "The Problem", body: <p>Raw NWP precipitation forecasts can contain systematic errors, especially in complex monsoon conditions. VarshaSetu studies whether regime-aware, forecast-time post-processing can reduce that error without inventing new observations.</p> },
  { title: "Two Experiment Tracks", body: <>
    <div className="story-track-pair">
      <div><strong>Track A</strong><span>2017 → 2018 → 2019</span><small>NOAA GEFSv12 reforecast</small></div>
      <div><strong>Track B</strong><span>2023 → 2024 → 2025</span><small>Historical operational GEFS</small></div>
    </div>
    <p className="phase5-caveat">Different GEFS lineages and evaluation populations. Results are not pooled.</p>
  </> },
  { title: "Forecast Case", body: <>
    <p>Every displayed case is real and historical -- a specific initialization, lead time, and paired IMD observation date, not a synthetic example.</p>
    <p className="micro-note">Labeled a <strong>historical case</strong> throughout, never a &ldquo;representative result.&rdquo;</p>
    <Link className="text-link" href="/forecast">Open Forecast Explorer →</Link>
  </> },
  { title: "Correction vs. Observation", body: <p>Raw GEFS, the corrected output, and the paired IMD observation render side by side on the same grid -- the same units, the same domain, one point inspector for all three.</p> },
  { title: "Synoptic Context", body: <>
    <p>Rainfall corrections sit inside atmospheric context: 850-hPa wind, 700-hPa moisture, 500-hPa geopotential height, mean sea-level pressure, and precipitable water are all frozen forecast-time fields, viewable alongside the rainfall grid.</p>
    <p className="phase5-caveat">This demonstrates the model sees synoptic state -- it is not a causal proof that any one atmospheric feature drove any one correction.</p>
  </> },
  { title: "Pseudo-Regime Architecture", body: <>
    <ol className="phase5-pipeline"><li>Frozen forecast-time atmosphere</li><li>Forecast-only pseudo-regime probabilities</li><li>Hard routing (M3) / soft mixture (M4)</li></ol>
    <p className="phase5-caveat">These are <strong>forecast-only pseudo-regimes</strong>, not independently observed monsoon regime truth.</p>
  </> },
  { title: "Extreme Probability", body: <>
    {facts.probability2025 ? <div className="story-stat-row"><span><strong>{signedScore(facts.probability2025.heavyBss)}</strong><small>Heavy BSS</small></span><span><strong>{signedScore(facts.probability2025.veryHeavyBss)}</strong><small>Very-heavy BSS</small></span></div> : UNAVAILABLE}
    <p className="phase5-caveat">Brier Skill Score against the frozen 2023 event-prevalence reference, shown with its sign. Very-heavy false-alarm ratio nonetheless remained high.</p>
  </> },
  { title: "2019 Benchmark", body: <>
    {facts.benchmark2019 ? <div className="story-stat-row"><span><strong>{mm(facts.benchmark2019.rawRmse)}</strong><small>Raw GEFS RMSE</small></span><span><strong>{mm(facts.benchmark2019.correctedRmse)}</strong><small>{facts.benchmark2019.correctedLabel} RMSE</small></span><span><strong>{rmseChange(facts.benchmark2019.reductionPercent)}</strong><small>RMSE change vs Raw</small></span></div> : UNAVAILABLE}
    <p className="micro-note">{facts.benchmark2019 ? `${count(facts.benchmark2019.cases)} completed held-out cases` : "Completed held-out cases"} · NOAA GEFSv12 reforecast + IMD.</p>
  </> },
  { title: "2025 Final Test", body: <>
    {facts.final2025 ? <div className="story-stat-row"><span><strong>{mm(facts.final2025.rawRmse)}</strong><small>Raw GEFS RMSE</small></span><span><strong>{mm(facts.final2025.correctedRmse)}</strong><small>{facts.final2025.correctedLabel} RMSE</small></span><span><strong>{rmseChange(facts.final2025.reductionPercent)}</strong><small>RMSE change vs Raw</small></span></div> : UNAVAILABLE}
    <p className="micro-note">{facts.final2025 ? `${count(facts.final2025.cases)} cases` : "Completed cases"}, one-time historical final test. <strong>M1 was selected before the 2025 holdout was opened</strong> -- not revised by anything observed afterward.</p>
  </> },
  { title: "Extreme-Skill Limitation", body: <p className="story-headline">Raw GEFS retained better extreme-rain spatial FSS than the RMSE-selected model, at every tested neighborhood size. Lower overall RMSE did not translate into better extreme-rain spatial skill -- stated here deliberately, not hidden in a footnote.</p> },
  { title: "Data Quality", body: <>
    {facts.quality ? <div className="story-stat-row"><span><strong>{count(facts.quality.scheduled)}</strong><small>Scheduled</small></span><span><strong>{count(facts.quality.c00Eligible)}</strong><small>c00 QC-eligible</small></span><span><strong>{count(facts.quality.fiveMemberEligible)}</strong><small>Five-member QC-eligible</small></span></div> : UNAVAILABLE}
    <p className="micro-note">Every scheduled message was acquired; the eligible counts reflect canonical scientific QC attrition, not missing data.</p>
  </> },
  { title: "Reproducibility", body: <>
    <ul className="phase5-limitations"><li>Frozen models -- no retraining after any test was opened</li><li>Hash-verified artifacts at every stage</li><li>A one-time final test, consumed once</li><li>Independent recalculation of the headline claims</li></ul>
    <p className="story-closing"><strong>VarshaSetu</strong><br />Research prototype for scientifically transparent monsoon forecast post-processing.</p>
  </> },
  ];
}

// The number of scenes does not depend on the data; keyboard handling uses this constant so the effect never re-subscribes.
const SCENE_COUNT = buildScenes({ benchmark2019: null, final2025: null, probability2025: null, quality: null }).length;

/** The caller mounts this only while open (see PresentButton in
 * app-shell.tsx), so each open starts fresh at scene 0 -- no reset-on-
 * prop-change effect needed. */
export function StoryMode({ onClose }: { onClose: () => void }) {
  const [index, setIndex] = useState(0);
  const dialogRef = useRef<HTMLDivElement>(null);
  // 2019 comes from the live verified API; 2025 and data quality come from the generated frozen presentation bundle.
  const comparison = useQuery({ queryKey: ["story-model-comparison"], queryFn: () => getScience("/model-comparison", modelComparisonSchema), staleTime: 5 * 60_000, retry: 1 });
  const SCENES = useMemo(() => buildScenes(buildStoryFacts({ comparison: comparison.data ?? null, final2025, quality: staticQuality })), [comparison.data]);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const shell = document.querySelector<HTMLElement>(".app-shell");
    const previousInert = shell?.inert ?? false;
    document.body.style.overflow = "hidden";
    if (shell) shell.inert = true;
    dialogRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") { event.preventDefault(); onClose(); return; }
      if (event.key === "Tab" && dialogRef.current) {
        const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')];
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
        return;
      }
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, select, textarea, [contenteditable]")) return;
      if (event.key === " " && target?.closest("a, button")) return;
      if (event.key === "ArrowRight" || event.key === " ") { event.preventDefault(); setIndex((current) => Math.min(current + 1, SCENE_COUNT - 1)); }
      else if (event.key === "ArrowLeft") { event.preventDefault(); setIndex((current) => Math.max(current - 1, 0)); }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      if (shell) shell.inert = previousInert;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);

  const scene = SCENES[index];
  return <div className="story-overlay" role="dialog" aria-modal="true" aria-label="Present VarshaSetu" ref={dialogRef} tabIndex={-1} onClickCapture={(event) => { if ((event.target as HTMLElement).closest("a[href]")) onClose(); }}>
    <div className="story-topbar">
      <div className="story-identity"><span className="brand-symbol" aria-hidden="true" /><strong>VarshaSetu</strong></div>
      <span className="story-progress" aria-live="polite">Scene {index + 1} of {SCENES.length}</span>
      <div className="story-progress-bar" aria-hidden="true"><div style={{ width: `${(100 * (index + 1)) / SCENES.length}%` }} /></div>
      <button type="button" className="story-exit" onClick={onClose}>Exit</button>
    </div>
    <div className="story-scene">
      <span className="story-scene-number">{String(index + 1).padStart(2, "0")}</span>
      <h2>{scene.title}</h2>
      <div className="story-scene-body">{scene.body}</div>
    </div>
    <div className="story-navbar">
      <button type="button" onClick={() => setIndex((current) => Math.max(current - 1, 0))} disabled={index === 0}>← Back</button>
      <div className="story-dots" aria-hidden="true">{SCENES.map((item, dotIndex) => <span key={item.title} className={dotIndex === index ? "active" : ""} />)}</div>
      {index === SCENES.length - 1 ? <button type="button" onClick={onClose}>Exit</button> : <button type="button" onClick={() => setIndex((current) => Math.min(current + 1, SCENES.length - 1))}>Next →</button>}
    </div>
  </div>;
}
