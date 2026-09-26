"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { PageHeading, PrototypeNote } from "@/components/science/common";
import observations from "../../../public/science/operational-v1/observations_six_seasons.json";

const seasons = [2017, 2018, 2019, 2023, 2024, 2025] as const;

export function SixSeasonObservations() {
  const [year, setYear] = useState<number>(2025);
  const [month, setMonth] = useState<number>(7);
  const records = useMemo(() => observations.records.filter((item) => item.year === year && item.month === month), [year, month]);
  const summaries = useMemo(() => seasons.map((item) => {
    const data = observations.records.filter((record) => record.year === item);
    return { year: item, days: data.length, heavyDays: data.filter((record) => record.heavy_cells > 0).length,
      veryHeavyDays: data.filter((record) => record.very_heavy_cells > 0).length,
      meanDailyDomainMm: data.reduce((sum, record) => sum + (record.mean_mm ?? 0), 0) / data.filter((record) => record.mean_mm != null).length };
  }), []);
  return <div className="page-content"><PageHeading title="Six-Season Observations" subtitle="Descriptive IMD context across six evaluated monsoon seasons" action={<PrototypeNote />} />
    <p className="phase5-caveat">Not a climatology or climate-trend analysis. These are six separate historical daily IMD files, evaluated on 1,301 common domain-cell positions with daily missingness excluded. Forecast experiments remain separate.</p>
    <div className="phase5-observation-tracks"><section><h2>GEFSv12 reforecast lineage</h2><div>{summaries.slice(0, 3).map((item) => <button type="button" className={year === item.year ? "selected" : ""} key={item.year} onClick={() => setYear(item.year)}><strong>{item.year}</strong><span>{item.year === 2017 ? "TRAIN" : item.year === 2018 ? "VALIDATE" : "FINAL TEST"}</span><small>{item.heavyDays} days with Heavy cells</small></button>)}</div></section><section><h2>Historical operational GEFS lineage</h2><div>{summaries.slice(3).map((item) => <button type="button" className={year === item.year ? "selected" : ""} key={item.year} onClick={() => setYear(item.year)}><strong>{item.year}</strong><span>{item.year === 2023 ? "CROSS-FIT" : item.year === 2024 ? "VALIDATE" : "FINAL TEST COMPLETED"}</span><small>{item.heavyDays} days with Heavy cells</small></button>)}</div></section></div>
    <div className="phase5-analysis-block"><h2>{year} observation summary · June 1–October 3</h2><div className="phase5-metric-strip">{summaries.filter((item) => item.year === year).map((item) => <span key={item.year}><small>Daily date labels</small><strong>{item.days}</strong></span>)}{summaries.filter((item) => item.year === year).map((item) => <span key={`mean-${item.year}`}><small>Mean of daily domain means</small><strong>{item.meanDailyDomainMm.toFixed(2)} mm</strong></span>)}{summaries.filter((item) => item.year === year).map((item) => <span key={`heavy-${item.year}`}><small>Days with ≥1 Heavy cell</small><strong>{item.heavyDays}</strong></span>)}{summaries.filter((item) => item.year === year).map((item) => <span key={`vh-${item.year}`}><small>Days with ≥1 Very Heavy cell</small><strong>{item.veryHeavyDays}</strong></span>)}</div><p>These are descriptive observation counts over the fixed display domain, not forecast skill or an annual national rainfall total.</p></div>
    <div className="phase5-controls"><label>Observation month<select value={month} onChange={(event) => setMonth(Number(event.target.value))}><option value={6}>June</option><option value={7}>July</option><option value={8}>August</option><option value={9}>September</option><option value={10}>October 1–3</option></select></label></div>
    <section className="phase5-analysis-block"><h2>{year} daily observed event timeline</h2><div className="phase5-event-calendar" role="list" aria-label="IMD daily Heavy and Very Heavy cell counts">{records.map((record) => <div key={record.date} role="listitem" className={record.very_heavy_cells > 0 ? "very-heavy" : record.heavy_cells > 0 ? "heavy" : "none"} title={`${record.date}: ${record.heavy_cells} Heavy, ${record.very_heavy_cells} Very Heavy cells; ${record.valid_cells} valid cells`}><strong>{record.date.slice(8)}</strong><span>{record.very_heavy_cells > 0 ? "VH" : record.heavy_cells > 0 ? "H" : "—"}</span></div>)}</div><p className="phase5-caveat">H = at least one IMD cell ≥64.5 mm / 24 h; VH = at least one ≥115.6 mm / 24 h. The annual files give daily date labels but do not explicitly encode accumulation bounds. October includes only days 1–3.</p></section>
    {year === 2019 || year === 2023 || year === 2024 || year === 2025 ? <Link className="text-link" href={`/casebook?experiment=${year === 2019 ? "reforecast" : "operational"}&year=${year}`}>Browse forecast-paired historical cases →</Link> : null}
  </div>;
}
