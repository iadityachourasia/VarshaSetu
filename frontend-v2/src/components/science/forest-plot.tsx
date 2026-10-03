"use client";

import { useEffect, useId, useRef, useState } from "react";

export type ForestRow = { label: string; point: number | null; low: number | null; high: number | null };

const finite = (value: number | null): value is number => value != null && Number.isFinite(value);
const ROW = 30;
const TOP = 26;
const LABEL_WIDTH = 132;
const STACKED = "(max-width: 900px)";   // the forest grid becomes one column here (see .forest-grid)
const RIGHT = 70;

/** Decimal places that keep the axis ticks distinct for the span being drawn. */
export function tickDigits(span: number): number {
  return span >= 1 ? 1 : span >= 0.1 ? 2 : 3;
}

/**
 * Point estimates with their intervals on one shared axis, a dashed line at zero, and the interval drawn in the accent colour only when it excludes zero.
 * It restates numbers the page already prints in a table (the table stays, for exact values and for assistive technology); the plot is for seeing at a
 * glance which contrasts clear zero and which do not. A row without a reported interval is drawn as an empty slot, never as a guess.
 */
export function ForestPlot({ title, rows, showLabels: labelsWanted = true, width = 520 }: { title: string; rows: ForestRow[]; showLabels?: boolean; width?: number }) {
  const figure = useRef<HTMLElement>(null);
  const [measured, setMeasured] = useState<{ width: number; stacked: boolean } | null>(null);
  useEffect(() => {
    const node = figure.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const update = () => setMeasured({ width: Math.round(node.clientWidth), stacked: window.matchMedia(STACKED).matches });
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  // The drawing is laid out at its rendered width, so its text stays at a readable size on any screen. When the plots stack (phones),
  // each one carries its own row labels, because the labelled neighbour is no longer beside it.
  const WIDTH = measured && measured.width > 0 ? Math.max(280, measured.width) : width;
  const showLabels = labelsWanted || Boolean(measured?.stacked);
  const id = useId();
  const drawn = rows.filter((row) => finite(row.point) && finite(row.low) && finite(row.high));
  const lows = drawn.map((row) => row.low as number);
  const highs = drawn.map((row) => row.high as number);
  const min = Math.min(0, ...lows);
  const max = Math.max(0, ...highs);
  const pad = (max - min || 1) * 0.08;
  const lo = min - pad;
  const hi = max + pad;
  const left = showLabels ? (WIDTH < 420 ? 92 : LABEL_WIDTH) : 12;
  const plotWidth = WIDTH - left - RIGHT;
  const x = (value: number) => left + ((value - lo) / (hi - lo)) * plotWidth;
  const height = TOP + rows.length * ROW + 24;
  const digits = tickDigits(hi - lo);
  // Label the ends of the data and the zero line, and drop an end label that would sit on top of zero.
  const ticks = [0, ...[lo + pad, hi - pad].filter((value) => Math.abs(value) > (hi - lo) * 0.12)];
  const summary = `${title}: ${drawn.filter((row) => (row.low as number) > 0 || (row.high as number) < 0).length} of ${drawn.length} intervals exclude zero`;
  return <figure className="forest-plot" ref={figure}>
    <svg viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-labelledby={`${id}-t`} focusable="false">
      <title id={`${id}-t`}>{summary}</title>
      <text className="forest-title" x={left} y={14}>{title}</text>
      <line className="forest-zero" x1={x(0)} x2={x(0)} y1={TOP - 6} y2={TOP + rows.length * ROW - 2} />
      {rows.map((row, index) => {
        const y = TOP + index * ROW + ROW / 2;
        const ok = finite(row.point) && finite(row.low) && finite(row.high);
        const excludes = ok && ((row.low as number) > 0 || (row.high as number) < 0);
        return <g key={row.label} className={excludes ? "forest-row forest-excludes" : "forest-row"}>
          <title>{ok ? `${row.label}: ${(row.point as number) >= 0 ? "+" : ""}${(row.point as number).toFixed(3)} (interval ${(row.low as number).toFixed(3)} to ${(row.high as number).toFixed(3)}) ${excludes ? "excludes zero" : "includes zero"}` : `${row.label}: not reported`}</title>
          {index % 2 === 0 ? <rect className="forest-band" x={0} y={y - ROW / 2} width={WIDTH} height={ROW} /> : null}
          {showLabels ? <text className="forest-label" x={0} y={y + 4}>{row.label}</text> : null}
          {ok ? <>
            <line className="forest-interval" x1={x(row.low as number)} x2={x(row.high as number)} y1={y} y2={y} />
            <line className="forest-cap" x1={x(row.low as number)} x2={x(row.low as number)} y1={y - 5} y2={y + 5} />
            <line className="forest-cap" x1={x(row.high as number)} x2={x(row.high as number)} y1={y - 5} y2={y + 5} />
            <circle className="forest-point" cx={x(row.point as number)} cy={y} r={3.6} />
            <text className="forest-value" x={WIDTH} y={y + 4} textAnchor="end">{`${(row.point as number) >= 0 ? "+" : ""}${(row.point as number).toFixed(3)}`}</text>
          </> : <text className="forest-value" x={WIDTH} y={y + 4} textAnchor="end">not reported</text>}
        </g>;
      })}
      {ticks.map((value) => <text key={value} className="forest-tick" x={x(value)} y={height - 6} textAnchor="middle">{value === 0 ? "0" : value.toFixed(digits)}</text>)}
    </svg>
  </figure>;
}
