"""AutoPatch API — orchestration brain for the self-healing demo."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.runs import router as runs_router

# backend/.env — keep keys out of the repo
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(
    title="AutoPatch",
    description="Autonomous, sandboxed code remediation engine",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs_router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    has_key = "yes" if os.getenv("GEMINI_API_KEY") else "no"
    return {"status": "ok", "gemini_key_configured": has_key}
