import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { shortEvidenceLabel } from "./evidence-chip";

// The governed labels, read from the API source so a new or reworded label cannot silently fall out of the chip mapping.
const source = readFileSync(path.resolve(__dirname, "../../../backend/app/api/evidence.py"), "utf8");
const labels = [...source.slice(source.indexOf("EVIDENCE_LABELS"), source.indexOf("CAVEATS = [")).matchAll(/:\s*\n?\s*"([^"]{12,})"/g)].map((m) => m[1]);

describe("short evidence labels", () => {
  it("finds the governed labels in the API source", () => {
    expect(labels.length).toBeGreaterThanOrEqual(14);
  });
  it("gives every governed label a chip, so none is shown as an unstyled long sentence", () => {
    const unmatched = labels.filter((label) => shortEvidenceLabel(label) === null);
    expect(unmatched, unmatched.join(" | ")).toEqual([]);
  });
  it("never states more than the label does", () => {
    expect(shortEvidenceLabel("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST")).toEqual({ text: "Post-hoc · 2025", tone: "posthoc" });
    expect(shortEvidenceLabel("2024 validation/selection year: development evidence")).toEqual({ text: "Development · 2024", tone: "development" });
    expect(shortEvidenceLabel("POST-UNSEAL SEALED TEST 2014-2016: first use of these years")).toEqual({ text: "Sealed test · 2014-2016", tone: "sealed" });
    expect(shortEvidenceLabel("INDEPENDENT TEST: first use of this year")).toEqual({ text: "Independent test · first use", tone: "independent" });
  });
  it("leaves an unrecognised label alone instead of guessing", () => {
    expect(shortEvidenceLabel("Some new kind of evidence")).toBeNull();
  });
});
