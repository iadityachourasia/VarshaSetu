import type { Palette } from "./grid";

/** Legend emphasis: hovering or focusing a legend class dims every map cell outside that class. Pure data and helpers; the maps and the legends share them. */
export type EmphasisKind = "rainfall" | "probability" | "decision";
export type Emphasis = { kind: EmphasisKind; lo: number; hi: number };
export type LegendBin = { label: string; sample: number; lo: number; hi: number };

/** Alpha of a cell outside the emphasised class: still visible as context, clearly subordinate. */
export const DIM_ALPHA = 40;

export const RAINFALL_BINS: LegendBin[] = [
  { label: "<0.1", sample: 0, lo: -Infinity, hi: 0.1 }, { label: "0.1–<5", sample: 1, lo: 0.1, hi: 5 }, { label: "5–<20", sample: 10, lo: 5, hi: 20 },
  { label: "20–<40", sample: 30, lo: 20, hi: 40 }, { label: "40–<64.5", sample: 50, lo: 40, hi: 64.5 }, { label: "64.5–<115.6", sample: 80, lo: 64.5, hi: 115.6 },
  { label: "≥115.6", sample: 120, lo: 115.6, hi: Infinity },
];
export const PROBABILITY_BINS: LegendBin[] = [
  { label: "0–<5%", sample: 0, lo: -Infinity, hi: 0.05 }, { label: "5–<15%", sample: 0.1, lo: 0.05, hi: 0.15 }, { label: "15–<30%", sample: 0.2, lo: 0.15, hi: 0.3 },
  { label: "30–<50%", sample: 0.4, lo: 0.3, hi: 0.5 }, { label: "50–<70%", sample: 0.6, lo: 0.5, hi: 0.7 }, { label: "70–<90%", sample: 0.8, lo: 0.7, hi: 0.9 },
  { label: "90–100%", sample: 1, lo: 0.9, hi: Infinity },
];
export const SCORE_BINS: LegendBin[] = PROBABILITY_BINS.map((bin, index) => ({ ...bin, label: ["0–<0.05", "0.05–<0.15", "0.15–<0.3", "0.3–<0.5", "0.5–<0.7", "0.7–<0.9", "0.9–1"][index] }));
export const DECISION_BINS: LegendBin[] = [
  { label: "Forecast: no (score below the frozen threshold)", sample: 0, lo: -Infinity, hi: 0.5 },
  { label: "Forecast: yes (score at or above it)", sample: 1, lo: 0.5, hi: Infinity },
];

export function inBin(value: number, lo: number, hi: number): boolean {
  return value >= lo && value < hi;
}

/** Which legend (if any) can emphasise a map drawn with this palette. */
export function emphasisKind(palette: Palette): EmphasisKind | null {
  return palette === "rainfall" ? "rainfall" : palette === "probability" ? "probability" : palette === "decision" ? "decision" : null;
}

/** The emphasis that applies to a map of this palette: only a legend of the same kind of quantity can dim it. */
export function emphasisFor(emphasis: Emphasis | null, palette: Palette): Emphasis | null {
  return emphasis && emphasis.kind === emphasisKind(palette) ? emphasis : null;
}
