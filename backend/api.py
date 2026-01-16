"""
API FastAPI pour l'extraction de critères de recherche d'entreprises

Stateless chat API with file-based activity embeddings.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

# ============================================================================
# Configuration et chargement de l'environnement
# IMPORTANT: Must be done BEFORE importing modules that read env vars at import time
# ============================================================================

def load_env_from_file(env_path: Optional[str] = None, override: bool = True) -> None:
    """
    Charge les variables depuis un fichier .env (clé=valeur par ligne).
    Si override=True, écrase les variables existantes (priorité au .env local).
    """
    candidate_paths = []
    module_dir = Path(__file__).resolve().parent
    candidate_paths.append(module_dir / ".env")
    if env_path:
        candidate_paths.insert(0, Path(env_path))
    candidate_paths.append(Path.cwd() / ".env")

    for path in candidate_paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key and (override or key not in os.environ):
                os.environ[key] = value
        break


# Load .env BEFORE importing other modules that depend on env vars
load_env_from_file()

# Now import modules
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from routers import chat_router
from services.extraction_service import extract_criteria, OpenRouterExtractorError
from services.activity_matcher import get_activity_matcher
from services.location_matcher import get_location_matcher

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Company Search Criteria Extractor",
    description="API pour extraire les critères de recherche d'entreprises depuis une requête en langage naturel",
    version="2.0.0",
    redirect_slashes=False,
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Include Routers
# ============================================================================

app.include_router(chat_router.router)

# ============================================================================
# Models Pydantic
# ============================================================================

class ExtractRequest(BaseModel):
    query: str

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Je cherche des PME en Ile-de-France dans la restauration avec un CA supérieur à 1M€"
            }
        }


class ExtractResponse(BaseModel):
    query: str
    result: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    version: str
    embeddings: str
    locations: str
    timestamp: datetime


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Company Search Criteria Extractor API",
        "version": "2.0.0"
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint with component status"""
    # Check activity matcher
    try:
        matcher = await get_activity_matcher()
        if matcher._initialized:
            embeddings_status = "file-based"
        else:
            embeddings_status = "not initialized"
    except Exception as e:
        embeddings_status = f"error: {str(e)}"

    # Check location matcher
    try:
        loc_matcher = get_location_matcher()
        if loc_matcher._initialized:
            locations_status = f"{len(loc_matcher.communes)} communes, {len(loc_matcher.departements)} deps, {len(loc_matcher.regions)} regions"
        else:
            locations_status = "not initialized"
    except Exception as e:
        locations_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy",
        version="2.0.0",
        embeddings=embeddings_status,
        locations=locations_status,
        timestamp=datetime.utcnow()
    )


@app.post("/extract", response_model=ExtractResponse)
async def extract_endpoint(payload: ExtractRequest) -> ExtractResponse:
    """
    Extrait les critères de recherche depuis une requête en langage naturel.
    Single-shot extraction without conversation context.
    """
    try:
        result = extract_criteria(payload.query)
    except OpenRouterExtractorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Erreur inattendue lors de l'extraction."
        ) from exc

    return ExtractResponse(query=payload.query, result=result)


# ============================================================================
# Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize matchers on startup"""
    print("🚀 Starting Company Search API...")

    # Initialize activity matcher (file-based embeddings)
    print("📊 Initializing activity matcher...")
    activity_matcher = await get_activity_matcher()
    if activity_matcher._initialized:
        print("✅ Activity matcher ready (file-based embeddings)")
    else:
        print("⚠️  Activity matcher not initialized - activity matching will be disabled")

    # Initialize location matcher
    print("📍 Initializing location matcher...")
    location_matcher = get_location_matcher()
    if location_matcher._initialized:
        print("✅ Location matcher ready")
    else:
        print("⚠️  Location matcher not initialized - location matching will be disabled")

    print("✅ API ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    print("🛑 Shutting down Company Search API...")
    print("✅ Shutdown complete")


# ============================================================================
# Main - pour lancement local
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
