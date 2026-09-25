import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Database, ShieldAlert } from 'lucide-react';
import { fetchSystemStatus } from './services/api';
import { SystemStatus } from './types';


export function App() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetchSystemStatus().then(setStatus).catch((reason: Error) => setError(reason.message));
  }, []);

  return (
    <div className="min-h-screen bg-slate-100 text-slate-950">
      <header className="border-b border-slate-300 bg-white px-6 py-5 shadow-sm">
        <div className="mx-auto max-w-6xl">
          <h1 className="text-3xl font-black tracking-tight">VarshaSetu</h1>
          <p className="mt-1 text-base font-extrabold text-slate-800">
            Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
          </p>
          <p className="mt-1 text-sm font-bold text-slate-600">
            Bridging Raw NWP Forecasts and Actionable Rainfall Intelligence
          </p>
          <p className="mt-2 text-sm font-bold text-slate-600">
            Phase 0 repository stabilization — scientific outputs are disabled until their evidence is reproducible.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 p-6">
        {error && (
          <div className="rounded-2xl border border-rose-300 bg-rose-50 p-6 text-rose-950">
            <div className="flex items-center gap-3 font-black">
              <ShieldAlert className="h-6 w-6" /> Backend status unavailable
            </div>
            <p className="mt-2 text-sm font-semibold">{error}</p>
          </div>
        )}

        {!status && !error && (
          <div className="rounded-2xl border border-slate-300 bg-white p-10 text-center font-bold text-slate-600">
            Loading verified repository status…
          </div>
        )}

        {status && (
          <>
            <section className="rounded-2xl border border-amber-300 bg-amber-50 p-6 shadow-sm">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-6 w-6 shrink-0 text-amber-700" />
                <div>
                  <h2 className="text-xl font-black">Scientific readiness gate: blocked</h2>
                  <p className="mt-1 text-sm font-semibold text-amber-950">
                    This is not an operational forecast. Historical model results, probabilities, alerts, and verification metrics are intentionally unavailable.
                  </p>
                </div>
              </div>
            </section>

            <section className="grid gap-6 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-300 bg-white p-6 shadow-sm">
                <h2 className="flex items-center gap-2 text-lg font-black">
                  <Database className="h-5 w-5 text-indigo-700" /> Checked-in dataset identity
                </h2>
                <dl className="mt-4 space-y-3 text-sm">
                  <div><dt className="font-bold text-slate-500">Dataset</dt><dd className="font-mono font-bold">{status.current_dataset.filename}</dd></div>
                  <div><dt className="font-bold text-slate-500">Rows / source columns</dt><dd className="font-bold">{status.current_dataset.rows.toLocaleString()} / {status.current_dataset.source_columns}</dd></div>
                  <div><dt className="font-bold text-slate-500">SHA-256</dt><dd className="break-all font-mono text-xs font-bold">{status.current_dataset.sha256}</dd></div>
                  <div><dt className="font-bold text-slate-500">Scientific provenance</dt><dd className="font-black uppercase text-rose-700">{status.current_dataset.provenance_status}</dd></div>
                </dl>
              </div>

              <div className="rounded-2xl border border-slate-300 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-black">Legacy artifact status</h2>
                <p className="mt-3 text-sm font-semibold text-slate-700">
                  {status.legacy_report.present
                    ? 'A legacy report is retained for audit evidence but quarantined because its source dataset is absent and its checksum differs.'
                    : 'No legacy report is present.'}
                </p>
                {status.legacy_report.sha256 && (
                  <p className="mt-3 break-all font-mono text-xs text-slate-600">{status.legacy_report.sha256}</p>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-rose-300 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-black">Unresolved blockers</h2>
              <ul className="mt-4 space-y-3">
                {status.scientific_readiness.blockers.map((blocker) => (
                  <li key={blocker} className="flex items-start gap-2 text-sm font-semibold text-slate-800">
                    <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-700" /> {blocker}
                  </li>
                ))}
              </ul>
            </section>

            <section className="rounded-2xl border border-emerald-300 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-black">Phase 0 controls now enforced</h2>
              <ul className="mt-4 space-y-3">
                {status.scientific_readiness.resolved_controls.map((control) => (
                  <li key={control} className="flex items-start gap-2 text-sm font-semibold text-slate-800">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" /> {control}
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
