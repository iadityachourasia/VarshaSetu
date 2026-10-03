"use client";

import { useToast } from "@/components/ui/toast";

/** The shortened form of a SHA-256 that is printed beside evidence: it copies the full digest on click, so a reader can paste it into a checker. */
export function HashChip({ hash, digits = 12 }: { hash: string; digits?: number }) {
  const toast = useToast();
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(hash);
      toast("Full SHA-256 copied");
    } catch {
      toast("Copy is blocked in this browser — select the digest manually");
    }
  };
  return <button type="button" className="hash-chip" onClick={copy} title={`Copy the full SHA-256 (${hash.length} characters)`} aria-label={`Copy full SHA-256 starting ${hash.slice(0, digits)}`} data-hash={hash}>{hash.slice(0, digits)}…</button>;
}
