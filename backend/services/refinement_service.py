"""
Refinement Service.

Decides when and how to refine search criteria when too many results.
"""

import os
from typing import Dict, Any, List, Optional, Tuple


# Configuration
REFINEMENT_THRESHOLD = int(os.getenv("REFINEMENT_THRESHOLD", "500"))
MAX_REFINEMENT_ROUNDS = int(os.getenv("MAX_REFINEMENT_ROUNDS", "3"))


# Priority order for refinement questions
REFINEMENT_PRIORITY = [
    "localisation",
    "taille_entreprise",
    "criteres_financiers",
    "criteres_juridiques",
]

# Question templates for each criterion
REFINEMENT_QUESTIONS = {
    "localisation": {
        "base": "Dans quelle zone geographique ?",
        "with_count": "J'ai trouve {count} entreprises. Dans quelle region, departement ou ville souhaitez-vous chercher ?",
        "follow_up": "Pouvez-vous preciser la zone geographique ? (region, departement ou ville)",
    },
    "taille_entreprise": {
        "base": "Quelle taille d'entreprise recherchez-vous ?",
        "with_count": "J'ai trouve {count} entreprises. Quelle taille vous interesse ? (TPE, PME, ETI, grand groupe)",
        "follow_up": "Pouvez-vous preciser la taille d'entreprise ? (TPE: 0-9 salaries, PME: 10-249, ETI: 250-4999, GE: 5000+)",
    },
    "criteres_financiers": {
        "base": "Avez-vous des criteres financiers ?",
        "with_count": "J'ai trouve {count} entreprises. Avez-vous un critere de chiffre d'affaires minimum ?",
        "follow_up": "Souhaitez-vous filtrer par chiffre d'affaires ? (ex: CA > 1M EUR)",
    },
    "criteres_juridiques": {
        "base": "Souhaitez-vous uniquement les sieges sociaux ?",
        "with_count": "J'ai trouve {count} entreprises. Voulez-vous filtrer uniquement les sieges sociaux (pas les etablissements secondaires) ?",
        "follow_up": "Filtrer uniquement les sieges sociaux (oui/non) ?",
    },
}


class RefinementService:
    """
    Service for deciding when and how to refine search results.

    When there are too many results, this service determines which
    criteria to ask about and generates appropriate questions.
    """

    def __init__(self, threshold: int = REFINEMENT_THRESHOLD):
        """
        Initialize the refinement service.

        Args:
            threshold: Maximum results before requiring refinement
        """
        self.threshold = threshold

    def needs_refinement(self, count: int) -> bool:
        """
        Check if the result count requires refinement.

        Args:
            count: Number of results from API

        Returns:
            True if count exceeds threshold
        """
        return count > self.threshold

    def get_missing_criteria(self, extraction: Dict[str, Any]) -> List[str]:
        """
        Identify which criteria are not yet specified.

        Args:
            extraction: Current extraction result

        Returns:
            List of missing criterion names in priority order
        """
        missing = []

        for criterion in REFINEMENT_PRIORITY:
            criteria_data = extraction.get(criterion, {})
            if not criteria_data.get("present", False):
                missing.append(criterion)

        return missing

    def get_refinable_criteria(self, extraction: Dict[str, Any]) -> List[str]:
        """
        Get criteria that can be further refined even if present.

        For example, if region is set but not city, we can ask for city.

        Args:
            extraction: Current extraction result

        Returns:
            List of criteria that can be refined
        """
        refinable = []

        # Localisation: can always be more specific
        loc = extraction.get("localisation", {})
        if loc.get("present"):
            # If only region, can ask for department/city
            if loc.get("region") and not loc.get("commune") and not loc.get("departement"):
                refinable.append("localisation")
            # If only department, can ask for city
            elif loc.get("departement") and not loc.get("commune"):
                refinable.append("localisation")

        # Company size: if using acronym ranges, could narrow down
        taille = extraction.get("taille_entreprise", {})
        if taille.get("present"):
            tranches = taille.get("tranche_effectif", [])
            # If broad range (more than 3 tranches), can narrow
            if len(tranches) > 3:
                refinable.append("taille_entreprise")

        return refinable

    def generate_refinement_question(
        self,
        count: int,
        extraction: Dict[str, Any],
        refinement_round: int = 1
    ) -> Tuple[str, str]:
        """
        Generate a follow-up question to narrow down results.

        Args:
            count: Current result count
            extraction: Current extraction result
            refinement_round: Which round of refinement (1, 2, 3)

        Returns:
            Tuple of (question_text, criterion_name)
        """
        # First check missing criteria
        missing = self.get_missing_criteria(extraction)

        if missing:
            criterion = missing[0]
            template = REFINEMENT_QUESTIONS.get(criterion, {})
            question = template.get("with_count", template.get("base", "Pouvez-vous preciser ?"))
            return question.format(count=count), criterion

        # If all criteria present, try to refine existing ones
        refinable = self.get_refinable_criteria(extraction)

        if refinable:
            criterion = refinable[0]
            template = REFINEMENT_QUESTIONS.get(criterion, {})
            question = template.get("follow_up", template.get("base", "Pouvez-vous preciser ?"))
            return question.format(count=count), criterion

        # Fallback: generic question
        return (
            f"J'ai trouve {count} entreprises, ce qui est beaucoup. "
            "Pouvez-vous preciser vos criteres pour affiner la recherche ?",
            "generic"
        )

    def should_deliver_results(
        self,
        count: int,
        extraction: Dict[str, Any],
        refinement_round: int
    ) -> bool:
        """
        Decide if we should deliver results despite high count.

        Args:
            count: Current result count
            extraction: Current extraction result
            refinement_round: Current refinement round

        Returns:
            True if we should stop refining and deliver results
        """
        # Always deliver if under threshold
        if count <= self.threshold:
            return True

        # Stop after max rounds
        if refinement_round >= MAX_REFINEMENT_ROUNDS:
            return True

        # Stop if no more criteria to ask about
        missing = self.get_missing_criteria(extraction)
        refinable = self.get_refinable_criteria(extraction)

        if not missing and not refinable:
            return True

        return False

    def get_delivery_message(
        self,
        count: int,
        extraction: Dict[str, Any],
        forced: bool = False
    ) -> str:
        """
        Generate a message when delivering results.

        Args:
            count: Result count
            extraction: Final extraction result
            forced: True if delivering despite high count (after max rounds)

        Returns:
            Message string
        """
        if forced:
            return (
                f"J'ai trouve {count} entreprises correspondant a vos criteres. "
                "C'est un volume important - vous pouvez affiner votre recherche "
                "avec des criteres supplementaires si besoin."
            )

        if count == 0:
            return (
                "Aucune entreprise ne correspond a ces criteres. "
                "Essayez d'elargir votre recherche (region plus large, taille differente...)."
            )

        if count <= 10:
            return f"Parfait ! J'ai trouve {count} entreprises correspondant exactement a vos criteres."

        if count <= 100:
            return f"J'ai trouve {count} entreprises correspondant a vos criteres."

        return f"J'ai trouve {count} entreprises correspondant a vos criteres."


# Module-level singleton
_refinement_service: Optional[RefinementService] = None


def get_refinement_service() -> RefinementService:
    """Get or create the singleton RefinementService instance."""
    global _refinement_service
    if _refinement_service is None:
        _refinement_service = RefinementService()
    return _refinement_service
