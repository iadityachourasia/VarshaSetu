"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { ReactNode } from "react";

// Phase 5A.3, sections 39-53: a guided, full-screen judge presentation.
// Every number here is one already verified and displayed elsewhere in
// this app (Verification, Extreme Rain, Ensemble, Quality) -- Story Mode
// narrates existing frozen evidence, it does not compute or fetch anything
// new. The product remains fully usable without ever opening this.
type Scene = { title: string; body: ReactNode };

const SCENES: Scene[] = [
  { title: "The Problem", body: <p>Raw NWP precipitation forecasts can contain systematic errors, especially in complex monsoon conditions. VarshaSetu studies whether regime-aware, forecast-time post-processing can reduce that error without inventing new observations.</p> },
  { title: "Two Independent Experiments", body: <>
    <p>Two separate historical tracks, never pooled into one line:</p>
    <div className="story-track-pair">
      <div><strong>Track A</strong><span>2017 → 2018 → 2019</span><small>NOAA GEFSv12 reforecast</small></div>
      <div><strong>Track B</strong><span>2023 → 2024 → 2025</span><small>Historical operational GEFS</small></div>
    </div>
    <p className="phase5-caveat">Different GEFS lineages and evaluation populations. Results are not pooled.</p>
  </> },
  { title: "Forecast Correction", body: <>
    <p>Every displayed correction is a real historical case -- Raw GEFS, the corrected output, and the paired IMD observation, side by side on the same grid.</p>
    <p className="micro-note">Labeled a <strong>historical case</strong> throughout this product, never a &ldquo;representative result.&rdquo;</p>
    <Link className="text-link" href="/forecast">Open Forecast Explorer →</Link>
  </> },
  { title: "Synoptic Context", body: <>
    <p>Rainfall corrections sit inside atmospheric context: 850-hPa wind components, 700-hPa moisture, 500-hPa geopotential height, mean sea-level pressure, and precipitable water are all frozen forecast-time fields, viewable alongside the rainfall grid.</p>
    <p className="phase5-caveat">Atmospheric context demonstrates the model sees synoptic state -- it is not a causal proof that any one atmospheric feature drove any one correction.</p>
  </> },
  { title: "Regime-Aware Processing", body: <>
    <ol className="phase5-pipeline"><li>Frozen forecast-time atmosphere</li><li>Forecast-only pseudo-regime probabilities</li><li>Hard routing (M3) / soft mixture (M4)</li></ol>
    <p className="phase5-caveat">These are <strong>forecast-only pseudo-regimes</strong>, not independently observed monsoon regime truth.</p>
  </> },
  { title: "2019 Retrospective Benchmark", body: <>
    <div className="story-stat-row"><span><strong>19.77 mm</strong><small>Raw GEFS</small></span><span><strong>17.85 mm</strong><small>Global XGBoost</small></span><span><strong>−9.73%</strong><small>RMSE reduction</small></span></div>
    <p className="micro-note">255 completed held-out cases · NOAA GEFSv12 reforecast + IMD.</p>
  </> },
  { title: "2025 Final Test", body: <>
    <div className="story-stat-row"><span><strong>16.17 mm</strong><small>Raw GEFS</small></span><span><strong>15.57 mm</strong><small>Preselected M1</small></span><span><strong>−3.66%</strong><small>RMSE reduction</small></span></div>
    <p className="micro-note">232 cases · one-time historical final test.</p>
    <p className="phase5-caveat"><strong>M1 was selected before the 2025 holdout was opened.</strong> That governance decision is not revised by anything observed afterward.</p>
  </> },
  { title: "Scientific Transparency", body: <>
    <p className="story-headline">Raw GEFS retained better extreme-rain spatial FSS than the selected model, at every tested neighborhood size.</p>
    <p className="micro-note">Lower overall RMSE did not translate into better extreme-rain spatial skill. This is stated here deliberately, not hidden in a footnote.</p>
  </> },
  { title: "Extreme Rain Probability", body: <>
    <div className="story-stat-row"><span><strong>+0.0948</strong><small>Heavy BSS</small></span><span><strong>+0.0265</strong><small>Very-heavy BSS</small></span></div>
    <p className="phase5-caveat">Very-heavy false-alarm ratio remained high on the 2025 final test. Positive skill against a fixed reference is not the same as an operationally low false-alarm rate.</p>
  </> },
  { title: "Uncertainty", body: <>
    <p>The available five-member ensemble subset is compared against the calibrated ML probability on the exact same matched 75-case, 97,575-cell population.</p>
    <p className="micro-note">This comparison covers only that matched subset -- it is not a claim about the full 232-case final-test population.</p>
  </> },
  { title: "Data Integrity", body: <>
    <div className="story-stat-row"><span><strong>1,125</strong><small>Scheduled</small></span><span><strong>615</strong><small>c00 QC-eligible</small></span><span><strong>218</strong><small>Five-member QC-eligible</small></span></div>
    <p className="micro-note">Every scheduled message was acquired; the eligible counts reflect canonical scientific QC attrition, not missing data or a failed download.</p>
  </> },
  { title: "Reproducible Science", body: <>
    <ul className="phase5-limitations"><li>Frozen models -- no retraining after any test was opened</li><li>Hash-verified artifacts at every stage</li><li>A one-time final test, consumed once</li><li>Independent recalculation of the headline claims</li><li>An internal independent reproducibility audit</li></ul>
    <p className="story-closing"><strong>VarshaSetu</strong><br />Research prototype for scientifically transparent monsoon forecast post-processing.</p>
  </> },
];

/** The caller mounts this only while open (see PresentButton in
 * app-shell.tsx), so each open starts fresh at scene 0 -- no reset-on-
 * prop-change effect needed. */
export function StoryMode({ onClose }: { onClose: () => void }) {
  const [index, setIndex] = useState(0);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    dialogRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      else if (event.key === "ArrowRight" || event.key === " ") { event.preventDefault(); setIndex((current) => Math.min(current + 1, SCENES.length - 1)); }
      else if (event.key === "ArrowLeft") { event.preventDefault(); setIndex((current) => Math.max(current - 1, 0)); }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const scene = SCENES[index];
  return <div className="story-overlay" role="dialog" aria-modal="true" aria-label="Present VarshaSetu" ref={dialogRef} tabIndex={-1}>
    <div className="story-topbar">
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
