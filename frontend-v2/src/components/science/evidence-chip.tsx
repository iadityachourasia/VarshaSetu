import { shortEvidenceLabel } from "@/lib/evidence-chip";

/**
 * The evidence role of a population as a compact chip. The short text is for scanning; the full mandatory label stays in the document for assistive
 * technology and as a tooltip, so a screen reader and any text search still find exactly the governed wording. An unrecognised label is shown unchanged.
 */
export function EvidenceChip({ label }: { label: string }) {
  const short = shortEvidenceLabel(label);
  if (!short) return <>{label}</>;
  return <span className={`evidence-chip evidence-chip-${short.tone}`} title={label}><span aria-hidden="true">{short.text}</span><span className="sr-only">{label}</span></span>;
}
