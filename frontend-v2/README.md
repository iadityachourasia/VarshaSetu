# VarshaSetu historical scientific frontend

This independent Next.js frontend serves the frozen, read-only Phase 2B/2C
science API. It is the primary local SIH demo frontend after the Phase 3C
recording gate. The legacy Vite frontend remains in `../frontend/`.

From the repository root on Windows, run
`& .\scripts\demo\start-demo.ps1`, open
`http://127.0.0.1:3200`, and run
`& .\scripts\demo\preflight-demo.ps1` immediately before recording.
Stop only launcher-owned services with `& .\scripts\demo\stop-demo.ps1`.
See `../docs/75_DEMO_LAUNCH_AND_RECOVERY.md` for prerequisites and recovery.

Local verification from this directory uses the pinned Node dependencies:

```powershell
node node_modules/typescript/bin/tsc --noEmit
node node_modules/eslint/bin/eslint.js .
node node_modules/vitest/vitest.mjs run
node node_modules/next/dist/bin/next build
node node_modules/@playwright/test/cli.js test --config=playwright.production.config.ts
```

The normal `npm` scripts are equivalent where npm is installed correctly.
Production tests use ports 8000 and 3200, not a Next development server.
The browser makes only same-origin `/api/science` requests for scientific
values; OpenFreeMap is a separate public geographic basemap dependency.
The offline fallback has only pinned district geometry. This is a historical
prototype, not a live or operational forecast product.
