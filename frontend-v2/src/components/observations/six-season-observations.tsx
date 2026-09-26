"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { PageHeading, PrototypeNote } from "@/components/science/common";
import observations from "../../../public/science/operational-v1/observations_six_seasons.json";

const seasons = [2017, 2018, 2019, 2023, 2024, 2025] as const;
const months = [6, 7, 8, 9, 10] as const;
const MONTH_LABEL: Record<number, string> = { 6: "JUN", 7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT*" };
type HeatmapMetric = "mean_mm" | "heavy_cells" | "very_heavy_cells";
const HEATMAP_METRIC_LABEL: Record<HeatmapMetric, string> = {
  mean_mm: "Mean domain rainfall (mm)", heavy_cells: "Days with ≥1 Heavy cell", very_heavy_cells: "Days with ≥1 Very Heavy cell",
};

/** One cell = one year x month over the same 750 real daily IMD records the
 * rest of this page already reads -- a client-side aggregate, not a new
 * science artifact. Heavy/very-heavy metrics count days with at least one
 * qualifying cell (an event-day count); mean rainfall averages the daily
 * domain-mean IMD value. Cell intensity is relative to the matrix's own max,
 * not an absolute climatological scale. */
function monthYearMatrix(metric: HeatmapMetric): { year: number; month: number; value: number | null }[] {
  return seasons.flatMap((year) => months.map((month) => {
    const rows = observations.records.filter((item) => item.year === year && item.month === month);
    if (rows.length === 0) return { year, month, value: null };
    if (metric === "mean_mm") {
      const withMean = rows.filter((item) => item.mean_mm != null);
      return { year, month, value: withMean.length ? withMean.reduce((sum, item) => sum + (item.mean_mm ?? 0), 0) / withMean.length : null };
    }
    return { year, month, value: rows.filter((item) => item[metric] > 0).length };
  }));
}

export function SixSeasonObservations() {
  const [year, setYear] = useState<number>(2025);
  const [month, setMonth] = useState<number>(7);
  const [heatmapMetric, setHeatmapMetric] = useState<HeatmapMetric>("mean_mm");
  const records = useMemo(() => observations.records.filter((item) => item.year === year && item.month === month), [year, month]);
  const matrix = useMemo(() => monthYearMatrix(heatmapMetric), [heatmapMetric]);
  const matrixMax = Math.max(1e-6, ...matrix.map((cell) => cell.value ?? 0));
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
    <section className="phase5-analysis-block"><h2>Six-season month × year matrix</h2><div className="phase5-controls"><label>Metric<select value={heatmapMetric} onChange={(event) => setHeatmapMetric(event.target.value as HeatmapMetric)}><option value="mean_mm">Mean domain rainfall</option><option value="heavy_cells">Heavy event-day count</option><option value="very_heavy_cells">Very-heavy event-day count</option></select></label></div>
      <table className="phase5-heatmap-table"><thead><tr><th scope="col">Year</th>{months.map((item) => <th scope="col" key={item}>{MONTH_LABEL[item]}</th>)}</tr></thead><tbody>{seasons.map((seasonYear) => <tr key={seasonYear}><th scope="row">{seasonYear}</th>{months.map((monthKey) => {
        const cell = matrix.find((item) => item.year === seasonYear && item.month === monthKey);
        const intensity = cell?.value != null ? Math.min(1, cell.value / matrixMax) : 0;
        return <td key={monthKey} style={cell?.value != null ? { background: `color-mix(in srgb, var(--teal) ${Math.round(20 + 70 * intensity)}%, var(--surface-raised))` } : undefined} title={`${seasonYear} ${MONTH_LABEL[monthKey]}: ${cell?.value == null ? "no data" : heatmapMetric === "mean_mm" ? `${cell.value.toFixed(2)} mm` : `${cell.value} days`}`}>{cell?.value == null ? "—" : heatmapMetric === "mean_mm" ? cell.value.toFixed(1) : cell.value}</td>;
      })}</tr>)}</tbody></table>
      <p className="phase5-caveat">{HEATMAP_METRIC_LABEL[heatmapMetric]} per year × month, aggregated client-side from the same 750 real daily IMD records used elsewhere on this page. Cell shading is relative to this matrix&rsquo;s own maximum, not an absolute or climatological scale. October covers only the evaluated 1–3 day tail.</p>
    </section>
    <div className="phase5-controls"><label>Observation month<select value={month} onChange={(event) => setMonth(Number(event.target.value))}><option value={6}>June</option><option value={7}>July</option><option value={8}>August</option><option value={9}>September</option><option value={10}>October 1–3</option></select></label></div>
    <section className="phase5-analysis-block"><h2>{year} daily observed event timeline</h2><div className="phase5-event-calendar" role="list" aria-label="IMD daily Heavy and Very Heavy cell counts">{records.map((record) => <div key={record.date} role="listitem" className={record.very_heavy_cells > 0 ? "very-heavy" : record.heavy_cells > 0 ? "heavy" : "none"} title={`${record.date}: ${record.heavy_cells} Heavy, ${record.very_heavy_cells} Very Heavy cells; ${record.valid_cells} valid cells`}><strong>{record.date.slice(8)}</strong><span>{record.very_heavy_cells > 0 ? "VH" : record.heavy_cells > 0 ? "H" : "—"}</span></div>)}</div><p className="phase5-caveat">H = at least one IMD cell ≥64.5 mm / 24 h; VH = at least one ≥115.6 mm / 24 h. The annual files give daily date labels but do not explicitly encode accumulation bounds. October includes only days 1–3.</p></section>
    {year === 2019 || year === 2023 || year === 2024 || year === 2025 ? <Link className="text-link" href={`/casebook?experiment=${year === 2019 ? "reforecast" : "operational"}&year=${year}`}>Browse forecast-paired historical cases →</Link> : null}
  </div>;
}
