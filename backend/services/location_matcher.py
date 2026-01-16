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

    def match_locations(self, extraction_result: dict) -> Tuple[dict, List[LocationCorrection]]:
        """
        Apply fuzzy matching to location fields in an extraction result.
        Searches across all lists and assigns to the correct field type.
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

        # Collect all location values to match
        location_values = []
        for field in ["commune", "departement", "region"]:
            value = localisation.get(field)
            if value:
                location_values.append((field, value))

        # Clear existing location fields (we'll repopulate with correct matches)
        matched_fields = {"commune": None, "departement": None, "region": None}

        # Match each value across all lists
        for original_field, value in location_values:
            # Pass original field as preferred type for tie-breaking
            result = self.find_best_match_across_all(value, preferred_type=original_field)

            if result:
                matched_value, correct_field, score = result

                # Only set if not already set (first match wins for each field)
                if matched_fields[correct_field] is None:
                    matched_fields[correct_field] = matched_value

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

        # Update localisation with matched values
        localisation["commune"] = matched_fields["commune"]
        localisation["departement"] = matched_fields["departement"]
        localisation["region"] = matched_fields["region"]

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
