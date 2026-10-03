// A short, scannable form of the mandatory evidence labels (EVIDENCE_LABELS in backend/app/api/evidence.py). The full label is never dropped: the chip
// component keeps it as the accessible name and as a tooltip, and every panel banner still prints it in full. Anything not recognised returns null so
// the caller shows the label unchanged rather than guessing a shorter claim.

export type EvidenceTone = "posthoc" | "development" | "training" | "independent" | "sealed" | "confirmatory";
export type ShortEvidence = { text: string; tone: EvidenceTone };

const YEARS = /\b(20\d{2}(?:-20\d{2})?)\b/;

export function shortEvidenceLabel(label: string): ShortEvidence | null {
  const years = label.match(YEARS)?.[1];
  const withYears = (prefix: string) => (years ? `${prefix} · ${years}` : prefix);
  if (/^POST-HOC EXPLORATORY ANALYSIS/i.test(label)) return { text: withYears("Post-hoc"), tone: "posthoc" };
  if (/^POST-UNSEAL SEALED TEST/i.test(label)) return { text: withYears("Sealed test"), tone: "sealed" };
  if (/^CONFIRMATORY TEST/i.test(label)) return { text: withYears("Confirmatory"), tone: "confirmatory" };
  if (/^INDEPENDENT TEST/i.test(label)) return { text: "Independent test · first use", tone: "independent" };
  if (/development evidence|development year/i.test(label)) return { text: withYears("Development"), tone: "development" };
  if (/training year/i.test(label)) return { text: withYears("Training"), tone: "training" };
  return null;
}
