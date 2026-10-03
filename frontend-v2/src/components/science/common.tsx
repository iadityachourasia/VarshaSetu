import type { ReactNode } from "react";
import type { DataSourceMode } from "@/lib/data-source";
import { DATA_SOURCE_LABEL } from "@/lib/data-source";
import { METRIC_DEFINITION } from "@/lib/metric-definitions";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { AlertTriangle, Inbox } from "lucide-react";
import { RetryButton } from "@/components/science/retry-button";

export function PageHeading({ title, subtitle, action }: { title: string; subtitle: string; action?: ReactNode }) {
  return <div className="page-heading"><div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>;
}

export function SectionHeading({ title, note, id }: { title: string; note?: string; id?: string }) {
  return <div className="section-heading" id={id}><h2>{title}</h2>{note ? <p>{note}</p> : null}</div>;
}

export { PageToc } from "./page-toc";

export function Metric({ label, value, detail, tone }: { label: string; value: string; detail?: string; tone?: "teal" | "amber" | "muted" }) {
  return <div className={`metric ${tone ? `metric-${tone}` : ""}`}><span className="metric-label">{label}</span><strong className="metric-value">{value}</strong>{detail ? <span className="metric-detail">{detail}</span> : null}</div>;
}

export function ErrorState({ message = "Scientific artifacts are unavailable. Start the verified historical API and try again.", retry = true }: { message?: string; retry?: boolean }) {
  return <div className="state-message state-message-error" role="alert"><span className="state-icon" aria-hidden="true"><AlertTriangle size={18} /></span><strong>Data unavailable</strong><p>{message}</p>{retry ? <RetryButton /> : null}</div>;
}

/** `action` is the next step a person can take (a link or a control); an empty state without one is a dead end. */
export function EmptyState({ message, action }: { message: string; action?: ReactNode }) {
  return <div className="state-message"><span className="state-icon" aria-hidden="true"><Inbox size={18} /></span><strong>Nothing to display</strong><p>{message}</p>{action ?? null}</div>;
}

export function LoadingState({ label = "Loading verified case", compact = false }: { label?: string; compact?: boolean }) {
  return <div className={compact ? "loading-state loading-state-compact" : "loading-state"} role="status" aria-label={label}><span className="skeleton-block" /><span className="skeleton-block" /><span className="skeleton-block" /><span className="sr-only">{label}</span></div>;
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

/** One canonical metric-abbreviation tooltip trigger (lib/metric-definitions.ts
 * is the single definition source -- no page writes its own). Base UI's
 * Trigger renders a real focusable element, so the definition is reachable
 * by keyboard, not only on hover. Falls back to plain text for an
 * unrecognized term rather than showing an empty tooltip. */
export function MetricTerm({ term }: { term: string }) {
  const definition = METRIC_DEFINITION[term];
  if (!definition) return <>{term}</>;
  return <Tooltip><TooltipTrigger className="metric-term">{term}</TooltipTrigger><TooltipContent>{definition}</TooltipContent></Tooltip>;
}
