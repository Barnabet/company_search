"""
API Transformer Service.

Transforms internal extraction format to external company API format.
"""

from typing import Dict, Any, List, Optional


# Mapping of internal employee size labels to API format
EMPLOYEE_SIZE_MAPPING = {
    "0 salarie": "0 employees",
    "1 ou 2 salaries": "1 to 2 employees",
    "3 a 5 salaries": "3 to 5 employees",
    "6 a 9 salaries": "6 to 9 employees",
    "10 a 19 salaries": "10 to 19 employees",
    "20 a 49 salaries": "20 to 49 employees",
    "50 a 99 salaries": "50 to 99 employees",
    "100 a 199 salaries": "100 to 199 employees",
    "200 a 249 salaries": "200 to 249 employees",
    "250 a 499 salaries": "250 to 499 employees",
    "500 a 999 salaries": "500 to 999 employees",
    "1 000 a 1 999 salaries": "1000 to 1999 employees",
    "2 000 a 4 999 salaries": "2000 to 4999 employees",
    "5 000 a 9 999 salaries": "5000 to 9999 employees",
    "10 000 salaries et plus": "10000+ employees",
}

# Regions list for validation
VALID_REGIONS = [
    "Ile-de-France",
    "Bretagne",
    "Normandie",
    "Occitanie",
    "Nouvelle-Aquitaine",
    "Auvergne-Rhone-Alpes",
    "Provence-Alpes-Cote d'Azur",
    "Pays de la Loire",
    "Hauts-de-France",
    "Grand Est",
    "Centre-Val de Loire",
    "Bourgogne-Franche-Comte",
    "Corse",
    "Guadeloupe",
    "Martinique",
    "Guyane",
    "La Reunion",
    "Mayotte",
]


def _to_array(value: Optional[Any]) -> List[Any]:
    """Convert a value to array if not None."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _transform_employee_sizes(tranches: Optional[List[str]]) -> List[str]:
    """
    Transform internal employee size format to API format.

    Args:
        tranches: List of internal size labels like "10 a 19 salaries"

    Returns:
        List of API format labels like "10 to 19 employees"
    """
    if not tranches:
        return []

    result = []
    for tranche in tranches:
        # Try exact match first
        api_format = EMPLOYEE_SIZE_MAPPING.get(tranche)
        if api_format:
            result.append(api_format)
        else:
            # Try normalized matching (lowercase, no accents)
            tranche_lower = tranche.lower().strip()
            for internal, api in EMPLOYEE_SIZE_MAPPING.items():
                if internal.lower() == tranche_lower:
                    result.append(api)
                    break

    return result


def transform_extraction_to_api_request(
    extraction: Dict[str, Any],
    naf_codes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Transform internal extraction result to external API format.

    Args:
        extraction: Internal extraction result from agent:
            {
                "localisation": {"present": bool, "commune": str, "departement": str, "region": str, "code_postal": str},
                "activite": {"present": bool, "activite_entreprise": str},
                "taille_entreprise": {"present": bool, "tranche_effectif": [], "acronyme": str},
                "criteres_financiers": {"present": bool, "ca_plus_recent": number, ...},
                "criteres_juridiques": {"present": bool, "siege_entreprise": str, ...}
            }
        naf_codes: NAF codes from ActivityMatcher (optional)

    Returns:
        Dict formatted for external API:
            {
                "location": {"present": bool, "city": [], "region": [], ...},
                "activity": {"present": bool, "activity_codes_list": [], "original_activity_request": str},
                "company_size": {"present": bool, "employees_number_range": []},
                "financial_criteria": {"present": bool, "turnover": number, ...},
                "legal_criteria": {"present": bool, "headquarters": bool}
            }
    """
    # Extract sub-dicts with defaults
    localisation = extraction.get("localisation", {})
    activite = extraction.get("activite", {})
    taille = extraction.get("taille_entreprise", {})
    financier = extraction.get("criteres_financiers", {})
    juridique = extraction.get("criteres_juridiques", {})

    # Build location
    location = {
        "present": localisation.get("present", False),
    }
    if location["present"]:
        if localisation.get("commune"):
            location["city"] = _to_array(localisation["commune"])
        if localisation.get("region"):
            location["region"] = _to_array(localisation["region"])
        if localisation.get("departement"):
            location["departement"] = _to_array(localisation["departement"])
        if localisation.get("code_postal"):
            location["post_code"] = _to_array(localisation["code_postal"])

    # Build activity
    activity = {
        "present": activite.get("present", False),
    }
    if activity["present"]:
        # Use provided NAF codes or extract from activite_entreprise
        if naf_codes:
            activity["activity_codes_list"] = naf_codes
        elif activite.get("activite_entreprise"):
            # If it looks like a NAF code (e.g., "6201Z")
            code = activite["activite_entreprise"]
            if len(code) == 5 and code[-1].isalpha():
                activity["activity_codes_list"] = [code]
            else:
                activity["activity_codes_list"] = []
        else:
            activity["activity_codes_list"] = []

        # Original activity request (the human-readable description)
        original_request = activite.get("activite_entreprise")
        if original_request:
            activity["original_activity_request"] = original_request

    # Build company_size
    company_size = {
        "present": taille.get("present", False),
    }
    if company_size["present"]:
        tranches = taille.get("tranche_effectif", [])
        if tranches:
            company_size["employees_number_range"] = _transform_employee_sizes(tranches)

    # Build financial_criteria
    financial_criteria = {
        "present": financier.get("present", False),
    }
    if financial_criteria["present"]:
        if financier.get("ca_plus_recent"):
            financial_criteria["turnover"] = financier["ca_plus_recent"]
        if financier.get("resultat_net_plus_recent"):
            financial_criteria["net_profit"] = financier["resultat_net_plus_recent"]

    # Build legal_criteria
    legal_criteria = {
        "present": juridique.get("present", False),
    }
    if legal_criteria["present"]:
        siege = juridique.get("siege_entreprise")
        if siege:
            # Convert "oui"/"non" or bool to boolean
            if isinstance(siege, bool):
                legal_criteria["headquarters"] = siege
            elif isinstance(siege, str):
                legal_criteria["headquarters"] = siege.lower() in ("oui", "yes", "true", "1")

        if juridique.get("capital"):
            legal_criteria["capital_threshold_sup"] = True

    return {
        "location": location,
        "activity": activity,
        "company_size": company_size,
        "financial_criteria": financial_criteria,
        "legal_criteria": legal_criteria,
    }


def get_criteria_summary(api_request: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary of the search criteria.

    Args:
        api_request: API-formatted request

    Returns:
        Summary string for display to user
    """
    parts = []

    # Activity
    activity = api_request.get("activity", {})
    if activity.get("present"):
        desc = activity.get("original_activity_request")
        if desc:
            parts.append(f"Activite: {desc}")

    # Location
    location = api_request.get("location", {})
    if location.get("present"):
        loc_parts = []
        if location.get("city"):
            loc_parts.append(", ".join(location["city"]))
        if location.get("region"):
            loc_parts.append(", ".join(location["region"]))
        if location.get("departement"):
            loc_parts.append(f"dept. {', '.join(location['departement'])}")
        if loc_parts:
            parts.append(f"Localisation: {' - '.join(loc_parts)}")

    # Size
    company_size = api_request.get("company_size", {})
    if company_size.get("present"):
        sizes = company_size.get("employees_number_range", [])
        if sizes:
            parts.append(f"Taille: {', '.join(sizes)}")

    # Financial
    financial = api_request.get("financial_criteria", {})
    if financial.get("present"):
        if financial.get("turnover"):
            parts.append(f"CA min: {financial['turnover']:,.0f} EUR")

    # Legal
    legal = api_request.get("legal_criteria", {})
    if legal.get("present"):
        if legal.get("headquarters"):
            parts.append("Sieges sociaux uniquement")

    return " | ".join(parts) if parts else "Aucun critere specifie"
