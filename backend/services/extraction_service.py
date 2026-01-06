"""
Extraction service for company search criteria.

This module handles the extraction of search criteria from user queries
using the OpenRouter API.
"""

import os
import json
from typing import Any, Dict, Optional
import requests

from sector_matcher import SectorMatcher

# ============================================================================
# Configuration
# ============================================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")

# ============================================================================
# System Prompt
# ============================================================================

SYSTEM_PROMPT = """Tu es un extracteur de contraintes pour un moteur de recherche d'entreprises françaises.

TA MISSION
-----------
À partir d'une requête utilisateur en français (souvent très libre : "je cherche...", "trouve-moi...", "peux-tu", etc.),
tu dois détecter les critères décrits dans la requête et renvoyer UNIQUEMENT un objet JSON décrivant ces critères.

Tu ne dois jamais expliquer ta réponse, ni ajouter de texte autour.
Réponds toujours par UN SEUL objet JSON bien formé.

FORMAT DE SORTIE
----------------
Tu dois répondre avec exactement la structure suivante :

{
  "localisation": {
    "present": true/false,
    "code_postal": string ou null,
    "departement": string ou null,
    "region": string ou null,
    "commune": string ou null
  },
  "activite": {
    "present": true/false,
    "libelle_secteur": string ou null,
    "activite_entreprise": string ou null
  },
  "taille_entreprise": {
    "present": true/false,
    "tranche_effectif": string ou null,
    "acronyme": string ou null
  },
  "criteres_financiers": {
    "present": true/false,
    "ca_plus_recent": number ou null,
    "resultat_net_plus_recent": number ou null,
    "rentabilite_plus_recente": number ou null
  },
  "criteres_juridiques": {
    "present": true/false,
    "categorie_juridique": string ou null,
    "siege_entreprise": "oui" ou "non" ou null,
    "date_creation_entreprise": string ou null,
    "capital": number ou null,
    "date_changement_dirigeant": string ou null,
    "nombre_etablissements": number ou null
  }
}

RÈGLES GÉNÉRALES
----------------
- Tu dois toujours renvoyer un JSON valide
- Si un critère n'est PAS demandé dans la requête, mets "present": false et tous les champs internes à null
- Si un critère est demandé, mets "present": true et remplis les champs que tu peux
- Ne JAMAIS inventer des valeurs précises quand elles ne sont pas présentes dans la requête
- Dates : format "YYYY-MM-DD"
- Nombres : retirer les espaces, "€", "k", "K", "M" (ex: "100 k€" -> 100000)
"""

# ============================================================================
# Singleton SectorMatcher
# ============================================================================

_sector_matcher: Optional[SectorMatcher] = None

def get_sector_matcher() -> SectorMatcher:
    """Get or create the sector matcher singleton."""
    global _sector_matcher
    if _sector_matcher is None:
        _sector_matcher = SectorMatcher()
    return _sector_matcher

# ============================================================================
# Helper Functions
# ============================================================================

def _clean_json_content(content: str) -> str:
    """Nettoie la réponse textuelle du modèle (code fences, texte parasite)."""
    cleaned = content.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # Extraire la partie entre le premier {/[ et le dernier }/]
    start_candidates = [idx for idx in (cleaned.find("{"), cleaned.find("[")) if idx != -1]
    if start_candidates:
        start = min(start_candidates)
        end_brace = cleaned.rfind("}")
        end_bracket = cleaned.rfind("]")
        end_candidates = [idx for idx in (end_brace, end_bracket) if idx != -1]
        if end_candidates:
            end = max(end_candidates)
            cleaned = cleaned[start : end + 1]

    return cleaned


def _normalize_extraction_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process extraction result to normalize libelle_secteur to exact reference values
    """
    if not isinstance(result, dict):
        return result

    # Normalize libelle_secteur
    activite = result.get("activite")
    if isinstance(activite, dict):
        libelle = activite.get("libelle_secteur")
        naf_code = activite.get("activite_entreprise")

        if naf_code is not None and libelle is not None:
            activite["libelle_secteur"] = None
        elif libelle is not None and isinstance(libelle, str):
            matcher = get_sector_matcher()
            matched = matcher.match(libelle, threshold=0.5)
            if matched:
                activite["libelle_secteur"] = matched

    # Enforce criteres_juridiques rules
    criteres_juridiques = result.get("criteres_juridiques")
    if isinstance(criteres_juridiques, dict):
        if criteres_juridiques.get("present") is False:
            criteres_juridiques["categorie_juridique"] = None
            criteres_juridiques["siege_entreprise"] = None
            criteres_juridiques["date_creation_entreprise"] = None
            criteres_juridiques["capital"] = None
            criteres_juridiques["date_changement_dirigeant"] = None
            criteres_juridiques["nombre_etablissements"] = None

    return result

# ============================================================================
# Exceptions
# ============================================================================

class OpenRouterExtractorError(Exception):
    """Erreur personnalisée pour l'extraction des critères via OpenRouter."""

# ============================================================================
# API Calls
# ============================================================================

def call_openrouter_chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Appelle l'API OpenRouter et renvoie la réponse JSON brute."""
    if not OPENROUTER_API_KEY:
        raise OpenRouterExtractorError(
            "OPENROUTER_API_KEY n'est pas définie dans les variables d'environnement."
        )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        url=OPENROUTER_API_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=60,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        raise OpenRouterExtractorError(
            f"Erreur HTTP OpenRouter ({response.status_code}): {response.text}"
        ) from e

    try:
        return response.json()
    except json.JSONDecodeError as e:
        raise OpenRouterExtractorError("Réponse OpenRouter non JSON.") from e


def extract_criteria(user_query: str) -> Dict[str, Any]:
    """
    Extrait les critères depuis une requête utilisateur via OpenRouter.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    payload: Dict[str, Any] = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
    }

    raw = call_openrouter_chat(payload)

    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise OpenRouterExtractorError(
            f"Format de réponse inattendu : {json.dumps(raw, ensure_ascii=False)}"
        ) from e

    try:
        result = json.loads(_clean_json_content(content))
    except json.JSONDecodeError as e:
        raise OpenRouterExtractorError(
            f"Le modèle n'a pas renvoyé un JSON valide : {content}"
        ) from e

    result = _normalize_extraction_result(result)

    return result
