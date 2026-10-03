"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { MapSettingsProvider } from "@/components/maps/map-settings";
import { ToastProvider } from "@/components/ui/toast";
import { MotionRoot } from "@/components/ui/motion-root";
import { MapEmphasisProvider } from "@/components/maps/map-emphasis";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 15 * 60_000, retry: 1, refetchOnWindowFocus: false } },
  }));
  return <QueryClientProvider client={client}><TooltipProvider><MapSettingsProvider><ToastProvider><MapEmphasisProvider><MotionRoot />{children}</MapEmphasisProvider></ToastProvider></MapSettingsProvider></TooltipProvider></QueryClientProvider>;
}
