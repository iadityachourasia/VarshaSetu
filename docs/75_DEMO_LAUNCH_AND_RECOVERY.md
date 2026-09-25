# Phase 3C — Local production demo launch and recovery

Use PowerShell on the Windows 11 development machine from the repository root.
Keep AC power and cooling available. The frontend is `frontend-v2/`; the
legacy `frontend/` is preserved. No launcher step trains, downloads, decodes,
reconstructs or writes scientific artifacts.

## Before recording

```powershell
& .\scripts\demo\start-demo.ps1
& .\scripts\demo\preflight-demo.ps1
```

Open `http://127.0.0.1:3200`. The launcher requires the project `.venv`,
Node.js, Phase 2C manifest and existing `frontend-v2/.next/BUILD_ID`.
If the build is missing, run `node node_modules/next/dist/bin/next build`
from `frontend-v2/` after the normal tests; the launcher never builds
or alters scientific data. Backend binds to 127.0.0.1:8000 and the Next
production server to 127.0.0.1:3200. `SCIENCE_API_URL` is a server-only
override, normally `http://127.0.0.1:8000`.

Preflight checks the manifest sidecar, readiness, official primary case,
model comparison, rainfall, regime, extreme probabilities, FSS, districts,
geometry, verification, frontend and proxy. It reports the official
OpenFreeMap Dark style separately. If the shell sandbox blocks outbound
network traffic, the online result is inconclusive there; verify in the
recording browser. The browser must load a real vector tile and labels before
the geographic shot. Scientific readiness is independent of that public host.

The launcher records only process IDs it starts in
`scripts/demo/.runtime/owned-processes.json`, with start timestamps. It
reuses healthy services and refuses unknown port occupants. Logs stay in that
ignored runtime directory. Repeated launch is safe. To stop only processes
started by this launcher:

```powershell
& .\scripts\demo\stop-demo.ps1
```

The stop script verifies PID start time and executable path; it leaves reused
or unrelated services untouched. If startup fails, inspect the two runtime
logs and the named failed preflight check. Do not clear or regenerate the
scientific cache as a troubleshooting shortcut.

## Recovery and rollback

If public tiles fail, present the explicitly labeled offline district
fallback and retry only after network restoration; do not hide attribution.
If the production frontend fails, stop its launcher-owned process, rebuild
the frontend after fixing the code, and rerun full Playwright production
tests. The legacy Vite frontend remains in `frontend/` and can be run on
its own historical port using its existing package scripts. It is not the
Phase 3C scientific demo and its legacy scientific API lock stays in place.
This rollback changes only the local demo URL; it does not change backend
science. The workspace lacks accessible Git metadata, so do not promise a
Git-based rollback.
