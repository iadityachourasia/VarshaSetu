"use client";

import type { ReactNode } from "react";
import { ResponsiveContainer } from "recharts";

/** Keep a real first render while ResizeObserver measures the final width. */
export function ChartFrame({ children, caption }: { children: ReactNode; caption: ReactNode }) {
  return <figure className="chart-figure">
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height={290} minWidth={0} initialDimension={{ width: 640, height: 290 }}>
        {children}
      </ResponsiveContainer>
    </div>
    <figcaption>{caption}</figcaption>
  </figure>;
}
