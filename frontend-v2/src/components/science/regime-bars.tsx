import { regimeName, percent } from "@/lib/format";

const order = ["ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED"];

export function RegimeBars({ probabilities, dominant }: { probabilities: Record<string, number>; dominant: string }) {
  return <section className="regime-panel" aria-label="Forecast-only regime probabilities"><div className="panel-caption"><span className="small-label">REGIME INTELLIGENCE</span><strong>{regimeName(dominant)}</strong></div>
    <div className="regime-bars">{order.map((key) => <div className="regime-row" key={key}><span>{regimeName(key)}</span><div className="regime-track"><div style={{ width: percent(probabilities[key], 2) }} /></div><strong>{percent(probabilities[key])}</strong></div>)}</div>
    <p className="micro-note">Prototype classifier reproduces a deterministic forecast-only regime methodology; this is not independent meteorological accuracy.</p>
  </section>;
}
