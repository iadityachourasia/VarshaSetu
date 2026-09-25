import React from 'react';
import { ShieldAlert } from 'lucide-react';


export const ScientificOutputUnavailable: React.FC<{ title: string }> = ({ title }) => (
  <div className="rounded-2xl border border-amber-300 bg-amber-50 p-6 text-amber-950 shadow-sm">
    <h2 className="flex items-center gap-2 text-lg font-black">
      <ShieldAlert className="h-5 w-5" /> {title}
    </h2>
    <p className="mt-2 text-sm font-semibold">
      Not available during Phase 0 stabilization. The configured dataset and legacy artifacts do not share a reproducible scientific identity.
    </p>
  </div>
);
