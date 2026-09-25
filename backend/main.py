import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure path resolution
sys.path.insert(0, os.path.dirname(__file__))

try:
    from backend.app.api.routes import router as api_router
    from backend.app.api.science import router as science_router
except ModuleNotFoundError:
    from app.api.routes import router as api_router
    from app.api.science import router as science_router

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

@app.get("/")
def root():
    return {
        "message": "VarshaSetu — SIH26080 Phase 0 status API",
        "documentation": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
