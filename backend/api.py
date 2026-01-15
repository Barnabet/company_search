"""
API FastAPI pour l'extraction de critères de recherche d'entreprises
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import requests
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db, init_db, close_db
from schemas import HealthCheck
from routers import conversation_router
from services.extraction_service import extract_criteria, OpenRouterExtractorError

# ============================================================================
# Configuration et chargement de l'environnement
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


load_env_from_file()

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Company Search Criteria Extractor",
    description="API pour extraire les critères de recherche d'entreprises depuis une requête en langage naturel",
    version="1.0.0",
    redirect_slashes=False,  # Disable automatic redirect to avoid CORS issues
)

# Configuration CORS pour permettre l'accès depuis le frontend Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Include Routers
# ============================================================================

app.include_router(conversation_router.router)

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


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Endpoint de santé"""
    return {
        "status": "ok",
        "message": "Company Search Criteria Extractor API",
        "version": "1.0.0"
    }


@app.get("/health", response_model=HealthCheck)
async def health(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint with database connection verification
    """
    db_status = "disconnected"
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        print(f"Database health check failed: {e}")
        db_status = f"error: {str(e)}"

    return HealthCheck(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        timestamp=datetime.utcnow()
    )


@app.post("/extract", response_model=ExtractResponse)
async def extract_endpoint(payload: ExtractRequest) -> ExtractResponse:
    """
    Extrait les critères de recherche depuis une requête en langage naturel.
    
    Args:
        payload: Objet contenant la requête utilisateur
    
    Returns:
        ExtractResponse: La requête originale et les critères extraits
    
    Raises:
        HTTPException: Si une erreur survient pendant l'extraction
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
    """Initialize database on application startup"""
    print("🚀 Starting Company Search API...")
    print("📊 Initializing database connection...")
    # Create tables if they don't exist (fallback when migrations don't run at build time)
    await init_db()
    print("✅ Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connections on shutdown"""
    print("🛑 Shutting down Company Search API...")
    await close_db()
    print("✅ Database connections closed")


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


