"""
Tests poussés pour l'API Agent conversationnel.

Ce script teste différents scénarios :
1. Requêtes valides qui doivent extraire directement (action="extract")
2. Requêtes vagues qui doivent clarifier (action="clarify")
3. Mapping automatique des acronymes (MIC/TPE/PME/ETI/GE) vers tranches INSEE
4. Conversations multi-tours (questions/réponses)
5. Requêtes complexes avec plusieurs critères

Usage:
    python test_agent_api.py --base-url http://localhost:8000
    python test_agent_api.py --base-url https://your-app.onrender.com
"""

import argparse
import json
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class TestStatus(Enum):
    """Status des tests"""
    PASSED = "✓ PASSED"
    FAILED = "✗ FAILED"
    SKIPPED = "⊘ SKIPPED"


@dataclass
class TestCase:
    """Un cas de test"""
    name: str
    user_message: str
    expected_action: str  # "extract" or "clarify"
    expected_criteria: Optional[Dict[str, Any]] = None  # Critères attendus si extract
    description: str = ""


@dataclass
class TestResult:
    """Résultat d'un test"""
    test_case: TestCase
    status: TestStatus
    actual_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


# ============================================================================
# Test Cases
# ============================================================================

# Tests de base - Extraction directe
BASIC_EXTRACT_TESTS = [
    TestCase(
        name="PME informatique (activité présente)",
        user_message="PME informatique",
        expected_action="extract",
        expected_criteria={
            "activite": {"present": True, "libelle_secteur": "informatique"},
            "taille_entreprise": {"present": True, "acronyme": "PME"}
        },
        description="Doit extraire directement car activité présente"
    ),
    TestCase(
        name="Restaurants en Bretagne",
        user_message="restaurants en Bretagne",
        expected_action="extract",
        expected_criteria={
            "activite": {"present": True, "libelle_secteur": "restauration"},
            "localisation": {"present": True, "region": "Bretagne"}
        },
        description="Activité + localisation"
    ),
    TestCase(
        name="Entreprises à Paris",
        user_message="entreprises à Paris",
        expected_action="extract",
        expected_criteria={
            "localisation": {"present": True}
        },
        description="Localisation seule suffit pour extraction"
    ),
    TestCase(
        name="Sociétés de conseil",
        user_message="sociétés de conseil",
        expected_action="extract",
        expected_criteria={
            "activite": {"present": True, "libelle_secteur": "conseil"}
        },
        description="Activité présente"
    ),
    TestCase(
        name="CA supérieur à 1M€",
        user_message="entreprises avec CA supérieur à 1M€",
        expected_action="extract",
        expected_criteria={
            "criteres_financiers": {"present": True, "ca_plus_recent": 1000000}
        },
        description="Critère financier exploitable"
    ),
]

# Tests de clarification - Requêtes vagues
CLARIFY_TESTS = [
    TestCase(
        name="Une PME seule (sans secteur)",
        user_message="une PME",
        expected_action="clarify",
        description="Taille seule sans secteur ni localisation → clarification"
    ),
    TestCase(
        name="Je cherche une entreprise",
        user_message="je cherche une entreprise",
        expected_action="clarify",
        description="Trop vague"
    ),
    TestCase(
        name="Bonjour",
        user_message="bonjour",
        expected_action="clarify",
        description="Message de salutation"
    ),
    TestCase(
        name="TPE seule",
        user_message="TPE",
        expected_action="clarify",
        description="Acronyme seul sans contexte"
    ),
]

# Tests de mapping INSEE - Vérification que les acronymes sont mappés
INSEE_MAPPING_TESTS = [
    TestCase(
        name="PME informatique → tranches INSEE",
        user_message="PME informatique",
        expected_action="extract",
        expected_criteria={
            "taille_entreprise": {
                "present": True,
                "acronyme": "PME",
                "tranche_effectif": [
                    "10 a 19 salaries",
                    "20 a 49 salaries",
                    "50 a 99 salaries",
                    "100 a 199 salaries",
                    "200 a 249 salaries"
                ]
            }
        },
        description="Vérifie que PME est mappé aux bonnes tranches INSEE"
    ),
    TestCase(
        name="TPE restauration → tranches INSEE",
        user_message="TPE restauration",
        expected_action="extract",
        expected_criteria={
            "taille_entreprise": {
                "present": True,
                "acronyme": "TPE",
                "tranche_effectif": [
                    "0 salarie",
                    "1 ou 2 salaries",
                    "3 a 5 salaries",
                    "6 a 9 salaries"
                ]
            }
        },
        description="Vérifie que TPE est mappé aux bonnes tranches"
    ),
    TestCase(
        name="ETI BTP → tranches INSEE",
        user_message="ETI dans le BTP",
        expected_action="extract",
        expected_criteria={
            "taille_entreprise": {
                "present": True,
                "acronyme": "ETI",
                "tranche_effectif": [
                    "250 a 499 salaries",
                    "500 a 999 salaries",
                    "1 000 a 1 999 salaries",
                    "2 000 a 4 999 salaries"
                ]
            }
        },
        description="Vérifie que ETI est mappé aux bonnes tranches"
    ),
    TestCase(
        name="Grand groupe santé → tranches INSEE",
        user_message="grand groupe dans la santé",
        expected_action="extract",
        expected_criteria={
            "taille_entreprise": {
                "present": True,
                "acronyme": "GE",
                "tranche_effectif": [
                    "5 000 a 9 999 salaries",
                    "10 000 salaries et plus"
                ]
            }
        },
        description="Vérifie que GE/grand groupe est mappé"
    ),
    TestCase(
        name="MIC commerce → tranches INSEE",
        user_message="MIC commerce",
        expected_action="extract",
        expected_criteria={
            "taille_entreprise": {
                "present": True,
                "acronyme": "MIC",
                "tranche_effectif": [
                    "0 salarie",
                    "1 ou 2 salaries",
                    "3 a 5 salaries",
                    "6 a 9 salaries"
                ]
            }
        },
        description="Vérifie que MIC est mappé"
    ),
]

# Tests de requêtes complexes
COMPLEX_TESTS = [
    TestCase(
        name="Multi-critères : PME + secteur + région + CA",
        user_message="PME informatique en Ile-de-France avec CA supérieur à 500k€",
        expected_action="extract",
        expected_criteria={
            "activite": {"present": True},
            "localisation": {"present": True},
            "taille_entreprise": {"present": True},
            "criteres_financiers": {"present": True}
        },
        description="Requête avec 4 critères différents"
    ),
    TestCase(
        name="Secteur + département",
        user_message="restaurants dans le 75",
        expected_action="extract",
        expected_criteria={
            "activite": {"present": True},
            "localisation": {"present": True}
        },
        description="Code postal/département"
    ),
]


# ============================================================================
# API Client
# ============================================================================

class AgentAPIClient:
    """Client pour tester l'API agent"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.conversation_endpoint = f"{self.base_url}/api/conversations"

    def create_conversation(self, user_message: str) -> Dict[str, Any]:
        """Crée une nouvelle conversation avec un message"""
        payload = {"message": user_message}
        response = requests.post(self.conversation_endpoint, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def send_message(self, conversation_id: str, user_message: str) -> Dict[str, Any]:
        """Envoie un message dans une conversation existante"""
        endpoint = f"{self.conversation_endpoint}/{conversation_id}/messages"
        payload = {"message": user_message}
        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()


# ============================================================================
# Test Runner
# ============================================================================

def check_nested_criteria(actual: Dict, expected: Dict, path: str = "") -> tuple[bool, str]:
    """
    Vérifie récursivement que les critères attendus sont présents.

    Returns:
        (success: bool, error_message: str)
    """
    for key, expected_value in expected.items():
        current_path = f"{path}.{key}" if path else key

        if key not in actual:
            return False, f"Clé manquante : {current_path}"

        actual_value = actual[key]

        if isinstance(expected_value, dict):
            if not isinstance(actual_value, dict):
                return False, f"{current_path} : attendu dict, reçu {type(actual_value)}"
            success, msg = check_nested_criteria(actual_value, expected_value, current_path)
            if not success:
                return False, msg

        elif isinstance(expected_value, list):
            if not isinstance(actual_value, list):
                return False, f"{current_path} : attendu list, reçu {type(actual_value)}"
            # Pour les listes, on vérifie que les éléments attendus sont présents
            if set(expected_value) != set(actual_value):
                return False, f"{current_path} : attendu {expected_value}, reçu {actual_value}"

        else:
            # Valeur simple
            if actual_value != expected_value:
                return False, f"{current_path} : attendu {expected_value}, reçu {actual_value}"

    return True, ""


def run_test(client: AgentAPIClient, test_case: TestCase) -> TestResult:
    """Exécute un test"""
    try:
        # Créer conversation et envoyer message
        response = client.create_conversation(test_case.user_message)

        # Récupérer la réponse de l'agent
        messages = response.get("messages", [])
        if len(messages) < 2:
            return TestResult(
                test_case=test_case,
                status=TestStatus.FAILED,
                error_message="Pas assez de messages dans la réponse"
            )

        agent_message = messages[-1]  # Dernier message = réponse agent

        # Vérifier l'action
        conversation_status = response.get("status")

        if test_case.expected_action == "extract":
            if conversation_status != "completed":
                return TestResult(
                    test_case=test_case,
                    status=TestStatus.FAILED,
                    actual_response=response,
                    error_message=f"Attendu status=completed (extract), reçu status={conversation_status}"
                )

            # Vérifier les critères extraits si spécifiés
            if test_case.expected_criteria:
                extraction_result = response.get("extraction_result", {})
                success, error_msg = check_nested_criteria(
                    extraction_result,
                    test_case.expected_criteria
                )

                if not success:
                    return TestResult(
                        test_case=test_case,
                        status=TestStatus.FAILED,
                        actual_response=response,
                        error_message=f"Critères incorrects : {error_msg}"
                    )

        elif test_case.expected_action == "clarify":
            if conversation_status == "completed":
                return TestResult(
                    test_case=test_case,
                    status=TestStatus.FAILED,
                    actual_response=response,
                    error_message=f"Attendu clarification, mais extraction effectuée"
                )

        # Test réussi
        return TestResult(
            test_case=test_case,
            status=TestStatus.PASSED,
            actual_response=response
        )

    except Exception as e:
        return TestResult(
            test_case=test_case,
            status=TestStatus.FAILED,
            error_message=f"Exception : {str(e)}"
        )


def run_test_suite(client: AgentAPIClient, tests: List[TestCase], suite_name: str) -> List[TestResult]:
    """Exécute une suite de tests"""
    print(f"\n{'='*80}")
    print(f"TEST SUITE : {suite_name}")
    print(f"{'='*80}\n")

    results = []
    for i, test_case in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] {test_case.name}...")
        print(f"    → Message : \"{test_case.user_message}\"")
        print(f"    → Attendu : {test_case.expected_action}")

        result = run_test(client, test_case)
        results.append(result)

        if result.status == TestStatus.PASSED:
            print(f"    {TestStatus.PASSED.value}")
        else:
            print(f"    {TestStatus.FAILED.value}")
            if result.error_message:
                print(f"    Erreur : {result.error_message}")
            if result.actual_response:
                print(f"    Réponse : {json.dumps(result.actual_response, indent=2, ensure_ascii=False)[:500]}...")

        print()

    return results


def print_summary(all_results: List[TestResult]):
    """Affiche le résumé des tests"""
    total = len(all_results)
    passed = sum(1 for r in all_results if r.status == TestStatus.PASSED)
    failed = sum(1 for r in all_results if r.status == TestStatus.FAILED)

    print(f"\n{'='*80}")
    print(f"RÉSUMÉ DES TESTS")
    print(f"{'='*80}")
    print(f"Total    : {total}")
    print(f"Réussis  : {passed} ({passed/total*100:.1f}%)")
    print(f"Échoués  : {failed} ({failed/total*100:.1f}%)")
    print(f"{'='*80}\n")

    if failed > 0:
        print("Tests échoués :")
        for result in all_results:
            if result.status == TestStatus.FAILED:
                print(f"  - {result.test_case.name}")
                print(f"    {result.error_message}")
        print()


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Tests poussés pour l'API Agent"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="URL de base de l'API (ex: http://localhost:8000)"
    )
    parser.add_argument(
        "--suite",
        type=str,
        choices=["basic", "clarify", "insee", "complex", "all"],
        default="all",
        help="Suite de tests à exécuter"
    )

    args = parser.parse_args()

    print(f"\n🚀 Démarrage des tests sur : {args.base_url}\n")

    client = AgentAPIClient(args.base_url)

    all_results = []

    if args.suite in ["basic", "all"]:
        results = run_test_suite(client, BASIC_EXTRACT_TESTS, "EXTRACTION BASIQUE")
        all_results.extend(results)

    if args.suite in ["clarify", "all"]:
        results = run_test_suite(client, CLARIFY_TESTS, "CLARIFICATION")
        all_results.extend(results)

    if args.suite in ["insee", "all"]:
        results = run_test_suite(client, INSEE_MAPPING_TESTS, "MAPPING TRANCHES INSEE")
        all_results.extend(results)

    if args.suite in ["complex", "all"]:
        results = run_test_suite(client, COMPLEX_TESTS, "REQUÊTES COMPLEXES")
        all_results.extend(results)

    print_summary(all_results)

    # Exit code
    failed_count = sum(1 for r in all_results if r.status == TestStatus.FAILED)
    exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
