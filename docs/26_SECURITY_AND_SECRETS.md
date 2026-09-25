# Security & Secrets

## Current priority

Security is important, but it must not displace scientific PS work during early SIH development.

## Mandatory basics

- Never commit API keys/passwords.
- Keep provider credentials server-side.
- Add `.env` to `.gitignore`.
- Provide `.env.example` containing names only.
- Restrict deployed CORS origins.
- Validate API input.
- Avoid arbitrary file-path input from clients.
- Keep downloaded scientific files outside publicly served frontend assets unless intended.

## Dataset access

Some meteorological products may have terms of use or require accounts.

Document:
- provider,
- access terms,
- whether redistribution is allowed.

Do not package restricted source files in a public repository without permission.

## Model artifacts

Treat artifacts as versioned software assets.

Do not load untrusted arbitrary pickle/joblib files supplied by users.

## Frontend

No:
- data-provider tokens,
- object-storage secret keys,
- backend secrets.

## Future production

If user accounts become necessary:
- implement real backend auth,
- do not retain the current simulated UI auth as if secure.

Auth is not Phase 0/1 scientific priority unless required by deployment.
