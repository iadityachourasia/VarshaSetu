import { probabilityColor, rainfallColor } from "@/lib/maps/grid";

const rainfallBins = [
  ["<0.1", 0], ["0.1–<5", 1], ["5–<20", 10], ["20–<40", 30],
  ["40–<64.5", 50], ["64.5–<115.6", 80], ["≥115.6", 120],
] as const;
const probabilityBins = [
  ["0–<5%", 0], ["5–<15%", 0.1], ["15–<30%", 0.2], ["30–<50%", 0.4],
  ["50–<70%", 0.6], ["70–<90%", 0.8], ["90–100%", 1],
] as const;

export function RainLegend() {
  return <div className="legend" aria-label="Shared rainfall legend, millimeters per 24 hours"><div className="legend-bins">{rainfallBins.map(([label, sample]) => <span key={label} className="legend-bin"><i style={{ background: rainfallColor(sample) }} aria-hidden="true" /><small>{label}</small></span>)}</div><span className="legend-unit">mm / 24 h</span></div>;
}

export function ProbabilityLegend() {
  return <div className="legend" aria-label="Probability legend, zero to one hundred percent"><div className="legend-bins">{probabilityBins.map(([label, sample]) => <span key={label} className="legend-bin"><i style={{ background: probabilityColor(sample) }} aria-hidden="true" /><small>{label}</small></span>)}</div><span className="legend-unit">probability</span></div>;
}

const scoreBins = [["0–<0.05", 0], ["0.05–<0.15", 0.1], ["0.15–<0.3", 0.2], ["0.3–<0.5", 0.4], ["0.5–<0.7", 0.6], ["0.7–<0.9", 0.8], ["0.9–1", 1]] as const;

/** Same colours as the probability legend, labelled as a score: the classifier output is not a calibrated probability. */
export function ScoreLegend() {
  return <div className="legend" aria-label="Classifier score legend, zero to one"><div className="legend-bins">{scoreBins.map(([label, sample]) => <span key={label} className="legend-bin"><i style={{ background: probabilityColor(sample) }} aria-hidden="true" /><small>{label}</small></span>)}</div><span className="legend-unit">classifier score (not a probability)</span></div>;
}

export function DecisionLegend() {
  return <div className="legend" aria-label="Forecast decision legend"><div className="legend-bins decision-bins"><span className="legend-bin"><i style={{ background: "#cfd8dc" }} aria-hidden="true" /><small>Forecast: no (score below the frozen threshold)</small></span><span className="legend-bin"><i style={{ background: "#d1495b" }} aria-hidden="true" /><small>Forecast: yes (score at or above it)</small></span></div></div>;
}
