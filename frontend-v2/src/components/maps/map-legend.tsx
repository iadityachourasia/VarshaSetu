"use client";

import { useEffect } from "react";
import { probabilityColor, rainfallColor } from "@/lib/maps/grid";
import { DECISION_BINS, PROBABILITY_BINS, RAINFALL_BINS, SCORE_BINS, type EmphasisKind, type LegendBin } from "@/lib/maps/emphasis";
import { useMapEmphasis } from "./map-emphasis";

/**
 * The classes of a legend. Pointing at (or tabbing to) one dims every map cell outside it, on every map of the page that draws the same kind of quantity; leaving restores the maps.
 * Each class is a real button so keyboard users get the same emphasis; nothing is selected or filtered permanently.
 */
function LegendBins({ kind, bins, color, className }: { kind: EmphasisKind; bins: LegendBin[]; color: (sample: number) => string; className?: string }) {
  const { emphasis, setEmphasis } = useMapEmphasis();
  useEffect(() => () => setEmphasis(null), [setEmphasis]);
  const active = emphasis?.kind === kind ? emphasis : null;
  const on = (bin: LegendBin) => setEmphasis({ kind, lo: bin.lo, hi: bin.hi });
  return <div className={`legend-bins${className ? ` ${className}` : ""}${active ? " legend-bins-active" : ""}`}>
    {bins.map((bin) => <button key={bin.label} type="button" className={`legend-bin${active && active.lo === bin.lo && active.hi === bin.hi ? " legend-bin-active" : ""}`}
      onMouseEnter={() => on(bin)} onMouseLeave={() => setEmphasis(null)} onFocus={() => on(bin)} onBlur={() => setEmphasis(null)}
      aria-label={`Highlight class ${bin.label} on the maps`}>
      <i style={{ background: color(bin.sample) }} aria-hidden="true" /><small>{bin.label}</small>
    </button>)}
  </div>;
}

export function RainLegend() {
  return <div className="legend" aria-label="Shared rainfall legend, millimeters per 24 hours"><LegendBins kind="rainfall" bins={RAINFALL_BINS} color={rainfallColor} /><span className="legend-unit">mm / 24 h</span></div>;
}

export function ProbabilityLegend() {
  return <div className="legend" aria-label="Probability legend, zero to one hundred percent"><LegendBins kind="probability" bins={PROBABILITY_BINS} color={probabilityColor} /><span className="legend-unit">probability</span></div>;
}

/** Same colours as the probability legend, labelled as a score: the classifier output is not a calibrated probability. */
export function ScoreLegend() {
  return <div className="legend" aria-label="Classifier score legend, zero to one"><LegendBins kind="probability" bins={SCORE_BINS} color={probabilityColor} /><span className="legend-unit">classifier score (not a probability)</span></div>;
}

export function DecisionLegend() {
  return <div className="legend" aria-label="Forecast decision legend"><LegendBins kind="decision" bins={DECISION_BINS} color={(sample) => (sample >= 0.5 ? "#d1495b" : "#cfd8dc")} className="decision-bins" /></div>;
}
