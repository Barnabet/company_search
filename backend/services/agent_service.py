"""
Agent service for intelligent conversation management.

Flow:
1. LLM extracts criteria from user query (or rejects if too vague)
2. API returns company count for extracted criteria
3. If count > 500: ask refinement question
4. If count <= 500: deliver results
"""

import json
import os
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from models import Message

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")


@dataclass
class AgentResponse:
    """Response from the agent processing"""
    action: str  # "extract", "reject", or "refine"
    message: str  # Message to display to user
    extraction_result: Optional[Dict[str, Any]] = None  # Extracted criteria if action="extract"
    company_count: Optional[int] = None  # Number of matching companies (from API)
    api_result: Optional[Dict[str, Any]] = None  # Full API response data
    naf_codes: Optional[List[str]] = None  # Matched NAF codes from activity matcher


# ============================================================================
# Combined Agent Prompt - Decision + Extraction in ONE call
# ============================================================================

AGENT_SYSTEM_PROMPT = """Tu es un agent intelligent pour rechercher des entreprises françaises.

MISSION
-------
Extrais les critères de recherche de la requête utilisateur.
Si la requête est trop vague (aucun critère exploitable), rejette-la.

CRITÈRES EXPLOITABLES
---------------------
- Secteur/activité : restauration, informatique, BTP, santé, conseil, industrie...
- Localisation : région, département, ville, code postal
- Critères financiers : CA, résultat net, rentabilité avec montant
- Taille : TPE/PME/ETI/GE ou nombre de salariés

REQUÊTES TROP VAGUES (à rejeter)
--------------------------------
- "bonjour", "aide-moi", "help"
- "je cherche une entreprise" (sans aucun critère)
- Questions hors-sujet (météo, recettes, etc.)

FORMAT DE SORTIE JSON
---------------------
Si la requête contient AU MOINS UN critère exploitable :
{
  "action": "extract",
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
    "tranche_effectif": array of strings ou null,
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
    "siege_entreprise": string ou null,
    "date_creation_entreprise": string ou null,
    "capital": number ou null,
    "date_changement_dirigeant": string ou null,
    "nombre_etablissements": number ou null
  }
}

Si la requête est TROP VAGUE (aucun critère) :
{
  "action": "reject",
  "message": "Message expliquant ce que l'utilisateur peut rechercher"
}

RÈGLES D'EXTRACTION
-------------------
- libelle_secteur : reprendre le terme utilisé (restauration, informatique...)
- activite_entreprise : code NAF UNIQUEMENT si explicitement mentionné, sinon null
- region : liste autorisée = Ile-de-France, Bretagne, Normandie, Occitanie, etc.
- Ne jamais inventer de valeurs non mentionnées

TRANCHES D'EFFECTIF INSEE
-------------------------
A) ACRONYME → TRANCHES
   - MIC/TPE → ["0 salarie", "1 ou 2 salaries", "3 a 5 salaries", "6 a 9 salaries"]
   - PME → ["10 a 19 salaries", "20 a 49 salaries", "50 a 99 salaries", "100 a 199 salaries", "200 a 249 salaries"]
   - ETI → ["250 a 499 salaries", "500 a 999 salaries", "1 000 a 1 999 salaries", "2 000 a 4 999 salaries"]
   - GE → ["5 000 a 9 999 salaries", "10 000 salaries et plus"]

B) NOMBRE → ACRONYME
   - 0-9 salariés → acronyme = "TPE"
   - 10-249 salariés → acronyme = "PME"
   - 250-4999 salariés → acronyme = "ETI"
   - 5000+ salariés → acronyme = "GE"

IMPORTANT : tranche_effectif doit être un ARRAY de strings.

Réponds UNIQUEMENT avec le JSON, sans texte autour.
"""


class AgentService:
    """Service for conversational AI agent logic - Simplified version"""

    @staticmethod
    def _call_llm(messages: List[Dict[str, str]], temperature: float = 0.0) -> str:
        """
        Call OpenRouter LLM.

        Args:
            messages: List of message dicts with role and content
            temperature: Temperature for generation

        Returns:
            str: LLM response content
        """
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set")

        payload: Dict[str, Any] = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

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

        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _format_conversation(messages: List[Message]) -> str:
        """Format conversation history for context."""
        lines = []
        for msg in messages:
            role_label = "Utilisateur" if msg.role.value == "user" else "Agent"
            lines.append(f"{role_label}: {msg.content}")
        return "\n".join(lines)

    @staticmethod
    def _clean_json(content: str) -> str:
        """Clean JSON response from LLM."""
        cleaned = content.strip()

        # Remove markdown code blocks
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        # Extract JSON object
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start:end + 1]

        return cleaned

    @staticmethod
    async def process_message(messages: List[Message]) -> AgentResponse:
        """
        Process user message(s) and extract search criteria.

        ONE LLM call that:
        1. Analyzes the conversation
        2. Extracts criteria OR rejects if too vague

        Args:
            messages: Conversation history

        Returns:
            AgentResponse: Action (extract/reject) with result or message
        """
        # Build conversation context
        if len(messages) == 1:
            user_content = messages[0].content
        else:
            # Multi-turn: include conversation history
            conversation_text = AgentService._format_conversation(messages)
            user_content = f"""CONVERSATION:
{conversation_text}

Extrais les critères de recherche de la conversation complète."""

        # Single LLM call
        llm_messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        try:
            response = AgentService._call_llm(llm_messages)
            data = json.loads(AgentService._clean_json(response))

            action = data.get("action", "reject")

            if action == "extract":
                # Build extraction result (remove "action" key)
                extraction = {k: v for k, v in data.items() if k != "action"}
                return AgentResponse(
                    action="extract",
                    message="Recherche en cours...",
                    extraction_result=extraction,
                )
            else:
                # Query too vague - rejected
                message = data.get("message", "Pouvez-vous préciser votre recherche ? (secteur d'activité, localisation, taille...)")
                return AgentResponse(
                    action="reject",
                    message=message,
                    extraction_result=None,
                )

        except Exception as e:
            print(f"Agent processing failed: {e}")
            # Fallback: reject
            return AgentResponse(
                action="reject",
                message="Pouvez-vous préciser votre recherche ? (secteur d'activité, localisation, taille...)",
                extraction_result=None,
            )

    @staticmethod
    async def process_with_api(
        extraction_result: Dict[str, Any],
        refinement_round: int = 1
    ) -> AgentResponse:
        """
        Process extraction result through external company API.

        1. Match activities to NAF codes using embeddings
        2. Transform to API format
        3. Call external API for company count
        4. Decide: deliver results or ask for refinement

        Args:
            extraction_result: Extraction result from process_message
            refinement_round: Current refinement round (1-3)

        Returns:
            AgentResponse with API results or refinement question
        """
        # Import services here to avoid circular imports
        from services.activity_matcher import get_activity_matcher
        from services.api_transformer import transform_extraction_to_api_request
        from services.company_api_client import get_company_api_client, CompanyAPIError
        from services.refinement_service import get_refinement_service

        naf_codes = []
        api_result = None
        company_count = 0

        try:
            # Step 1: Match activities to NAF codes using embeddings
            activity_matcher = get_activity_matcher()
            activite = extraction_result.get("activite", {})
            activity_query = activite.get("libelle_secteur") or activite.get("activite_entreprise")

            if activity_query:
                naf_codes = activity_matcher.get_naf_codes_for_query(activity_query, top_k=3)
                print(f"[Agent] Activity '{activity_query}' matched to NAF codes: {naf_codes}")

            # Step 2: Transform to API format
            api_request = transform_extraction_to_api_request(extraction_result, naf_codes)
            print(f"[Agent] API request: {json.dumps(api_request, ensure_ascii=False)}")

            # Step 3: Call external API
            api_client = get_company_api_client()
            api_response = api_client.count_companies(api_request)

            company_count = api_response.count
            api_result = api_response.data
            print(f"[Agent] API returned {company_count} companies")

        except CompanyAPIError as e:
            print(f"[Agent] API error: {e}")
            # Return extraction result with error message
            return AgentResponse(
                action="extract",
                message=f"Critères extraits, mais impossible de contacter la base de données: {e}",
                extraction_result=extraction_result,
                company_count=None,
                api_result=None,
                naf_codes=naf_codes if naf_codes else None,
            )

        except Exception as e:
            print(f"[Agent] Unexpected error in process_with_api: {e}")
            return AgentResponse(
                action="extract",
                message="Critères extraits. Une erreur est survenue lors de la recherche.",
                extraction_result=extraction_result,
                company_count=None,
                api_result=None,
                naf_codes=naf_codes if naf_codes else None,
            )

        # Step 4: Check if refinement needed
        refinement_service = get_refinement_service()

        if refinement_service.should_deliver_results(company_count, extraction_result, refinement_round):
            # Deliver results
            forced = company_count > refinement_service.threshold
            message = refinement_service.get_delivery_message(company_count, extraction_result, forced)

            return AgentResponse(
                action="extract",
                message=message,
                extraction_result=extraction_result,
                company_count=company_count,
                api_result=api_result,
                naf_codes=naf_codes if naf_codes else None,
            )

        else:
            # Need refinement - ask follow-up question
            question, _criterion = refinement_service.generate_refinement_question(
                company_count, extraction_result, refinement_round
            )

            return AgentResponse(
                action="refine",
                message=question,
                extraction_result=extraction_result,
                company_count=company_count,
                api_result=None,  # Don't include full results yet
                naf_codes=naf_codes if naf_codes else None,
            )
