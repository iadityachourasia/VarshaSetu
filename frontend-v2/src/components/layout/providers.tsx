"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { MapSettingsProvider } from "@/components/maps/map-settings";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 15 * 60_000, retry: 1, refetchOnWindowFocus: false } },
  }));
  return <QueryClientProvider client={client}><TooltipProvider><MapSettingsProvider>{children}</MapSettingsProvider></TooltipProvider></QueryClientProvider>;
}
