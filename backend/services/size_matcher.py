"""
Size Matcher Service for transforming simple size expressions to INSEE employee ranges.

Converts expressions like '<10', '>500', '10-50', 'TPE', 'PME' to proper INSEE tranches.
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass


# ============================================================================
# INSEE Employee Ranges (ordered by size)
# ============================================================================

INSEE_RANGES = [
    ("0 salarie", 0, 0),
    ("1 ou 2 salaries", 1, 2),
    ("3 a 5 salaries", 3, 5),
    ("6 a 9 salaries", 6, 9),
    ("10 a 19 salaries", 10, 19),
    ("20 a 49 salaries", 20, 49),
    ("50 a 99 salaries", 50, 99),
    ("100 a 199 salaries", 100, 199),
    ("200 a 249 salaries", 200, 249),
    ("250 a 499 salaries", 250, 499),
    ("500 a 999 salaries", 500, 999),
    ("1 000 a 1 999 salaries", 1000, 1999),
    ("2 000 a 4 999 salaries", 2000, 4999),
    ("5 000 a 9 999 salaries", 5000, 9999),
    ("10 000 salaries et plus", 10000, float('inf')),
]

# Acronym mappings
ACRONYM_RANGES = {
    "MIC": ["0 salarie", "1 ou 2 salaries", "3 a 5 salaries", "6 a 9 salaries"],
    "TPE": ["0 salarie", "1 ou 2 salaries", "3 a 5 salaries", "6 a 9 salaries"],
    "PME": ["10 a 19 salaries", "20 a 49 salaries", "50 a 99 salaries", "100 a 199 salaries", "200 a 249 salaries"],
    "ETI": ["250 a 499 salaries", "500 a 999 salaries", "1 000 a 1 999 salaries", "2 000 a 4 999 salaries"],
    "GE": ["5 000 a 9 999 salaries", "10 000 salaries et plus"],
}

# Acronym boundaries for display
ACRONYM_BOUNDARIES = {
    "MIC": (0, 9),
    "TPE": (0, 9),
    "PME": (10, 249),
    "ETI": (250, 4999),
    "GE": (5000, float('inf')),
}


@dataclass
class SizeMatchResult:
    """Result of size expression parsing"""
    tranches: List[str]  # INSEE range strings
    acronyme: Optional[str]  # Detected or computed acronym
    original_expression: str  # Original input
    min_employees: Optional[int]  # Minimum employees (for display)
    max_employees: Optional[int]  # Maximum employees (for display)


def _get_ranges_for_bounds(min_val: int, max_val: float) -> List[str]:
    """Get INSEE ranges that fall within the given bounds.

    Uses range_max for both checks:
    - range_max >= min_val: the range reaches our minimum (has values at or above min_val)
    - range_max <= max_val: the range doesn't exceed our maximum

    This ensures that for '<=500', we exclude '500 to 999' (max 999 > 500).
    """
    result = []
    for label, range_min, range_max in INSEE_RANGES:
        # Include range if its max reaches our min AND stays within our max
        if range_max >= min_val and range_max <= max_val:
            result.append(label)
    return result


def _detect_acronym(min_val: int, max_val: float) -> Optional[str]:
    """Detect the best matching acronym for given bounds."""
    for acronym, (acr_min, acr_max) in ACRONYM_BOUNDARIES.items():
        if min_val == acr_min and max_val == acr_max:
            return acronym
    return None


def parse_size_expression(expression: str) -> Optional[SizeMatchResult]:
    """
    Parse a size expression and return the matching INSEE ranges.

    Supported formats:
    - Acronyms: 'TPE', 'PME', 'ETI', 'GE', 'MIC'
    - Less than: '<10', '< 50', '<= 100'
    - Greater than: '>500', '> 100', '>= 250'
    - Range: '10-50', '10 - 50', '10 à 50', '10 a 50'
    - Exact: '50' (treated as that exact range)
    - Combined: '>10 AND <50', '>= 10 ET <= 100'

    Returns None if expression cannot be parsed.
    """
    if not expression:
        return None

    expr = expression.strip().upper()

    # Check for acronym first
    for acronym in ACRONYM_RANGES:
        if expr == acronym:
            min_val, max_val = ACRONYM_BOUNDARIES[acronym]
            return SizeMatchResult(
                tranches=ACRONYM_RANGES[acronym],
                acronyme=acronym,
                original_expression=expression,
                min_employees=min_val,
                max_employees=int(max_val) if max_val != float('inf') else None
            )

    # Try to parse as combined expression (e.g., '>10 AND <50')
    and_match = re.match(r'([<>=\d\s]+)\s*(?:AND|ET|&)\s*([<>=\d\s]+)', expr, re.IGNORECASE)
    if and_match:
        left, right = and_match.groups()
        min_val = 0
        max_val = float('inf')

        # Parse left part
        left_match = re.match(r'([<>=]+)\s*(\d+)', left.strip())
        if left_match:
            op, val = left_match.groups()
            val = int(val)
            if '>' in op:
                min_val = val + 1 if '=' not in op else val
            elif '<' in op:
                max_val = val - 1 if '=' not in op else val

        # Parse right part
        right_match = re.match(r'([<>=]+)\s*(\d+)', right.strip())
        if right_match:
            op, val = right_match.groups()
            val = int(val)
            if '>' in op:
                min_val = val + 1 if '=' not in op else val
            elif '<' in op:
                max_val = val - 1 if '=' not in op else val

        tranches = _get_ranges_for_bounds(min_val, max_val)
        if tranches:
            return SizeMatchResult(
                tranches=tranches,
                acronyme=_detect_acronym(min_val, max_val),
                original_expression=expression,
                min_employees=min_val,
                max_employees=int(max_val) if max_val != float('inf') else None
            )

    # Try to parse as range (e.g., '10-50', '10 à 50')
    range_match = re.match(r'(\d+)\s*[-àa]\s*(\d+)', expr, re.IGNORECASE)
    if range_match:
        min_val, max_val = int(range_match.group(1)), int(range_match.group(2))
        tranches = _get_ranges_for_bounds(min_val, max_val)
        if tranches:
            return SizeMatchResult(
                tranches=tranches,
                acronyme=_detect_acronym(min_val, max_val),
                original_expression=expression,
                min_employees=min_val,
                max_employees=max_val
            )

    # Try to parse as comparison (e.g., '<10', '>500', '>=100')
    comp_match = re.match(r'([<>=]+)\s*(\d+)', expr)
    if comp_match:
        op, val = comp_match.groups()
        val = int(val)

        if '<' in op:
            max_val = val - 1 if '=' not in op else val
            min_val = 0
        elif '>' in op:
            min_val = val + 1 if '=' not in op else val
            max_val = float('inf')
        else:
            return None

        tranches = _get_ranges_for_bounds(min_val, max_val)
        if tranches:
            return SizeMatchResult(
                tranches=tranches,
                acronyme=_detect_acronym(min_val, max_val),
                original_expression=expression,
                min_employees=min_val,
                max_employees=int(max_val) if max_val != float('inf') else None
            )

    # Try to parse as exact number (find the range containing this number)
    exact_match = re.match(r'^(\d+)$', expr)
    if exact_match:
        val = int(exact_match.group(1))
        tranches = _get_ranges_for_bounds(val, val)
        if tranches:
            return SizeMatchResult(
                tranches=tranches,
                acronyme=None,
                original_expression=expression,
                min_employees=val,
                max_employees=val
            )

    return None


def transform_size_field(extraction_result: dict) -> Tuple[dict, Optional[str]]:
    """
    Transform the taille_entreprise field in an extraction result.

    Converts simple expressions to proper INSEE tranches.

    Args:
        extraction_result: The extraction result dict

    Returns:
        Tuple of (modified extraction_result, correction description or None)
    """
    taille = extraction_result.get("taille_entreprise", {})
    if not taille or not taille.get("present"):
        return extraction_result, None

    # Check if there's a simple expression to transform
    # The model will output either 'effectif_expression' (new) or 'acronyme' (legacy)
    expression = taille.get("effectif_expression") or taille.get("acronyme")

    if not expression:
        # No expression to transform, check if tranches already set
        if taille.get("tranche_effectif"):
            return extraction_result, None
        return extraction_result, None

    # Parse the expression
    result = parse_size_expression(expression)

    if result:
        # Update the extraction with proper values
        taille["tranche_effectif"] = result.tranches
        taille["acronyme"] = result.acronyme

        # Remove the raw expression field
        if "effectif_expression" in taille:
            del taille["effectif_expression"]

        correction = None
        if result.original_expression.upper() not in ACRONYM_RANGES:
            # It was an expression, not an acronym - note the transformation
            correction = f"'{result.original_expression}' → {len(result.tranches)} tranches INSEE"
            print(f"[SizeMatcher] {correction}")

        return extraction_result, correction
    else:
        print(f"[SizeMatcher] Could not parse expression: '{expression}'")
        return extraction_result, None


# ============================================================================
# CLI for testing
# ============================================================================

if __name__ == "__main__":
    test_expressions = [
        "TPE",
        "PME",
        "ETI",
        "GE",
        "<10",
        ">500",
        ">=100",
        "<=50",
        "10-50",
        "10 à 250",
        ">10 AND <100",
        ">=50 ET <=500",
        "50",
        "1000",
    ]

    print("Size Expression Parser Test\n")
    for expr in test_expressions:
        result = parse_size_expression(expr)
        if result:
            print(f"'{expr}':")
            print(f"  Tranches: {result.tranches}")
            print(f"  Acronyme: {result.acronyme}")
            print(f"  Range: {result.min_employees} - {result.max_employees or '∞'}")
            print()
        else:
            print(f"'{expr}': Could not parse\n")
