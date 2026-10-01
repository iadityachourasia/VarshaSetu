import logging
import os
import sys
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse

# Ensure path resolution
sys.path.insert(0, os.path.dirname(__file__))

try:
    from backend.app.core.cors import ALLOWED_HEADERS, ALLOWED_METHODS, allowed_origins
    from backend.app.version import API_VERSION, deployed_commit
    from backend.app.api.routes import router as api_router
    from backend.app.api.science import router as science_router
    from backend.app.api.operational import router as operational_router
    from backend.app.api.evidence import router as evidence_router
    from backend.app.api.zones import router as zones_router
except ModuleNotFoundError:
    from app.core.cors import ALLOWED_HEADERS, ALLOWED_METHODS, allowed_origins
    from app.version import API_VERSION, deployed_commit
    from app.api.routes import router as api_router
    from app.api.science import router as science_router
    from app.api.operational import router as operational_router
    from app.api.evidence import router as evidence_router
    from app.api.zones import router as zones_router

def warm_evidence_caches() -> dict[str, str]:
    """Pre-verify and cache the small hash-chained evidence files so the first visitor does not pay for it.

    Best effort: a failure is recorded and logged, never raised, and never changes what a request later returns
    (an integrity failure is still reported by the request itself).
    """
    try:
        from backend.app.api import evidence, zones
    except ModuleNotFoundError:
        from app.api import evidence, zones
    steps = {"evidence_manifest": evidence._manifest, "ps_coverage": evidence._coverage, "zone_chain": zones._chain,
             "district_manifest": evidence._district_manifest}
    outcome: dict[str, str] = {}
    for name, step in steps.items():
        try:
            step()
            outcome[name] = "ok"
        except Exception as error:  # noqa: BLE001 - best effort by design
            outcome[name] = f"failed: {type(error).__name__}"
            logging.getLogger("varshasetu.warmup").warning("warm-up step %s failed: %s", name, error)
    return outcome


@asynccontextmanager
async def lifespan(_: FastAPI):
    threading.Thread(target=warm_evidence_caches, name="evidence-warmup", daemon=True).start()
    yield


app = FastAPI(
    title="VarshaSetu API",
    description=(
        "Scientific API for the VarshaSetu SIH26080 rainfall post-processing "
        "platform. Scientific inference is fail-closed until readiness blockers "
        "are resolved."
    ),
    version=API_VERSION,
    lifespan=lifespan,
)

# Explicit origins, no credentials (the API sets no cookies), read-only methods; see app/core/cors.py.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=list(ALLOWED_METHODS),
    allow_headers=list(ALLOWED_HEADERS),
)

app.include_router(api_router, prefix="/api")
app.include_router(science_router, prefix="/api")
app.include_router(operational_router, prefix="/api")
app.include_router(evidence_router, prefix="/api")
app.include_router(zones_router, prefix="/api")


@app.exception_handler(HTTPException)
async def structured_science_error_handler(request: Request, exc: HTTPException):
    """Flatten a dict `detail={"code": ..., "detail": ...}` (used only by the
    new /api/science/operational/* router) into a top-level {code, detail}
    body. A plain string `detail` (every other existing route, unchanged)
    falls through to FastAPI's default {"detail": "..."} handler exactly as
    before -- this is purely additive and does not change any existing
    response body."""
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)
    return await http_exception_handler(request, exc)

@app.get("/")
def root():
    return {
        "message": "VarshaSetu science API (read-only, hash-verified frozen artifacts)",
        "version": API_VERSION,
        "documentation": "/docs",
        "health": "/api/health",
        "science_status": "/api/science/status",
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
