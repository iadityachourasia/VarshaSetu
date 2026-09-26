import type { ReactNode } from "react";
import type { DataSourceMode } from "@/lib/data-source";
import { DATA_SOURCE_LABEL } from "@/lib/data-source";

export function PageHeading({ title, subtitle, action }: { title: string; subtitle: string; action?: ReactNode }) {
  return <div className="page-heading"><div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>;
}

export function SectionHeading({ title, note }: { title: string; note?: string }) {
  return <div className="section-heading"><h2>{title}</h2>{note ? <p>{note}</p> : null}</div>;
}

export function Metric({ label, value, detail, tone }: { label: string; value: string; detail?: string; tone?: "teal" | "amber" | "muted" }) {
  return <div className={`metric ${tone ? `metric-${tone}` : ""}`}><span className="metric-label">{label}</span><strong className="metric-value">{value}</strong>{detail ? <span className="metric-detail">{detail}</span> : null}</div>;
}

export function ErrorState({ message = "Scientific artifacts are unavailable. Start the verified historical API and try again." }: { message?: string }) {
  return <div className="state-message" role="alert"><strong>Data unavailable</strong><p>{message}</p></div>;
}

export function EmptyState({ message }: { message: string }) {
  return <div className="state-message"><strong>Nothing to display</strong><p>{message}</p></div>;
}

export function LoadingState({ label = "Loading verified case" }: { label?: string }) {
  return <div className="loading-state" role="status" aria-label={label}><span className="skeleton-block" /><span className="skeleton-block" /><span className="skeleton-block" /><span className="sr-only">{label}</span></div>;
}

export function PrototypeNote() {
  return <span className="prototype-note">Historical scientific prototype · not operational</span>;
}

/** Subtle data-source-mode chip for workspace headers / provenance contexts.
 * Deliberately quiet in normal operation (VERIFIED_API renders nothing) and
 * only becomes visible when the fallback, an integrity failure, or a network
 * failure actually occurred -- see lib/data-source.ts for the governing rule
 * that a fallback is never silent. */
export function DataSourceIndicator({ mode }: { mode: DataSourceMode }) {
  if (mode === "VERIFIED_API") return null;
  const tone = mode === "INTEGRITY_FAILURE" ? "amber" : mode === "VERIFIED_STATIC_FALLBACK" ? "muted" : "amber";
  return <span className={`data-source-chip data-source-${tone}`} role="status">{DATA_SOURCE_LABEL[mode]}</span>;
}
