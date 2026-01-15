"""
Agent service for intelligent conversation management.

Simplified approach: ONE LLM call that decides whether to extract or clarify.
Then queries external API and handles refinement if too many results.
"""

import json
import os
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

from models import Message

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")


@dataclass
class AgentResponse:
    """Response from the agent processing"""
    action: str  # "extract", "clarify", or "refine"
    message: str  # Question to ask or confirmation message
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
Analyse la requête utilisateur et décide :
1. EXTRAIRE : si au moins un critère exploitable est présent
2. CLARIFIER : si la requête est trop vague

CRITÈRES EXPLOITABLES (au moins 1 requis pour extraire)
-------------------------------------------------------
- Secteur/activité : restauration, informatique, BTP, santé, conseil, industrie...
- Localisation : région, département, ville, code postal
- Critères financiers : CA, résultat net, rentabilité avec montant

CRITÈRES INSUFFISANTS SEULS (nécessitent clarification)
-------------------------------------------------------
- Taille seule (TPE/PME/ETI/grand groupe) SANS secteur ni localisation
- Termes vagues : "entreprise", "société", "bonjour", "aide-moi"
RÈGLES DE DÉCISION
------------------
✅ EXTRAIRE si :
- "PME informatique" → activité présente
- "restaurants en Bretagne" → activité + localisation
- "entreprises à Paris" → localisation présente
- "sociétés de conseil" → activité présente
- "CA > 1M€" → critère financier exploitable

❌ CLARIFIER si :
- "une PME" → taille seule, demander secteur
- "je cherche une entreprise" → trop vague
- "bonjour" / "aide-moi" → pas de critère

FORMAT DE SORTIE JSON
---------------------
Si EXTRAIRE, renvoie l'extraction complète :
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

Si CLARIFIER, renvoie une question :
{
  "action": "clarify",
  "question": "Question courte et naturelle avec exemples"
}

REGLE DE PRECISION: Si l'utilisateur ne mentionne pas de secteur ni de localisation ni d'activité, ni de critère financier, ni de critère juridique, ni la taille avec un nombre de salariés, alors tu mets a false tous les champs "present".

EXEMPLES DE QUESTIONS DE CLARIFICATION
--------------------------------------
- "Une PME dans quel secteur d'activité ? (restauration, informatique, BTP...)"
- "Quel type d'entreprise recherchez-vous ? (secteur, localisation...)"
- "Dans quelle région ou département ?"

RÈGLES D'EXTRACTION (si action=extract)
---------------------------------------
- libelle_secteur : reprendre le terme utilisé (restauration, informatique...)
- activite_entreprise : code NAF UNIQUEMENT si explicitement mentionné, sinon null
- region : liste autorisée = Ile-de-France, Bretagne, Normandie, Occitanie, etc.
- Ne jamais inventer de valeurs non mentionnées

TRANCHES D'EFFECTIF INSEE (inférence bidirectionnelle)
-------------------------------------------------------
Le mapping fonctionne dans LES DEUX SENS :

A) ACRONYME → TRANCHES (si l'utilisateur dit "PME", "TPE", etc.)
   - MIC/TPE → ["0 salarie", "1 ou 2 salaries", "3 a 5 salaries", "6 a 9 salaries"]
   - PME → ["10 a 19 salaries", "20 a 49 salaries", "50 a 99 salaries", "100 a 199 salaries", "200 a 249 salaries"]
   - ETI → ["250 a 499 salaries", "500 a 999 salaries", "1 000 a 1 999 salaries", "2 000 a 4 999 salaries"]
   - GE → ["5 000 a 9 999 salaries", "10 000 salaries et plus"]

B) TRANCHES/NOMBRE → ACRONYME (si l'utilisateur mentionne un nombre de salariés)
   Déduis l'acronyme à partir du nombre mentionné :
   - "moins de 10 salariés" ou "5 employés" → acronyme = "TPE", tranche = ["3 a 5 salaries"]
   - "50 salariés" ou "entre 20 et 100" → acronyme = "PME", tranche adaptée
   - "300 employés" ou "500 salariés" → acronyme = "ETI", tranche adaptée
   - "plus de 5000" ou "10000 salariés" → acronyme = "GE", tranche adaptée

   Mapping inverse par nombre :
   - 0-9 salariés → acronyme = "TPE"
   - 10-249 salariés → acronyme = "PME"
   - 250-4999 salariés → acronyme = "ETI"
   - 5000+ salariés → acronyme = "GE"

IMPORTANT : tranche_effectif doit être un ARRAY de strings.
Exemples :
- "PME informatique" → acronyme="PME", tranche_effectif=["10 a 19 salaries", "20 a 49 salaries", ...]
- "entreprise de 50 salariés" → acronyme="PME", tranche_effectif=["50 a 99 salaries"]
- "startup de 5 personnes" → acronyme="TPE", tranche_effectif=["3 a 5 salaries"]


RÉPONSES EMPATHIQUES (conversations multi-tours)
------------------------------------------------
Si tu détectes que l'utilisateur RÉPÈTE une requête similaire ou reformule la même demande :

1. NE PAS répéter la même question générique
2. RECONNAÎTRE sa demande avec empathie
3. PROPOSER des alternatives concrètes liées à son intention

Exemples de réponses empathiques :

❌ MAUVAIS (répétitif) :
User: "je cherche du pain"
Agent: "Quel type d'entreprise recherchez-vous ?"
User: "je cherche du pain"
Agent: "Quel type d'entreprise recherchez-vous ?" ← INTERDIT

✅ BON (empathique avec alternatives) :
User: "je cherche du pain"
Agent: "Dans quel secteur d'activité ?"
User: "je cherche du pain"
Agent: "Je comprends que vous cherchez quelque chose lié au pain. Notre service recherche des entreprises. Souhaitez-vous trouver des boulangeries artisanales, des distributeurs de pain, ou des entreprises agroalimentaires ?"

Autres exemples :
- "avocat" répété → "Recherchez-vous des cabinets d'avocats, ou des entreprises dans le secteur juridique ?"
- "voiture" répété → "Cherchez-vous des concessionnaires automobiles, des garages, ou des constructeurs ?"
- Requête incohérente 3x → "Je suis un assistant spécialisé dans la recherche d'entreprises françaises. Puis-je vous aider à trouver une entreprise dans un domaine particulier ? (restauration, informatique, BTP, santé...)"

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
    def _detect_repetition_pattern(messages: List[Message]) -> Optional[str]:
        """
        Detect if the user is repeating similar requests.

        Args:
            messages: Conversation history

        Returns:
            The repeated pattern if detected, None otherwise
        """
        # Get only user messages
        user_messages = [m.content.lower().strip() for m in messages if m.role.value == "user"]

        if len(user_messages) < 2:
            return None

        # Check if last 2 user messages are similar
        last_two = user_messages[-2:]
        similarity = SequenceMatcher(None, last_two[0], last_two[1]).ratio()

        if similarity > 0.6:
            return last_two[-1]  # Return the repeated message

        # Check if user repeated same thing 3 times
        if len(user_messages) >= 3:
            last_three = user_messages[-3:]
            avg_similarity = sum(
                SequenceMatcher(None, last_three[i], last_three[j]).ratio()
                for i in range(3) for j in range(i + 1, 3)
            ) / 3

            if avg_similarity > 0.5:
                return f"répétition multiple: {last_three[-1]}"

        return None

    @staticmethod
    async def process_message(messages: List[Message]) -> AgentResponse:
        """
        Process user message(s) and decide whether to extract or clarify.

        ONE LLM call that:
        1. Analyzes the conversation
        2. Decides: extract or clarify
        3. Returns extraction result OR question

        Args:
            messages: Conversation history

        Returns:
            AgentResponse: Action (extract/clarify) with result or question
        """
        # Detect repetition pattern
        repetition_pattern = AgentService._detect_repetition_pattern(messages)

        # Build conversation context
        if len(messages) == 1:
            user_content = messages[0].content
        else:
            # Multi-turn: include conversation history
            conversation_text = AgentService._format_conversation(messages)

            # Add repetition hint if detected
            repetition_hint = ""
            if repetition_pattern:
                repetition_hint = f"""

⚠️ ATTENTION RÉPÉTITION DÉTECTÉE: L'utilisateur répète "{repetition_pattern}"
→ NE PAS reposer la même question générique
→ Propose des alternatives concrètes liées à son intention
→ Sois empathique et aide-le à trouver une entreprise correspondante"""

            user_content = f"""CONVERSATION:
{conversation_text}
{repetition_hint}
Analyse la conversation complète et décide si tu peux extraire les critères ou si tu dois poser une question."""

        # Single LLM call
        llm_messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        try:
            response = AgentService._call_llm(llm_messages)
            data = json.loads(AgentService._clean_json(response))

            action = data.get("action", "clarify")

            if action == "extract":
                # Build extraction result (remove "action" key)
                extraction = {k: v for k, v in data.items() if k != "action"}
                return AgentResponse(
                    action="extract",
                    message="Parfait ! J'ai tous les critères nécessaires. Lancement de la recherche...",
                    extraction_result=extraction,
                )
            else:
                # Clarification needed
                question = data.get("question", "Pouvez-vous préciser votre recherche ?")
                return AgentResponse(
                    action="clarify",
                    message=question,
                    extraction_result=None,
                )

        except Exception as e:
            print(f"Agent processing failed: {e}")
            # Fallback: ask for clarification
            return AgentResponse(
                action="clarify",
                message="Pouvez-vous préciser votre recherche ? (secteur d'activité, localisation...)",
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
