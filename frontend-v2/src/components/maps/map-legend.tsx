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
