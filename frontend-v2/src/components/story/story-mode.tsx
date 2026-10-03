"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { getScience, modelComparisonSchema } from "@/lib/api/science";
import { getPsCoverage } from "@/lib/api/evidence";
import { SHOW_COMPLIANCE_PAGE } from "@/lib/features";
import { getR03Result, getR05Confirmation, getR05Result } from "@/lib/api/reforecast";
import { buildStoryFacts, count, mm, rmseChange, score3, signedScore, type ReforecastRound, type StoryFacts } from "@/lib/story-facts";
import { final2025 } from "@/science/frozen/results";
import staticQuality from "../../../public/science/operational-v1/quality.json";

// The presentation narrates the evidence in the order a reviewer asks for it: the problem, the forecast, the regimes, the skill, then the assurance.
// One message, one visual and one stated limitation per scene. No scientific number is typed in this file: every figure is derived in lib/story-facts.ts
// from the hash-verified API (2019 benchmark, requirement coverage, regime detection, reforecast study) or from the generated frozen presentation bundle
// (2025 test, data quality), and a scene whose source is unavailable says so instead of showing a number. The product is fully usable without ever opening this.
type Scene = { chapter: string; title: string; lead: string; body: ReactNode };

const UNAVAILABLE = <p className="story-callout story-callout-quiet">This figure comes from the verified API, which is not reachable right now, so no number is shown.</p>;
const Caveat = ({ children }: { children: ReactNode }) => <p className="story-callout">{children}</p>;
const Stat = ({ value, label, tone }: { value: string; label: string; tone?: "good" | "muted" }) => <span className={tone ? `story-stat story-stat-${tone}` : "story-stat"}><strong>{value}</strong><small>{label}</small></span>;

function Round({ title, round }: { title: string; round: ReforecastRound }) {
  return <div className="story-round">
    <div className="story-round-head"><strong>{round.years ? `${title} · ${round.years}` : title}</strong><span className="story-tag">{round.label}</span></div>
    <div className="story-stat-row">
      <Stat value={`${round.rawRmse.toFixed(2)} → ${round.correctedRmse.toFixed(2)}`} label="RMSE in mm, Raw → corrected" />
      <Stat value={`${score3(round.rawHeavyCsi)} → ${score3(round.classifierHeavyCsi)}`} label="Heavy-rain CSI, Raw → classifier" />
      <Stat value={round.tier} label={`Frozen decision tier · ${count(round.cases)} cases`} tone={round.tier === "FULL" ? "good" : "muted"} />
    </div>
  </div>;
}

function buildScenes(facts: StoryFacts): Scene[] {
  const scenes: Scene[] = [
    { chapter: "Context", title: "The Problem", lead: "Raw numerical forecasts of monsoon rain carry systematic errors.", body: <>
      <p>VarshaSetu studies whether regime-aware, forecast-time post-processing can reduce that error without inventing new observations, and reports honestly where it does not.</p>
      <Caveat>A research prototype on historical data, not an operational service and not an official warning.</Caveat>
    </> },
    { chapter: "Context", title: "Two Experiment Tracks", lead: "Two forecast lineages, kept apart.", body: <>
      <div className="story-track-pair">
        <div><strong>Track A</strong><span>2017 → 2018 → 2019</span><small>NOAA GEFSv12 reforecast</small></div>
        <div><strong>Track B</strong><span>2023 → 2024 → 2025</span><small>Historical operational GEFS</small></div>
      </div>
      <Caveat>Different GEFS lineages and evaluation populations. Results are never pooled. A longer reforecast study is reported separately.</Caveat>
    </> },
    { chapter: "Forecast", title: "Forecast Case", lead: "Every case is a real, dated forecast.", body: <>
      <p>A specific initialization, lead time and paired IMD observation date, never a synthetic example and never called a &ldquo;representative result&rdquo;.</p>
      <Link className="story-link" href="/forecast">Open Forecast Explorer →</Link>
    </> },
    { chapter: "Forecast", title: "Correction vs. Observation", lead: "Raw, corrected and observed on one grid.", body: <>
      <p>Raw GEFS, the corrected output and the paired IMD observation render side by side with the same units, the same domain and one point inspector for all three.</p>
      <Link className="story-link" href="/forecast">See the three panels →</Link>
    </> },
    { chapter: "Forecast", title: "Synoptic Context", lead: "The correction sits inside the atmosphere that produced the forecast.", body: <>
      <p>850-hPa wind, 700-hPa moisture, 500-hPa geopotential height, sea-level pressure and precipitable water are frozen forecast-time fields, viewable beside the rainfall grid.</p>
      <Caveat>This shows the model sees synoptic state. It is not a causal proof that any one atmospheric feature drove any one correction.</Caveat>
    </> },
    { chapter: "Regimes", title: "Pseudo-Regime Architecture", lead: "Regime probabilities route the correction.", body: <>
      <ol className="story-pipeline"><li>Frozen forecast-time atmosphere</li><li>Forecast-only pseudo-regime probabilities</li><li>Hard routing (M3) or soft mixture (M4)</li></ol>
      <Caveat>These are forecast-only pseudo-regimes, not independently observed monsoon regime truth. Coastal and western-disturbance indicators are shown as labelled heuristics and feed no model.</Caveat>
    </> },
    { chapter: "Regimes", title: "Regimes Against Observation", lead: "Detecting each regime state from the forecast, scored on sealed years.", body: <>
      {facts.regimeTasks ? <div className="story-task-grid">{facts.regimeTasks.map((task) => <div key={task.key} className="story-task"><strong>{task.auc == null ? "n/a" : task.auc.toFixed(3)}</strong><span>{task.label}</span><small>AUC · {count(task.cases)} cases · {task.verdict}</small></div>)}</div> : UNAVAILABLE}
      <Caveat>Labels are objective, rule-based and relative (IMD and ERA5 derived), not expert analyses. The pseudo-class named Active did not match observed active spells in the separate check on the operational years.</Caveat>
      <Link className="story-link" href="/regimes">Open Regime Intelligence →</Link>
    </> },
    { chapter: "Skill", title: "Extreme Probability", lead: "Calibrated probabilities of heavy and very-heavy rain.", body: <>
      {facts.probability2025 ? <div className="story-stat-row"><Stat value={signedScore(facts.probability2025.heavyBss)} label="Heavy BSS" tone="good" /><Stat value={signedScore(facts.probability2025.veryHeavyBss)} label="Very-heavy BSS" /></div> : UNAVAILABLE}
      <Caveat>Brier Skill Score against the frozen 2023 event-prevalence reference, shown with its sign. The very-heavy false-alarm ratio nonetheless remained high.</Caveat>
    </> },
    { chapter: "Skill", title: "2019 Benchmark", lead: "Track A, completed held-out test.", body: <>
      {facts.benchmark2019 ? <div className="story-stat-row"><Stat value={mm(facts.benchmark2019.rawRmse)} label="Raw GEFS RMSE" tone="muted" /><Stat value={mm(facts.benchmark2019.correctedRmse)} label={`${facts.benchmark2019.correctedLabel} RMSE`} /><Stat value={rmseChange(facts.benchmark2019.reductionPercent)} label="RMSE change vs Raw" tone="good" /></div> : UNAVAILABLE}
      <p className="story-note">{facts.benchmark2019 ? `${count(facts.benchmark2019.cases)} completed held-out cases` : "Completed held-out cases"} · NOAA GEFSv12 reforecast + IMD.</p>
    </> },
    { chapter: "Skill", title: "2025 Final Test", lead: "Track B, one-time historical final test.", body: <>
      {facts.final2025 ? <div className="story-stat-row"><Stat value={mm(facts.final2025.rawRmse)} label="Raw GEFS RMSE" tone="muted" /><Stat value={mm(facts.final2025.correctedRmse)} label={`${facts.final2025.correctedLabel} RMSE`} /><Stat value={rmseChange(facts.final2025.reductionPercent)} label="RMSE change vs Raw" tone="good" /></div> : UNAVAILABLE}
      <p className="story-note">{facts.final2025 ? `${count(facts.final2025.cases)} cases` : "Completed cases"}. <strong>M1 was selected before the 2025 holdout was opened</strong> and not revised by anything observed afterwards.</p>
    </> },
    { chapter: "Skill", title: "Sealed Reforecast Years", lead: "A heavy-rain correction tested on years no earlier model used.", body: <>
      {facts.reforecast ? <>
        <Round title="Round 1 · sealed years" round={facts.reforecast.round1} />
        {facts.reforecast.round2 ? <Round title="Round 2 · pre-registered confirmation" round={facts.reforecast.round2} /> : null}
      </> : UNAVAILABLE}
      <Caveat>{facts.reforecast && facts.reforecast.round1.tier !== "FULL" ? "Round 1 did not pass its frozen decision rule, so one correction was pre-registered and confirmed on years earlier Track A experiments had used. " : ""}Both rounds use the reforecast lineage only, never the operational years.{facts.reforecast?.regimeAddsValue === false ? " Regime-aware routing was not shown to add value." : ""}</Caveat>
    </> },
    { chapter: "Skill", title: "Extreme-Skill Limitation", lead: "Lower overall error is not better extreme-rain skill.", body: <>
      <p className="story-headline">Raw GEFS retained better extreme-rain spatial FSS than the RMSE-selected model at every tested neighbourhood size. This is stated here deliberately, not hidden in a footnote.</p>
      <Caveat>The dedicated heavy-rain classifiers were tested on reforecast years only, not on the operational years, and their very-heavy probabilities are not calibrated.</Caveat>
    </> },
    { chapter: "Assurance", title: "Requirement Coverage", lead: "Every official requirement, with its limitation stated.", body: <>
      {facts.coverage ? <div className="story-stat-row"><Stat value={`${facts.coverage.implemented} of ${facts.coverage.total}`} label="Rows implemented" tone="good" /><Stat value={`${facts.coverage.partial}`} label="Rows partial, gap stated" tone="muted" /><Stat value={`${facts.coverage.mandatoryImplemented} of ${facts.coverage.mandatoryTotal}`} label="Mandatory rows implemented" /></div> : UNAVAILABLE}
      <Caveat>A row is implemented only if the capability exists, is reachable in the app and is backed by hash-verified evidence. Partial rows say what is missing.</Caveat>
      <Link className="story-link" href="/compliance">Open the coverage page →</Link>
    </> },
    { chapter: "Assurance", title: "Data Quality", lead: "Attrition is quality control, not missing data.", body: <>
      {facts.quality ? <div className="story-stat-row"><Stat value={count(facts.quality.scheduled)} label="Scheduled" tone="muted" /><Stat value={count(facts.quality.c00Eligible)} label="c00 QC-eligible" /><Stat value={count(facts.quality.fiveMemberEligible)} label="Five-member QC-eligible" /></div> : UNAVAILABLE}
      <p className="story-note">Every scheduled message was acquired; the eligible counts reflect canonical scientific quality control.</p>
    </> },
    { chapter: "Assurance", title: "Reproducibility", lead: "Nothing is trusted that cannot be checked.", body: <>
      <ul className="story-checks"><li>Frozen models, with no retraining after any test was opened</li><li>Hash-verified artifacts at every stage, refused on any mismatch</li><li>Protocols frozen and signed before sealed data were read</li><li>An experimental live-cycle worker proven by exact replay, with no skill claim</li></ul>
      <p className="story-closing"><strong>VarshaSetu</strong><br />Research prototype for scientifically transparent monsoon forecast post-processing.</p>
    </> },
  ];
  return SHOW_COMPLIANCE_PAGE ? scenes : scenes.filter((scene) => scene.title !== "Requirement Coverage");
}

const EMPTY_FACTS: StoryFacts = { benchmark2019: null, final2025: null, probability2025: null, quality: null, coverage: null, regimeTasks: null, reforecast: null };
// The number of scenes does not depend on the data; keyboard handling uses this constant so the effect never re-subscribes.
const SCENE_COUNT = buildScenes(EMPTY_FACTS).length;

/** The caller mounts this only while open (see PresentButton in app-shell.tsx), so each open starts fresh at scene 0. */
export function StoryMode({ onClose }: { onClose: () => void }) {
  const [index, setIndex] = useState(0);
  const dialogRef = useRef<HTMLDivElement>(null);
  const stale = { staleTime: 5 * 60_000, retry: 1 } as const;
  // 2019 comes from the verified API; 2025 and data quality come from the generated frozen presentation bundle; the newer scenes read their own verified endpoints.
  const comparison = useQuery({ queryKey: ["story-model-comparison"], queryFn: () => getScience("/model-comparison", modelComparisonSchema), ...stale });
  const coverage = useQuery({ queryKey: ["story-coverage"], queryFn: () => getPsCoverage(), enabled: SHOW_COMPLIANCE_PAGE, ...stale });
  const r03 = useQuery({ queryKey: ["story-r03"], queryFn: () => getR03Result(), ...stale });
  const r05 = useQuery({ queryKey: ["story-r05"], queryFn: () => getR05Result(), ...stale });
  const confirmation = useQuery({ queryKey: ["story-r05-confirmation"], queryFn: () => getR05Confirmation(), ...stale });
  const SCENES = useMemo(
    () => buildScenes(buildStoryFacts({ comparison: comparison.data ?? null, final2025, quality: staticQuality, coverage: coverage.data ?? null, r03: r03.data ?? null, r05: r05.data ?? null, confirmation: confirmation.data ?? null })),
    [comparison.data, coverage.data, r03.data, r05.data, confirmation.data],
  );
  const chapters = useMemo(() => SCENES.reduce<{ name: string; items: { title: string; index: number }[] }[]>((groups, scene, sceneIndex) => {
    const last = groups[groups.length - 1];
    if (last && last.name === scene.chapter) last.items.push({ title: scene.title, index: sceneIndex });
    else groups.push({ name: scene.chapter, items: [{ title: scene.title, index: sceneIndex }] });
    return groups;
  }, []), [SCENES]);

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
        const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>("a[href], button:not([disabled])")];
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
      <div className="story-identity"><span className="brand-symbol" aria-hidden="true" /><strong>VarshaSetu</strong><em>Presentation</em></div>
      <span className="story-progress" aria-live="polite">Scene {index + 1} of {SCENES.length}</span>
      <div className="story-progress-bar" aria-hidden="true"><div style={{ width: `${(100 * (index + 1)) / SCENES.length}%` }} /></div>
      <button type="button" className="story-exit" onClick={onClose}>Exit</button>
    </div>
    <div className="story-main">
      <nav className="story-rail" aria-label="Scenes">
        {chapters.map((group) => <div key={group.name} className="story-rail-group">
          <span className="story-rail-chapter">{group.name}</span>
          {group.items.map((item) => <button key={item.title} type="button" className={item.index === index ? "active" : item.index < index ? "done" : ""} aria-current={item.index === index ? "step" : undefined} onClick={() => setIndex(item.index)}><i aria-hidden="true">{String(item.index + 1).padStart(2, "0")}</i>{item.title}</button>)}
        </div>)}
      </nav>
      <div className="story-stage">
        <div className="story-scene" key={index}>
          <span className="story-kicker"><b>{String(index + 1).padStart(2, "0")}</b>{scene.chapter}</span>
          <h2>{scene.title}</h2>
          <p className="story-lead">{scene.lead}</p>
          <div className="story-scene-body">{scene.body}</div>
        </div>
      </div>
    </div>
    <div className="story-navbar">
      <button type="button" onClick={() => setIndex((current) => Math.max(current - 1, 0))} disabled={index === 0}>← Back</button>
      <div className="story-dots" aria-hidden="true">{SCENES.map((item, dotIndex) => <span key={item.title} className={dotIndex === index ? "active" : ""} />)}</div>
      <span className="story-hint" aria-hidden="true"><kbd>←</kbd><kbd>→</kbd> navigate · <kbd>Esc</kbd> exit</span>
      {index === SCENES.length - 1 ? <button type="button" onClick={onClose}>Exit</button> : <button type="button" onClick={() => setIndex((current) => Math.min(current + 1, SCENES.length - 1))}>Next →</button>}
    </div>
  </div>;
}
