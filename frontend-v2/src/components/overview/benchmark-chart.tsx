export type BenchmarkCase = {
  case_id: string;
  initialization_utc: string;
  raw_rmse_mm: number | null;
  corrected_rmse_mm: number | null;
  eligible?: boolean;
};

export type BenchmarkPoint = {
  date: number;
  raw: number;
  corrected: number;
};

/** Only a complete paired population may be drawn beside a frozen benchmark. */
export function pairedCaseSeries(cases: BenchmarkCase[], expectedCount: number, year: 2019 | 2025): BenchmarkPoint[] | null {
  if (cases.length !== expectedCount || expectedCount < 2) return null;
  const ids = new Set<string>();
  const points = cases.flatMap((item) => {
    const date = Date.parse(item.initialization_utc);
    if (!item.case_id || ids.has(item.case_id) || item.eligible === false) return [];
    ids.add(item.case_id);
    if (item.raw_rmse_mm === null || item.corrected_rmse_mm === null) return [];
    if (!Number.isFinite(date) || !Number.isFinite(item.raw_rmse_mm) || !Number.isFinite(item.corrected_rmse_mm)) return [];
    if (new Date(date).getUTCFullYear() !== year) return [];
    if (item.raw_rmse_mm < 0 || item.corrected_rmse_mm < 0) return [];
    return [{ date, raw: item.raw_rmse_mm, corrected: item.corrected_rmse_mm }];
  });
  if (points.length !== expectedCount || ids.size !== expectedCount) return null;
  return points.sort((a, b) => a.date - b.date);
}

function linePath(points: BenchmarkPoint[], key: "raw" | "corrected", max: number) {
  return points.map((point, index) => {
    const x = 40 + index / (points.length - 1) * 390;
    const y = 172 - point[key] / max * 150;
    return `${index ? "L" : "M"}${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(" ");
}

export function BenchmarkChart({ points, year, raw, corrected, correctedLabel }: {
  points: BenchmarkPoint[] | null;
  year: 2019 | 2025;
  raw: number;
  corrected: number;
  correctedLabel: string;
}) {
  if (!points) return <figure className="overview-aggregate-chart" aria-label={`${year} aggregate RMSE comparison`}>
    <figcaption>Aggregate RMSE · case series unavailable</figcaption>
    <div className="overview-aggregate-row"><span>Raw GEFS</span><i style={{ width: `${Math.min(100, raw / Math.max(raw, corrected) * 100)}%` }} /><b>{raw.toFixed(2)} mm</b></div>
    <div className="overview-aggregate-row corrected"><span>{correctedLabel}</span><i style={{ width: `${Math.min(100, corrected / Math.max(raw, corrected) * 100)}%` }} /><b>{corrected.toFixed(2)} mm</b></div>
  </figure>;

  const max = Math.max(10, Math.ceil(Math.max(...points.flatMap((point) => [point.raw, point.corrected])) / 10) * 10);
  const months = new Map<number, { first: number; last: number; text: string }>();
  points.forEach((point, index) => {
    const date = new Date(point.date);
    const month = date.getUTCMonth();
    const existing = months.get(month);
    if (existing) existing.last = index;
    else months.set(month, { first: index, last: index, text: date.toLocaleString("en-US", { month: "short", timeZone: "UTC" }) });
  });
  const monthLabels = [...months.values()].map(({ first, last, text }) => ({
    x: Math.max(52, Math.min(418, 40 + (first + last) / 2 / (points.length - 1) * 390)), text,
  }));
  return <figure className="overview-case-chart">
    <figcaption>{year} per-case RMSE (mm) · {points.length} paired cases</figcaption>
    <div className="overview-chart-key"><span className="raw">Raw GEFS</span><span className="corrected">{correctedLabel}</span></div>
    <div className="overview-chart-viewport" tabIndex={0} aria-label={`Scrollable ${year} per-case RMSE chart`}>
    <svg viewBox="0 0 460 205" role="img" aria-label={`${year} per-case RMSE. Raw GEFS and ${correctedLabel}, ordered by forecast initialization date; connecting segments only join separate cases.`}>
      {[0, .5, 1].map((fraction) => <g key={fraction}><line x1="40" x2="430" y1={172 - fraction * 150} y2={172 - fraction * 150} className="overview-chart-grid" /><text x="31" y={176 - fraction * 150} textAnchor="end">{Math.round(max * fraction)}</text></g>)}
      <path d={linePath(points, "raw", max)} className="overview-chart-raw" />
      <path d={linePath(points, "corrected", max)} className="overview-chart-corrected" />
      {monthLabels.map(({ x, text }) => <text key={text} x={x} y="195" textAnchor="middle">{text}</text>)}
    </svg>
    </div>
    <p className="overview-chart-note">Each point is a separate forecast case, ordered by initialization date. Scroll the chart horizontally on narrow screens.</p>
  </figure>;
}
