"""
Agent service for intelligent conversation management.

Simplified approach: ONE LLM call that decides whether to extract or clarify.
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
    action: str  # "extract" or "clarify"
    message: str  # Question to ask or confirmation message
    extraction_result: Optional[Dict[str, Any]] = None  # Extracted criteria if action="extract"


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
- tranche_effectif : "10 a 19 salaries", "20 a 49 salaries", etc.
- acronyme : TPE, PME, ETI, grand groupe
- Ne jamais inventer de valeurs non mentionnées

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
        # Build conversation context
        if len(messages) == 1:
            user_content = messages[0].content
        else:
            # Multi-turn: include conversation history
            conversation_text = AgentService._format_conversation(messages)
            user_content = f"""CONVERSATION:
{conversation_text}

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
