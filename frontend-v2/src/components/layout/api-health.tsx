"use client";

import { useQuery } from "@tanstack/react-query";

type Health = "checking" | "verified" | "integrity" | "unreachable";

async function checkHealth(): Promise<Exclude<Health, "checking">> {
  try {
    const response = await fetch("/api/science/status", { cache: "no-store", signal: AbortSignal.timeout(8000) });
    if (response.ok) return "verified";
    return response.status === 503 ? "integrity" : "unreachable";
  } catch {
    return "unreachable";
  }
}

const TEXT: Record<Health, { label: string; detail: string }> = {
  checking: { label: "Checking data", detail: "Checking the verified scientific API" },
  verified: { label: "Evidence verified", detail: "The scientific API answered and its stored artifacts passed their hash checks" },
  integrity: { label: "Integrity check failed", detail: "A stored artifact failed its hash check; the API refuses to serve scientific values until it is fixed" },
  unreachable: { label: "API unreachable", detail: "The scientific API did not answer; pages show a stated error or a labelled static fallback, never invented numbers" },
};

/** A quiet status light in the header. It reports only what the API itself said, and rechecks every few minutes so a failure after the page loaded is not hidden. */
export function ApiHealth() {
  const query = useQuery({ queryKey: ["api-health"], queryFn: checkHealth, refetchInterval: 3 * 60_000, staleTime: 60_000, retry: false });
  const state: Health = query.data ?? "checking";
  const { label, detail } = TEXT[state];
  return <span className={`api-health api-health-${state}`} role="status" title={detail} data-testid="api-health"><i aria-hidden="true" /><span>{label}</span><span className="sr-only">. {detail}</span></span>;
}
