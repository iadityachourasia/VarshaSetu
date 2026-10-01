import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse

# Ensure path resolution
sys.path.insert(0, os.path.dirname(__file__))

try:
    from backend.app.api.routes import router as api_router
    from backend.app.api.science import router as science_router
    from backend.app.api.operational import router as operational_router
    from backend.app.api.evidence import router as evidence_router
    from backend.app.api.zones import router as zones_router
except ModuleNotFoundError:
    from app.api.routes import router as api_router
    from app.api.science import router as science_router
    from app.api.operational import router as operational_router
    from app.api.evidence import router as evidence_router
    from app.api.zones import router as zones_router

app = FastAPI(
    title="VarshaSetu API",
    description=(
        "Scientific API for the VarshaSetu SIH26080 rainfall post-processing "
        "platform. Scientific inference is fail-closed until readiness blockers "
        "are resolved."
    ),
    version="0.1.0-phase0"
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "message": "VarshaSetu — SIH26080 Phase 0 status API",
        "documentation": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
