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
from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass


class MessageLike(Protocol):
    """Protocol for message objects - works with any object that has role and content"""
    @property
    def role(self) -> Any: ...
    @property
    def content(self) -> str: ...

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")


@dataclass
class ActivityMatch:
    """A single activity match result"""
    activity: str  # Activity label
    naf_codes: List[str]  # Associated NAF codes
    score: float  # Similarity score (0-1)
    selected: bool = False  # Whether this match was selected by the agent


@dataclass
class LocationCorrectionInfo:
    """Info about a location correction for response generation"""
    original: str  # Original value from user/LLM
    corrected: str  # Corrected value
    field_changed: bool  # True if field type was changed
    original_field: str  # Original field type
    corrected_field: str  # Corrected field type


@dataclass
class AgentResponse:
    """Response from the agent processing"""
    action: str  # "extract", "reject", or "refine"
    message: str  # Message to display to user
    extraction_result: Optional[Dict[str, Any]] = None  # Extracted criteria if action="extract"
    company_count: Optional[int] = None  # count_legal - Number of matching companies by NAF codes
    count_semantic: Optional[int] = None  # count_semantic - Number of matching companies by semantic search
    api_result: Optional[Dict[str, Any]] = None  # Full API response data
    naf_codes: Optional[List[str]] = None  # Matched NAF codes from activity matcher
    activity_matches: Optional[List[ActivityMatch]] = None  # Activity matches with scores
    location_corrections: Optional[List[LocationCorrectionInfo]] = None  # Location corrections made


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
    "activite_entreprise": string ou null
  },
  "taille_entreprise": {
    "present": true/false,
    "effectif_expression": string ou null
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
  "message": "Réponse conversationnelle et naturelle au message de l'utilisateur, en le guidant vers une recherche"
}

RÈGLES D'EXTRACTION
-------------------
- activite_entreprise : reprendre le terme utilisé par l'utilisateur (restauration, informatique, BTP...)
- region : liste autorisée = Ile-de-France, Bretagne, Normandie, Occitanie, etc.
- Ne jamais inventer de valeurs non mentionnées

TAILLE D'ENTREPRISE (effectif_expression)
-----------------------------------------
Utilise une expression simple pour la taille :
- Acronymes : "TPE", "PME", "ETI", "GE"
- Comparaisons : "<10", ">500", ">=100", "<=50"
- Intervalles : "10-50", "100-500"
- Combinés : ">10 AND <100"

Correspondances acronymes :
- TPE : 0-9 salariés
- PME : 10-249 salariés
- ETI : 250-4999 salariés
- GE : 5000+ salariés

Réponds UNIQUEMENT avec le JSON, sans texte autour.
"""


# ============================================================================
# NAF Code Selection Prompt
# ============================================================================

NAF_SELECTION_PROMPT = """Tu es un assistant qui aide à sélectionner le code NAF le plus pertinent.

L'utilisateur recherche des entreprises dans le secteur: "{activity_query}"

Voici les correspondances trouvées dans notre base de données (triées par similarité):

{matches_text}

INSTRUCTIONS:
1. Analyse la demande de l'utilisateur
2. Choisis le(s) code(s) NAF le(s) plus pertinent(s) parmi les options
3. Si aucune option ne correspond bien, indique-le

FORMAT DE RÉPONSE JSON:
{{
  "selected_indices": [0],  // Indices des activités sélectionnées (0, 1, 2...)
  "explanation": "Explication courte du choix",
  "no_good_match": false  // true si aucune option ne correspond vraiment
}}

Réponds UNIQUEMENT avec le JSON.
"""


# ============================================================================
# Response Generation Prompt
# ============================================================================

RESPONSE_GENERATION_PROMPT = """Tu es un assistant de recherche d'entreprises françaises. Génère une réponse utile et naturelle.

CONTEXTE DE LA RECHERCHE:
- Requête utilisateur: "{user_query}"
- Nombre d'entreprises trouvées: {company_count}

CRITÈRES EXTRAITS:
{extraction_summary}

CORRESPONDANCES D'ACTIVITÉ:
{activity_matches_summary}

CORRECTIONS DE LOCALISATION:
{location_corrections}

INSTRUCTIONS:
1. Si count > 1000: Suggère des critères pour affiner (taille, CA, localisation plus précise...)
2. Si count = 0: Suggère d'élargir la recherche ou de corriger les critères
3. Si des corrections ont été faites (localisation, activité): Mentionne-les brièvement
4. Si des correspondances d'activité ont un faible score (<50%): Propose de vérifier
5. Sois concis (2-3 phrases max)

CRITÈRES DISPONIBLES POUR AFFINER:
- Localisation: région, département, commune, code postal
- Taille: TPE, PME, ETI, GE (ou nombre de salariés)
- Financier: CA minimum, résultat net
- Juridique: forme juridique, date de création

Réponds directement avec le message (pas de JSON), en français."""


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
    def _format_conversation(messages: List[MessageLike]) -> str:
        """Format conversation history for context."""
        lines = []
        for msg in messages:
            # Handle both enum (msg.role.value) and string (msg.role) formats
            role_value = msg.role.value if hasattr(msg.role, 'value') else msg.role
            role_label = "Utilisateur" if role_value == "user" else "Agent"
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
    async def process_message(
        messages: List[MessageLike],
        previous_extraction: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process user message(s) and extract search criteria.

        ONE LLM call that:
        1. Analyzes the conversation
        2. Extracts criteria OR rejects if too vague

        Args:
            messages: Conversation history
            previous_extraction: Previous extraction result for context

        Returns:
            AgentResponse: Action (extract/reject) with result or message
        """
        # Build conversation context
        if len(messages) == 1 and not previous_extraction:
            user_content = messages[0].content
        else:
            # Multi-turn: include conversation history and previous extraction
            conversation_text = AgentService._format_conversation(messages)

            # Build context with previous extraction if available
            context_parts = [f"CONVERSATION:\n{conversation_text}"]

            if previous_extraction:
                context_parts.append(f"\nCRITÈRES ACTUELS (à conserver ou modifier selon le message):\n{json.dumps(previous_extraction, ensure_ascii=False, indent=2)}")

            context_parts.append("\nExtrais les critères de recherche. Si le dernier message ne contient pas de nouveaux critères, conserve les critères actuels.")

            user_content = "\n".join(context_parts)

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

                # Apply fuzzy matching to location fields
                from services.location_matcher import get_location_matcher
                location_matcher = get_location_matcher()
                extraction, loc_corrections = location_matcher.match_locations(extraction)

                # Transform size expressions to INSEE ranges
                from services.size_matcher import transform_size_field
                extraction, size_correction = transform_size_field(extraction)

                # Convert location corrections to our format
                location_corrections = [
                    LocationCorrectionInfo(
                        original=c.original_value,
                        corrected=c.matched_value,
                        field_changed=c.field_changed,
                        original_field=c.original_field,
                        corrected_field=c.matched_field
                    )
                    for c in loc_corrections if c.was_corrected
                ]

                return AgentResponse(
                    action="extract",
                    message="Recherche en cours...",
                    extraction_result=extraction,
                    location_corrections=location_corrections if location_corrections else None,
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
    def _select_naf_codes(activity_query: str, matches: List[tuple]) -> tuple:
        """
        Use LLM to select the best NAF codes from activity matches.

        Args:
            activity_query: User's activity search term
            matches: List of (activity, score, naf_codes) tuples

        Returns:
            Tuple of (selected_indices, explanation, no_good_match)
        """
        if not matches:
            return [], "Aucune correspondance trouvée", True

        # Format matches for LLM
        matches_lines = []
        for i, (activity, score, naf_codes) in enumerate(matches):
            naf_str = ", ".join(naf_codes) if naf_codes else "(pas de code NAF)"
            matches_lines.append(f"{i}. {activity} (similarité: {score:.2f}) - NAF: {naf_str}")

        matches_text = "\n".join(matches_lines)

        prompt = NAF_SELECTION_PROMPT.format(
            activity_query=activity_query,
            matches_text=matches_text
        )

        try:
            llm_messages = [
                {"role": "user", "content": prompt}
            ]
            response = AgentService._call_llm(llm_messages)
            data = json.loads(AgentService._clean_json(response))

            selected_indices = data.get("selected_indices", [0])
            explanation = data.get("explanation", "")
            no_good_match = data.get("no_good_match", False)

            return selected_indices, explanation, no_good_match

        except Exception as e:
            print(f"[Agent] NAF selection LLM failed: {e}, defaulting to first match")
            return [0], "Sélection par défaut", False

    @staticmethod
    def _call_llm_text(messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """
        Call OpenRouter LLM for free-text response (not JSON).

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
    def _generate_contextual_response(
        user_query: str,
        company_count: int,
        extraction_result: Dict[str, Any],
        activity_matches: List[ActivityMatch],
        location_corrections: Optional[List[LocationCorrectionInfo]] = None,
        conversation_history: Optional[str] = None
    ) -> str:
        """
        Generate a contextual response message using LLM.

        Args:
            user_query: The user's original query
            company_count: Number of companies found
            extraction_result: Extracted criteria
            activity_matches: Activity matches with scores
            location_corrections: Location corrections made (if any)
            conversation_history: Full conversation history for context

        Returns:
            str: Contextual response message
        """
        # Build extraction summary
        extraction_lines = []
        loc = extraction_result.get("localisation", {})
        if loc.get("present"):
            parts = []
            if loc.get("region"):
                parts.append(f"Région: {loc['region']}")
            if loc.get("departement"):
                parts.append(f"Département: {loc['departement']}")
            if loc.get("commune"):
                parts.append(f"Commune: {loc['commune']}")
            if loc.get("code_postal"):
                parts.append(f"Code postal: {loc['code_postal']}")
            if parts:
                extraction_lines.append(f"- Localisation: {', '.join(parts)}")

        act = extraction_result.get("activite", {})
        if act.get("present") and act.get("activite_entreprise"):
            extraction_lines.append(f"- Activité: {act['activite_entreprise']}")

        taille = extraction_result.get("taille_entreprise", {})
        if taille.get("present"):
            if taille.get("acronyme"):
                extraction_lines.append(f"- Taille: {taille['acronyme']}")

        fin = extraction_result.get("criteres_financiers", {})
        if fin.get("present"):
            parts = []
            if fin.get("ca_plus_recent"):
                parts.append(f"CA > {fin['ca_plus_recent']}€")
            if fin.get("resultat_net_plus_recent"):
                parts.append(f"Résultat net > {fin['resultat_net_plus_recent']}€")
            if parts:
                extraction_lines.append(f"- Financier: {', '.join(parts)}")

        jur = extraction_result.get("criteres_juridiques", {})
        if jur.get("present"):
            parts = []
            if jur.get("categorie_juridique"):
                parts.append(f"Forme: {jur['categorie_juridique']}")
            if jur.get("date_creation_entreprise"):
                parts.append(f"Création: {jur['date_creation_entreprise']}")
            if parts:
                extraction_lines.append(f"- Juridique: {', '.join(parts)}")

        extraction_summary = "\n".join(extraction_lines) if extraction_lines else "Aucun critère spécifique"

        # Build activity matches summary
        activity_lines = []
        for match in activity_matches:
            status = "✓" if match.selected else "○"
            naf_str = ", ".join(match.naf_codes) if match.naf_codes else "pas de NAF"
            activity_lines.append(f"  {status} {match.activity} ({match.score*100:.0f}%) - {naf_str}")
        activity_matches_summary = "\n".join(activity_lines) if activity_lines else "Aucune correspondance d'activité"

        # Build location corrections summary
        location_lines = []
        if location_corrections:
            for c in location_corrections:
                if c.field_changed:
                    location_lines.append(f"  - '{c.original}' ({c.original_field}) → '{c.corrected}' ({c.corrected_field})")
                elif c.original != c.corrected:
                    location_lines.append(f"  - '{c.original}' → '{c.corrected}'")
        location_corrections_text = "\n".join(location_lines) if location_lines else "Aucune correction"

        # Identify missing fields that could help narrow results
        missing_fields = []
        if not loc.get("present") or not any([loc.get("region"), loc.get("departement"), loc.get("commune")]):
            missing_fields.append("localisation (région, département, ou commune)")
        if not taille.get("present"):
            missing_fields.append("taille d'entreprise (TPE, PME, ETI, GE)")
        if not fin.get("present"):
            missing_fields.append("critères financiers (CA minimum, résultat net)")

        prompt = RESPONSE_GENERATION_PROMPT.format(
            user_query=user_query,
            company_count=company_count,
            extraction_summary=extraction_summary,
            activity_matches_summary=activity_matches_summary,
            location_corrections=location_corrections_text
        )

        # Add missing fields hint
        if missing_fields and company_count > 500:
            prompt += f"\n\nCRITÈRES NON RENSEIGNÉS (pour affiner):\n- " + "\n- ".join(missing_fields)

        # Add conversation history if available
        if conversation_history:
            prompt += f"\n\nHISTORIQUE DE LA CONVERSATION:\n{conversation_history}"

        try:
            # Send user query as a separate user message for better context
            llm_messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_query},
            ]
            response = AgentService._call_llm_text(llm_messages)
            return response.strip()
        except Exception as e:
            print(f"[Agent] Response generation LLM failed: {e}")
            # Fallback to simple message
            if company_count == 0:
                return "Aucune entreprise ne correspond à ces critères. Essayez d'élargir votre recherche."
            elif company_count <= 100:
                return f"J'ai trouvé {company_count} entreprises correspondant à vos critères."
            elif company_count <= 500:
                return f"J'ai trouvé {company_count} entreprises. Vous pouvez affiner si besoin."
            else:
                return f"J'ai trouvé {company_count} entreprises. Affinez vos critères pour réduire ce nombre."

    @staticmethod
    async def process_with_api(
        extraction_result: Dict[str, Any],
        refinement_round: int = 1,
        user_query: str = "",
        location_corrections: Optional[List[LocationCorrectionInfo]] = None,
        previous_extraction: Optional[Dict[str, Any]] = None,
        previous_activity_matches: Optional[List[ActivityMatch]] = None,
        conversation_history: Optional[str] = None
    ) -> AgentResponse:
        """
        Process extraction result through external company API.

        1. Check if activity field changed (for caching)
        2. Match activities to NAF codes using embeddings (if changed)
        3. LLM selects best NAF codes from matches
        4. Transform to API format
        5. Call external API for company count
        6. Generate contextual response message

        Args:
            extraction_result: Extraction result from process_message
            refinement_round: Current refinement round (unused, kept for compatibility)
            user_query: The user's original query for context
            location_corrections: Location corrections made during extraction
            previous_extraction: Previous extraction for caching unchanged fields
            previous_activity_matches: Previous activity matches for caching
            conversation_history: Full conversation history for response generation

        Returns:
            AgentResponse with extraction, company_count, and activity_matches
        """
        # Import services here to avoid circular imports
        from services.activity_matcher import get_activity_matcher
        from services.api_transformer import transform_extraction_to_api_request
        from services.company_api_client import get_company_api_client, CompanyAPIError

        naf_codes = []
        api_result = None
        company_count = 0
        count_semantic = 0
        original_activity_text = None
        activity_matches: List[ActivityMatch] = []

        try:
            # Check if activity changed (for caching)
            activite = extraction_result.get("activite", {})
            activity_query = activite.get("activite_entreprise")

            previous_activity = None
            if previous_extraction:
                previous_activite = previous_extraction.get("activite", {})
                previous_activity = previous_activite.get("activite_entreprise")

            activity_changed = activity_query != previous_activity

            # Step 1: Match activities to NAF codes using embeddings (or use cache)
            if activity_query:
                # Save original activity text for semantic search
                original_activity_text = activity_query

                if not activity_changed and previous_activity_matches:
                    # Activity unchanged - reuse previous matches
                    print(f"[Agent] Activity unchanged ('{activity_query}'), reusing cached matches")
                    activity_matches = previous_activity_matches
                    # Collect NAF codes from selected matches
                    for match in activity_matches:
                        if match.selected:
                            for code in match.naf_codes:
                                if code not in naf_codes:
                                    naf_codes.append(code)
                else:
                    # Activity changed - run embedding search
                    activity_matcher = await get_activity_matcher()
                    matches = activity_matcher.find_similar_activities(activity_query, top_k=5, threshold=0.3)
                    print(f"[Agent] Activity '{activity_query}' matches:")
                    for activity, score, codes in matches:
                        print(f"  - {activity} (score={score:.2f}) NAF: {codes}")

                    # Step 2: LLM selects best matches
                    selected_indices, explanation, no_good_match = AgentService._select_naf_codes(
                        activity_query, matches
                    )
                    print(f"[Agent] LLM selected indices: {selected_indices}, explanation: {explanation}")

                    # Build activity matches list and collect NAF codes
                    for i, (activity, score, codes) in enumerate(matches):
                        is_selected = i in selected_indices and not no_good_match
                        activity_matches.append(ActivityMatch(
                            activity=activity,
                            naf_codes=codes,
                            score=score,
                            selected=is_selected
                        ))
                        if is_selected:
                            for code in codes:
                                if code not in naf_codes:
                                    naf_codes.append(code)

                print(f"[Agent] Final NAF codes: {naf_codes}")

            # Step 2: Transform to API format (pass original activity text for semantic search)
            api_request = transform_extraction_to_api_request(
                extraction_result,
                naf_codes,
                original_activity_text=original_activity_text
            )
            print(f"[Agent] API request: {json.dumps(api_request, ensure_ascii=False)}")

            # Step 3: Call external API
            api_client = get_company_api_client()
            api_response = api_client.count_companies(api_request)

            company_count = api_response.count  # count_legal
            count_semantic = api_response.count_semantic  # count_semantic
            api_result = api_response.data
            print(f"[Agent] API returned count_legal={company_count}, count_semantic={count_semantic}")

        except CompanyAPIError as e:
            print(f"[Agent] API error: {e}")
            # Return extraction result with error message
            return AgentResponse(
                action="extract",
                message=f"Critères extraits, mais impossible de contacter la base de données: {e}",
                extraction_result=extraction_result,
                company_count=None,
                count_semantic=None,
                api_result=None,
                naf_codes=naf_codes if naf_codes else None,
                activity_matches=activity_matches if activity_matches else None,
            )

        except Exception as e:
            print(f"[Agent] Unexpected error in process_with_api: {e}")
            return AgentResponse(
                action="extract",
                message="Critères extraits. Une erreur est survenue lors de la recherche.",
                extraction_result=extraction_result,
                company_count=None,
                count_semantic=None,
                api_result=None,
                naf_codes=naf_codes if naf_codes else None,
                activity_matches=activity_matches if activity_matches else None,
            )

        # Step 4: Generate contextual response message
        if user_query and activity_matches:
            message = AgentService._generate_contextual_response(
                user_query=user_query,
                company_count=company_count,
                extraction_result=extraction_result,
                activity_matches=activity_matches,
                location_corrections=location_corrections,
                conversation_history=conversation_history
            )
        else:
            # Fallback to simple message if no context available
            if company_count == 0:
                message = "Aucune entreprise ne correspond à ces critères. Essayez d'élargir votre recherche."
            elif company_count <= 100:
                message = f"J'ai trouvé {company_count} entreprises correspondant à vos critères."
            elif company_count <= 500:
                message = f"J'ai trouvé {company_count} entreprises. Vous pouvez affiner si besoin."
            else:
                message = f"J'ai trouvé {company_count} entreprises. Affinez vos critères pour réduire ce nombre."

        return AgentResponse(
            action="extract",
            message=message,
            extraction_result=extraction_result,
            company_count=company_count,
            count_semantic=count_semantic,
            api_result=api_result,
            naf_codes=naf_codes if naf_codes else None,
            activity_matches=activity_matches if activity_matches else None,
            location_corrections=location_corrections,
        )
