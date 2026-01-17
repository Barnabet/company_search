"""
Location Matcher Service for fuzzy matching of communes, departements, and regions.

Matches user input to exact values from reference lists using normalized text comparison.
"""

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple


@dataclass
class LocationCorrection:
    """Record of a location field correction"""
    original_value: str  # What the user/LLM provided
    matched_value: str  # What we matched it to
    original_field: str  # Original field type (commune, departement, region)
    matched_field: str  # Correct field type after cross-list search
    score: float  # Similarity score

    @property
    def was_corrected(self) -> bool:
        """Returns True if the value or field type was changed"""
        return self.original_value != self.matched_value or self.original_field != self.matched_field

    @property
    def field_changed(self) -> bool:
        """Returns True if the field type was changed"""
        return self.original_field != self.matched_field

# ============================================================================
# Configuration
# ============================================================================

DATA_DIR = Path(__file__).parent.parent / "data"
COMMUNES_FILE = DATA_DIR / "communes.txt"
DEPARTEMENTS_FILE = DATA_DIR / "departements.txt"
REGIONS_FILE = DATA_DIR / "regions.txt"

# Department number to name mapping
DEPARTEMENT_NUMBERS = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence",
    "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardeche", "08": "Ardennes",
    "09": "Ariege", "10": "Aube", "11": "Aude", "12": "Aveyron",
    "13": "Bouches-du-Rhone", "14": "Calvados", "15": "Cantal", "16": "Charente",
    "17": "Charente-Maritime", "18": "Cher", "19": "Correze", "2A": "Corse-du-Sud",
    "2B": "Haute-Corse", "21": "Cote-d'Or", "22": "Cotes-d'Armor", "23": "Creuse",
    "24": "Dordogne", "25": "Doubs", "26": "Drome", "27": "Eure",
    "28": "Eure-et-Loir", "29": "Finistere", "30": "Gard", "31": "Haute-Garonne",
    "32": "Gers", "33": "Gironde", "34": "Herault", "35": "Ille-et-Vilaine",
    "36": "Indre", "37": "Indre-et-Loire", "38": "Isere", "39": "Jura",
    "40": "Landes", "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire",
    "44": "Loire-Atlantique", "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne",
    "48": "Lozere", "49": "Maine-et-Loire", "50": "Manche", "51": "Marne",
    "52": "Haute-Marne", "53": "Mayenne", "54": "Meurthe-et-Moselle", "55": "Meuse",
    "56": "Morbihan", "57": "Moselle", "58": "Nievre", "59": "Nord",
    "60": "Oise", "61": "Orne", "62": "Pas-de-Calais", "63": "Puy-de-Dome",
    "64": "Pyrenees-Atlantiques", "65": "Hautes-Pyrenees", "66": "Pyrenees-Orientales",
    "67": "Bas-Rhin", "68": "Haut-Rhin", "69": "Rhone", "70": "Haute-Saone",
    "71": "Saone-et-Loire", "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie",
    "75": "Paris", "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines",
    "79": "Deux-Sevres", "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne",
    "83": "Var", "84": "Vaucluse", "85": "Vendee", "86": "Vienne",
    "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne", "90": "Territoire de Belfort",
    "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis",
    "94": "Val-de-Marne", "95": "Val-d'Oise",
    # Overseas territories
    "971": "Guadeloupe", "972": "Martinique", "973": "Guyane",
    "974": "La Reunion", "976": "Mayotte", "975": "Saint-Pierre-et-Miquelon",
}


# ============================================================================
# Text Normalization
# ============================================================================

def normalize_text(text: str) -> str:
    """
    Normalize text for fuzzy matching.
    Removes accents, converts to lowercase, strips whitespace.
    """
    # Remove accents
    nfkd = unicodedata.normalize('NFKD', text)
    without_accents = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase and strip
    return without_accents.lower().strip()


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein (edit) distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row are one character longer
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def compute_similarity(s1: str, s2: str) -> float:
    """
    Compute similarity between two strings using Levenshtein distance.
    Returns 1.0 for exact match, lower values for more different strings.
    """
    n1, n2 = normalize_text(s1), normalize_text(s2)

    # Exact match after normalization
    if n1 == n2:
        return 1.0

    if not n1 or not n2:
        return 0.0

    # Levenshtein distance-based similarity
    distance = levenshtein_distance(n1, n2)
    max_len = max(len(n1), len(n2))
    similarity = 1.0 - (distance / max_len)

    return max(0.0, similarity)


# ============================================================================
# Location Matcher
# ============================================================================

class LocationMatcher:
    """Matches user location input to reference values."""

    def __init__(self):
        self.communes: List[str] = []
        self.departements: List[str] = []
        self.regions: List[str] = []
        self._communes_normalized: List[Tuple[str, str]] = []  # (normalized, original)
        self._departements_normalized: List[Tuple[str, str]] = []
        self._regions_normalized: List[Tuple[str, str]] = []
        self._initialized = False

    def initialize(self) -> bool:
        """Load location reference data from files."""
        try:
            # Load communes
            if COMMUNES_FILE.exists():
                with open(COMMUNES_FILE, 'r', encoding='utf-8') as f:
                    self.communes = [line.strip() for line in f if line.strip()]
                self._communes_normalized = [(normalize_text(c), c) for c in self.communes]
                print(f"[LocationMatcher] Loaded {len(self.communes)} communes")

            # Load departements
            if DEPARTEMENTS_FILE.exists():
                with open(DEPARTEMENTS_FILE, 'r', encoding='utf-8') as f:
                    self.departements = [line.strip() for line in f if line.strip()]
                self._departements_normalized = [(normalize_text(d), d) for d in self.departements]
                print(f"[LocationMatcher] Loaded {len(self.departements)} departements")

            # Load regions
            if REGIONS_FILE.exists():
                with open(REGIONS_FILE, 'r', encoding='utf-8') as f:
                    self.regions = [line.strip() for line in f if line.strip()]
                self._regions_normalized = [(normalize_text(r), r) for r in self.regions]
                print(f"[LocationMatcher] Loaded {len(self.regions)} regions")

            self._initialized = True
            return True

        except Exception as e:
            print(f"[LocationMatcher] Failed to initialize: {e}")
            return False

    def match_commune(self, query: str, threshold: float = 0.7) -> Optional[str]:
        """Match a user query to the best commune."""
        return self._find_best_match(query, self._communes_normalized, threshold)

    def match_departement(self, query: str, threshold: float = 0.7) -> Optional[str]:
        """Match a user query to the best departement."""
        return self._find_best_match(query, self._departements_normalized, threshold)

    def match_region(self, query: str, threshold: float = 0.7) -> Optional[str]:
        """Match a user query to the best region."""
        return self._find_best_match(query, self._regions_normalized, threshold)

    def _find_best_match(
        self,
        query: str,
        normalized_list: List[Tuple[str, str]],
        threshold: float
    ) -> Optional[str]:
        """Find the best matching value from a normalized list."""
        if not query or not normalized_list:
            return None

        query_normalized = normalize_text(query)

        # First try exact match on normalized text
        for norm, original in normalized_list:
            if norm == query_normalized:
                return original

        # Then try fuzzy matching
        best_match = None
        best_score = 0.0

        for norm, original in normalized_list:
            score = compute_similarity(query, original)
            if score > best_score:
                best_score = score
                best_match = original

        if best_score >= threshold:
            return best_match

        return None

    def find_best_match_across_all(
        self,
        query: str,
        preferred_type: Optional[str] = None,
        threshold: float = 0.7
    ) -> Optional[Tuple[str, str, float]]:
        """
        Find the best match across all location lists.

        Args:
            query: The location string to match
            preferred_type: If provided, prefer this field type on ties (e.g., "region")
            threshold: Minimum similarity score to accept a match

        Returns:
            Tuple of (matched_value, field_type, score) or None if no match above threshold.
            field_type is one of: "commune", "departement", "region"
        """
        if not query:
            return None

        # Collect all matches with their scores
        all_matches: List[Tuple[str, str, float]] = []  # (value, type, score)

        # Search in all three lists
        for field_type, normalized_list in [
            ("commune", self._communes_normalized),
            ("departement", self._departements_normalized),
            ("region", self._regions_normalized),
        ]:
            query_normalized = normalize_text(query)

            for norm, original in normalized_list:
                # Exact match gets score 1.0
                if norm == query_normalized:
                    all_matches.append((original, field_type, 1.0))
                else:
                    score = compute_similarity(query, original)
                    if score >= threshold:
                        all_matches.append((original, field_type, score))

        if not all_matches:
            return None

        # Sort by score descending
        all_matches.sort(key=lambda x: x[2], reverse=True)

        best_score = all_matches[0][2]

        # Get all matches with the best score (ties)
        tied_matches = [m for m in all_matches if m[2] == best_score]

        if len(tied_matches) == 1:
            return tied_matches[0]

        # On tie, prefer the original field type (agent's guess)
        if preferred_type:
            for match in tied_matches:
                if match[1] == preferred_type:
                    return match

        # Otherwise return the first one
        return tied_matches[0]

    def _split_multi_values(self, value: str) -> List[str]:
        """
        Split a value that may contain multiple locations (comma-separated).
        Returns a list of individual values, stripped of whitespace.
        """
        if not value:
            return []

        # Split by comma and clean up
        parts = [p.strip() for p in value.split(',')]
        # Filter out empty parts
        return [p for p in parts if p]

    def match_locations(self, extraction_result: dict) -> Tuple[dict, List[LocationCorrection]]:
        """
        Apply fuzzy matching to location fields in an extraction result.
        Searches across all lists and assigns to the correct field type.
        Handles comma-separated lists of values (e.g., "Bordeaux, Toulouse").
        Modifies the extraction_result in place and returns it with corrections.

        Returns:
            Tuple of (extraction_result, corrections) where corrections is a list
            of LocationCorrection objects describing what was changed.
        """
        corrections: List[LocationCorrection] = []

        if not self._initialized:
            return extraction_result, corrections

        localisation = extraction_result.get("localisation", {})
        if not localisation or not localisation.get("present"):
            return extraction_result, corrections

        # Handle 2-digit postal codes: convert to department name
        code_postal = localisation.get("code_postal")
        if code_postal:
            code_str = str(code_postal).strip()
            # Check if it's a 2 or 3 digit department number (not a full postal code)
            if len(code_str) <= 3 and code_str.upper() in DEPARTEMENT_NUMBERS:
                dept_name = DEPARTEMENT_NUMBERS[code_str.upper()]
                print(f"[LocationMatcher] Converting 2-digit postal code '{code_str}' to departement '{dept_name}'")

                # Record the correction
                corrections.append(LocationCorrection(
                    original_value=code_str,
                    matched_value=dept_name,
                    original_field="code_postal",
                    matched_field="departement",
                    score=1.0
                ))

                # Move to departement field (only if not already set)
                if not localisation.get("departement"):
                    localisation["departement"] = dept_name

                # Clear the invalid postal code
                localisation["code_postal"] = None

        # Collect all location values to match (supporting multi-values)
        location_values = []  # List of (field, value) tuples
        for field in ["commune", "departement", "region"]:
            value = localisation.get(field)
            if value:
                # Split comma-separated values
                individual_values = self._split_multi_values(value)
                for v in individual_values:
                    location_values.append((field, v))

        # Store matched values by field type (using lists to support multiple values)
        matched_fields: dict[str, List[str]] = {"commune": [], "departement": [], "region": []}

        # Match each value across all lists
        for original_field, value in location_values:
            # Pass original field as preferred type for tie-breaking
            result = self.find_best_match_across_all(value, preferred_type=original_field)

            if result:
                matched_value, correct_field, score = result

                # Add to the list if not already present
                if matched_value not in matched_fields[correct_field]:
                    matched_fields[correct_field].append(matched_value)

                    # Record the correction
                    correction = LocationCorrection(
                        original_value=value,
                        matched_value=matched_value,
                        original_field=original_field,
                        matched_field=correct_field,
                        score=score
                    )
                    corrections.append(correction)

                    if correct_field != original_field:
                        print(f"[LocationMatcher] '{value}' ({original_field}) -> '{matched_value}' ({correct_field}) [score={score:.2f}]")
                    else:
                        print(f"[LocationMatcher] '{value}' -> '{matched_value}' ({correct_field}) [score={score:.2f}]")
            else:
                print(f"[LocationMatcher] '{value}' ({original_field}) -> no match found")
                # Record failed match as correction with no matched value
                corrections.append(LocationCorrection(
                    original_value=value,
                    matched_value="",
                    original_field=original_field,
                    matched_field=original_field,
                    score=0.0
                ))

        # Update localisation with matched values (join multiple values with commas)
        localisation["commune"] = ", ".join(matched_fields["commune"]) if matched_fields["commune"] else None
        localisation["departement"] = ", ".join(matched_fields["departement"]) if matched_fields["departement"] else None
        localisation["region"] = ", ".join(matched_fields["region"]) if matched_fields["region"] else None

        return extraction_result, corrections


# ============================================================================
# Module-level Singleton
# ============================================================================

_location_matcher: Optional[LocationMatcher] = None


def get_location_matcher() -> LocationMatcher:
    """Get or create the singleton LocationMatcher instance."""
    global _location_matcher

    if _location_matcher is None:
        _location_matcher = LocationMatcher()
        _location_matcher.initialize()

    return _location_matcher


# ============================================================================
# CLI for testing
# ============================================================================

if __name__ == "__main__":
    matcher = get_location_matcher()

    # Test cross-list matching
    test_values = [
        "paris",           # Could be commune or departement
        "Lyon",            # Commune
        "rhone",           # Departement
        "ile de france",   # Region
        "bretagne",        # Region
        "marseille",       # Commune
        "bouches du rhone", # Departement
        "haute garonne",   # Departement
        "toulouse",        # Commune
    ]

    print("\nCross-list matching (finds best match across all lists):")
    for q in test_values:
        result = matcher.find_best_match_across_all(q)
        if result:
            value, field_type, score = result
            print(f"  '{q}' -> '{value}' ({field_type}) [score={score:.2f}]")
        else:
            print(f"  '{q}' -> no match")

    # Test full extraction matching
    print("\n\nTesting extraction result matching:")
    test_extraction = {
        "localisation": {
            "present": True,
            "region": "Lyon",  # Wrong! Lyon is a commune
            "departement": "bretagne",  # Wrong! Bretagne is a region
            "commune": None
        }
    }
    print(f"  Input: {test_extraction['localisation']}")
    result, corrections = matcher.match_locations(test_extraction)
    print(f"  Output: {result['localisation']}")
    print("\n  Corrections made:")
    for c in corrections:
        if c.was_corrected:
            print(f"    - '{c.original_value}' ({c.original_field}) -> '{c.matched_value}' ({c.matched_field})")
