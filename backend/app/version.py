"""Single source of the API version and the deployed commit (served by /api/health and the OpenAPI document)."""

from __future__ import annotations

import os

API_VERSION = "0.2.0"
# Render sets RENDER_GIT_COMMIT at runtime; the other names cover local and CI runs. Never shell out to git.
_COMMIT_VARIABLES = ("RENDER_GIT_COMMIT", "GIT_COMMIT", "SOURCE_VERSION", "GITHUB_SHA")


def deployed_commit(environ: dict[str, str] | None = None) -> str:
    environ = os.environ if environ is None else environ
    for name in _COMMIT_VARIABLES:
        value = environ.get(name, "").strip()
        if value:
            return value[:40]
    return "unknown"
