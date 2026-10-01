"""Explicit CORS policy: named origins only, no credentials, read-only methods.

The production frontend reaches the API through a same-origin proxy (Vercel rewrites), so browsers do not call this API
cross-origin in production; the list exists for local development and for a directly hosted frontend. Override with
CORS_ALLOW_ORIGINS (comma-separated). A wildcard is refused: it would re-open the policy this module closes.
"""

from __future__ import annotations

import os

DEFAULT_ORIGINS = (
    "https://varshasetu.vercel.app",
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:3100", "http://127.0.0.1:3100",
    "http://localhost:5173", "http://127.0.0.1:5173",
)
ALLOWED_METHODS = ("GET", "HEAD", "OPTIONS")
ALLOWED_HEADERS = ("Accept", "Content-Type")


def allowed_origins(environ: dict[str, str] | None = None) -> list[str]:
    environ = os.environ if environ is None else environ
    configured = environ.get("CORS_ALLOW_ORIGINS")
    if configured is None:
        return list(DEFAULT_ORIGINS)
    origins = [item.strip().rstrip("/") for item in configured.split(",") if item.strip()]
    if "*" in origins or not origins:
        raise ValueError("CORS_ALLOW_ORIGINS must name explicit origins; a wildcard or an empty list is not allowed")
    return origins
