"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { RotateCw } from "lucide-react";

/** Asks every failed or active request on the page to run again. It changes no data and never fabricates a result: a request that fails again shows its error again. */
export function RetryButton() {
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const retry = async () => {
    setBusy(true);
    try { await client.refetchQueries({ type: "active" }); } finally { setBusy(false); }
  };
  return <button type="button" className="state-retry" onClick={retry} disabled={busy}><RotateCw size={14} aria-hidden="true" className={busy ? "state-retry-spin" : undefined} />{busy ? "Retrying…" : "Try again"}</button>;
}
