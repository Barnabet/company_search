# sector_matcher.py
"""
Utility module for matching model predictions for libelle_secteur
to exact values from the reference list.
"""

import unicodedata
from pathlib import Path
from typing import Optional, List, Tuple
from difflib import SequenceMatcher


def load_sectors(filepath: str = "data/libelle_secteur.txt") -> List[str]:
    """Load valid sector labels from reference file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Reference file not found: {filepath}")
    
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def normalize_for_comparison(text: str) -> str:
    """
    Normalize a string for fuzzy comparison:
    - NFD decomposition to split accents
    - Remove combining characters (accents)
    - Lowercase
    - Strip extra whitespace
    - Normalize punctuation and special chars
    """
    if not text:
        return ""
    
    # NFD decomposition and remove accents
    text = unicodedata.normalize('NFD', text)
    text = "".join(c for c in text if unicodedata.category(c) != 'Mn')
    
    # Lowercase and normalize whitespace
    text = text.lower().strip()
    text = " ".join(text.split())  # Normalize multiple spaces
    
    # Normalize common variations
    text = text.replace("'", "'").replace("'", "'")
    text = text.replace("–", "-").replace("—", "-")
    
    return text


def string_similarity(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, s1, s2).ratio()


def get_significant_words(text: str) -> set:
    """Extract significant words from text, ignoring common stop words."""
    stop_words = {
        'de', 'du', 'des', 'le', 'la', 'les', 'et', 'en', 'a', 'au', 'aux',
        'd', 'l', 'n', 'c', 'qu', 'sur', 'pour', 'par', 'avec', 'sans',
        'autres', 'autre', 'non', 'hors', 'except', 'exception', 'activites',
        'activite', 'services', 'service'
    }
    words = set(text.lower().split())
    return words - stop_words


def normalize_word(word: str) -> str:
    """Normalize a word by removing common French suffixes (basic stemming)."""
    # Remove common plural/conjugation endings
    if len(word) > 4:
        if word.endswith('s') and not word.endswith('ss'):
            word = word[:-1]
        elif word.endswith('es'):
            word = word[:-2]
        elif word.endswith('ment'):
            word = word[:-4]
    return word


def words_match_fuzzy(word1: str, word2: str) -> bool:
    """Check if two words match, allowing for plural/conjugation variations."""
    # Exact match
    if word1 == word2:
        return True
    # Normalized match (basic stemming)
    if normalize_word(word1) == normalize_word(word2):
        return True
    # One is prefix of other (at least 4 chars)
    if len(word1) >= 4 and len(word2) >= 4:
        if word1.startswith(word2) or word2.startswith(word1):
            return True
    return False


def word_overlap_score(pred: str, ref: str) -> float:
    """
    Calculate word overlap score between prediction and reference.
    Returns a score based on how many significant words from prediction
    appear in the reference, with fuzzy matching for plural/variations.
    """
    pred_words = get_significant_words(pred)
    ref_words = get_significant_words(ref)
    
    if not pred_words:
        return 0.0
    
    # Count how many prediction words match reference words (with fuzzy matching)
    matching_count = 0
    for pw in pred_words:
        for rw in ref_words:
            if words_match_fuzzy(pw, rw):
                matching_count += 1
                break
    
    # Calculate score: percentage of prediction words found in reference
    coverage = matching_count / len(pred_words)
    
    # Bonus if all prediction words are found
    if matching_count == len(pred_words):
        coverage += 0.3
    
    return coverage


def contains_match(prediction: str, reference: str) -> bool:
    """Check if prediction is contained in reference or vice versa."""
    pred_norm = normalize_for_comparison(prediction)
    ref_norm = normalize_for_comparison(reference)
    
    return pred_norm in ref_norm or ref_norm in pred_norm


class SectorMatcher:
    """
    Matches model predictions to exact values from the reference sector list.
    Uses multiple matching strategies:
    1. Exact match (case-insensitive, accent-insensitive)
    2. Containment match (prediction contained in reference)
    3. Fuzzy similarity matching
    """
    
    def __init__(self, sectors_file: str = "data/libelle_secteur.txt"):
        self.sectors = load_sectors(sectors_file)
        self.sectors_normalized = {
            normalize_for_comparison(s): s for s in self.sectors
        }
        # Precompute lowercase versions for faster lookup
        self.sectors_lower = {s.lower(): s for s in self.sectors}
    
    def match(self, prediction: str, threshold: float = 0.6) -> Optional[str]:
        """
        Match a prediction to the closest sector from the reference list.
        
        Args:
            prediction: The model's predicted sector label
            threshold: Minimum similarity score to consider a match (0.0-1.0)
        
        Returns:
            The matched sector from the reference list, or None if no good match
        """
        if not prediction:
            return None
        
        prediction = prediction.strip()
        pred_normalized = normalize_for_comparison(prediction)
        pred_lower = prediction.lower()
        
        # Strategy 1: Exact match (case-insensitive)
        if pred_lower in self.sectors_lower:
            return self.sectors_lower[pred_lower]
        
        # Strategy 2: Normalized exact match (accent-insensitive)
        if pred_normalized in self.sectors_normalized:
            return self.sectors_normalized[pred_normalized]
        
        # Strategy 3: Find best containment match
        # If prediction is a substring of a sector, prefer that sector
        containment_matches = []
        for ref_norm, ref_original in self.sectors_normalized.items():
            if pred_normalized in ref_norm:
                # Prediction is contained in reference - good match
                containment_matches.append((ref_original, len(ref_norm)))
        
        if containment_matches:
            # Return the shortest containing match (most specific)
            containment_matches.sort(key=lambda x: x[1])
            return containment_matches[0][0]
        
        # Strategy 4: Word-based matching (prioritize word overlap over character similarity)
        best_match = None
        best_score = 0.0
        
        for ref_norm, ref_original in self.sectors_normalized.items():
            # Primary score: word overlap (most important)
            word_score = word_overlap_score(pred_normalized, ref_norm)
            
            # Secondary score: character similarity (for tie-breaking)
            char_score = string_similarity(pred_normalized, ref_norm)
            
            # Combined score: word overlap is weighted much higher
            score = (word_score * 0.7) + (char_score * 0.3)
            
            # Bonus for partial containment
            if pred_normalized in ref_norm:
                score += 0.2
            
            if score > best_score:
                best_score = score
                best_match = ref_original
        
        if best_score >= threshold:
            return best_match
        
        return None
    
    def match_or_keep(self, prediction: str, threshold: float = 0.6) -> str:
        """
        Match a prediction to reference, or keep original if no match found.
        
        Args:
            prediction: The model's predicted sector label
            threshold: Minimum similarity score to consider a match
        
        Returns:
            The matched sector or the original prediction
        """
        if not prediction:
            return prediction
        
        matched = self.match(prediction, threshold)
        return matched if matched else prediction
    
    def get_all_sectors(self) -> List[str]:
        """Return the list of all valid sectors."""
        return self.sectors.copy()


# Module-level singleton instance for convenience
_default_matcher: Optional[SectorMatcher] = None


def get_matcher() -> SectorMatcher:
    """Get or create the default SectorMatcher instance."""
    global _default_matcher
    if _default_matcher is None:
        _default_matcher = SectorMatcher()
    return _default_matcher


def match_sector(prediction: str, threshold: float = 0.6) -> Optional[str]:
    """
    Convenience function to match a sector prediction.
    
    Args:
        prediction: The model's predicted sector label
        threshold: Minimum similarity score
    
    Returns:
        The matched sector or None
    """
    return get_matcher().match(prediction, threshold)


def match_sector_or_keep(prediction: str, threshold: float = 0.6) -> str:
    """
    Convenience function to match a sector or keep original.
    
    Args:
        prediction: The model's predicted sector label
        threshold: Minimum similarity score
    
    Returns:
        The matched sector or original prediction
    """
    return get_matcher().match_or_keep(prediction, threshold)


