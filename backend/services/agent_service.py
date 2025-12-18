"""
Agent service for intelligent conversation management.

This service implements the core conversational AI logic:
- Completeness analysis (is the query ready for extraction?)
- Question generation (what to ask next?)
- Conversation merging (combine multi-turn inputs)
"""

import json
import os
import requests
from typing import List, Dict, Any, Optional

from models import Message
from schemas import CompletenessAnalysis

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")


# ============================================================================
# Question Templates (Fast path for common scenarios)
# ============================================================================

QUESTION_TEMPLATES = {
    "missing_activity": (
        "Une {company_type} dans quel secteur d'activité ? "
        "(par exemple : restauration, informatique, construction, santé...)"
    ),
    "missing_location": (
        "Dans quelle région ou département souhaitez-vous chercher ? "
        "(par exemple : Bretagne, 75, Paris, Île-de-France...)"
    ),
    "vague_activity": (
        "Une PME de quoi exactement ? "
        "(secteur d'activité ou type de produit/service : restauration, services informatiques, BTP...)"
    ),
    "very_broad": (
        "Votre recherche est large. Avez-vous une préférence de localisation "
        "(région, département) ou de taille d'entreprise (TPE, PME, ETI) ?"
    ),
    "confirm_optional": (
        "J'ai compris : {criteria}. Souhaitez-vous ajouter d'autres critères ? "
        "(localisation, taille, chiffre d'affaires...)"
    ),
}


# ============================================================================
# Agent Service
# ============================================================================

class AgentService:
    """Service for conversational AI agent logic"""

    @staticmethod
    def _call_llm(prompt: str, temperature: float = 0.0, response_format: Optional[str] = None) -> str:
        """
        Call OpenRouter LLM with given prompt.

        Args:
            prompt: The prompt to send
            temperature: Temperature for generation (0.0 = deterministic)
            response_format: Optional response format ("json_object" for JSON)

        Returns:
            str: LLM response content

        Raises:
            Exception: If API call fails
        """
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set")

        messages = [{"role": "user", "content": prompt}]

        payload: Dict[str, Any] = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "temperature": temperature,
        }

        if response_format:
            payload["response_format"] = {"type": response_format}

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
        """
        Format conversation history for LLM context.

        Args:
            messages: List of messages

        Returns:
            str: Formatted conversation string
        """
        lines = []
        for msg in messages:
            role_label = "User" if msg.role.value == "user" else "Agent"
            lines.append(f"{role_label}: {msg.content}")
        return "\n".join(lines)

    @staticmethod
    async def analyze_completeness(messages: List[Message]) -> CompletenessAnalysis:
        """
        Analyze if conversation has enough info for extraction (MODERATE mode).

        Thresholds:
        - >= 0.9: Extract immediately (very confident)
        - 0.6-0.9: Ask one confirmation question
        - < 0.6: Need clarification

        Args:
            messages: Conversation history

        Returns:
            CompletenessAnalysis: Analysis result
        """
        conversation_text = AgentService._format_conversation(messages)

        prompt = f"""Analyse cette conversation sur la recherche d'entreprises françaises.

CONVERSATION:
{conversation_text}

RÈGLES:
- Requis (au moins 1) : Activité/secteur OU Localisation
- Optionnel : Taille, critères financiers/juridiques

MODE: MODÉRÉ
- is_complete=true si confiance >= 0.9 (tous critères clairs, ex: "PME restauration Bretagne CA > 1M€")
- is_complete=false si confiance < 0.9 (même si requête acceptable, proposer confirmation/enrichissement)

EXEMPLE MODE MODÉRÉ:
- "PME restauration" → confiance=0.7 → is_complete=false, question="Souhaitez-vous préciser la localisation?"
- "PME" → confiance=0.3 → is_complete=false, question="Une PME de quoi exactement?"
- "PME restauration en Bretagne CA > 1M€" → confiance=0.95 → is_complete=true

Réponds en JSON:
{{
  "is_complete": boolean,
  "missing_fields": ["activite", "localisation", "taille_entreprise", "criteres_financiers"],
  "confidence": 0.0-1.0,
  "suggested_question": "question à poser" ou null si is_complete=true,
  "reasoning": "explication brève du score"
}}
"""

        try:
            response = AgentService._call_llm(prompt, response_format="json_object")
            data = json.loads(response)
            return CompletenessAnalysis(**data)
        except Exception as e:
            # Fallback: conservative analysis
            print(f"Completeness analysis failed: {e}")
            return CompletenessAnalysis(
                is_complete=False,
                missing_fields=["activite", "localisation"],
                confidence=0.3,
                suggested_question="Pouvez-vous préciser votre recherche ?",
                reasoning=f"Error in analysis: {str(e)}",
            )

    @staticmethod
    def _try_template_match(missing_fields: List[str], messages: List[Message]) -> Optional[str]:
        """
        Try to match situation to a question template.

        Args:
            missing_fields: List of missing required fields
            messages: Conversation history

        Returns:
            str or None: Template question if matched
        """
        # Extract all user text
        user_text = " ".join([
            msg.content.lower()
            for msg in messages
            if msg.role.value == "user"
        ])

        # Detect company type mentioned
        company_type = "entreprise"
        for term in ["pme", "tpe", "eti"]:
            if term in user_text:
                company_type = term.upper()
                break

        # Priority 1: Activity completely missing
        if "activite" in missing_fields and not any(
            word in user_text
            for word in ["secteur", "activité", "domaine", "restauration", "informatique", "construction"]
        ):
            return QUESTION_TEMPLATES["missing_activity"].format(company_type=company_type)

        # Priority 2: Vague activity term like "PME" alone
        if any(word in user_text for word in ["pme", "tpe", "entreprise"]) and "activite" in missing_fields:
            return QUESTION_TEMPLATES["vague_activity"]

        # Priority 3: Location missing
        if "localisation" in missing_fields and len(missing_fields) >= 2:
            return QUESTION_TEMPLATES["missing_location"]

        # Priority 4: Very broad query
        if len(missing_fields) >= 3:
            return QUESTION_TEMPLATES["very_broad"]

        return None

    @staticmethod
    async def generate_question(
        messages: List[Message], analysis: CompletenessAnalysis
    ) -> str:
        """
        Generate next question to ask user.

        Uses hybrid approach:
        1. Try template matching (fast)
        2. Fall back to LLM generation (contextual)

        Args:
            messages: Conversation history
            analysis: Completeness analysis result

        Returns:
            str: Question to ask user
        """
        # If already complete, no question needed
        if analysis.is_complete:
            return "Parfait ! J'ai tous les critères nécessaires. Lancement de la recherche..."

        # Try template first
        template_question = AgentService._try_template_match(analysis.missing_fields, messages)
        if template_question:
            return template_question

        # Fall back to LLM generation
        conversation_text = AgentService._format_conversation(messages)

        prompt = f"""Tu es un assistant aidant à chercher des entreprises françaises.

CONVERSATION:
{conversation_text}

ANALYSE:
- Champs manquants : {', '.join(analysis.missing_fields) if analysis.missing_fields else 'aucun'}
- Raisonnement : {analysis.reasoning}
- Confiance : {analysis.confidence}

TÂCHE:
Génère UNE question naturelle en français pour obtenir l'info la plus importante manquante.
La question doit :
- Être amicale et conversationnelle
- Être spécifique à ce qui a été discuté
- Demander le champ manquant le PLUS critique
- Inclure des exemples concrets entre parenthèses

Réponds UNIQUEMENT avec la question, sans JSON ni explication.

EXEMPLES:
- "Dans quel secteur d'activité ? (par exemple : restauration, informatique, BTP...)"
- "Souhaitez-vous préciser la région ? (Bretagne, Île-de-France, Hauts-de-France...)"
"""

        try:
            return AgentService._call_llm(prompt, temperature=0.3).strip()
        except Exception as e:
            print(f"Question generation failed: {e}")
            # Fallback to generic question
            return "Pouvez-vous me donner plus de détails sur votre recherche ?"

    @staticmethod
    async def merge_conversation(messages: List[Message]) -> str:
        """
        Merge multi-turn conversation into single coherent query.

        Args:
            messages: Conversation history

        Returns:
            str: Merged query for extraction
        """
        # If only one user message, return it
        user_messages = [msg for msg in messages if msg.role.value == "user"]
        if len(user_messages) == 1:
            return user_messages[0].content

        # Get last 10 messages for context (limit context window)
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        conversation_text = AgentService._format_conversation(recent_messages)

        prompt = f"""Synthétise cette conversation en UNE phrase décrivant la recherche d'entreprises.

CONVERSATION:
{conversation_text}

TÂCHE:
Combine TOUS les critères mentionnés par l'utilisateur (activité, lieu, taille, finances, juridique).
Retourne SEULEMENT la phrase synthétisée, rien d'autre.

EXEMPLES:
Conversation:
User: "Je cherche des PME"
User: "Dans la restauration"
User: "En Bretagne"
→ OUTPUT: "PME dans la restauration en Bretagne"

Conversation:
User: "entreprises de construction"
User: "avec plus de 50 salariés"
User: "créées après 2020"
→ OUTPUT: "Entreprises de construction avec plus de 50 salariés créées après 2020"
"""

        try:
            merged = AgentService._call_llm(prompt, temperature=0.0).strip()
            # Clean up any markdown or extra formatting
            merged = merged.strip('"').strip("'")
            return merged
        except Exception as e:
            print(f"Conversation merge failed: {e}")
            # Fallback: just join user messages
            return " ".join([msg.content for msg in user_messages])
