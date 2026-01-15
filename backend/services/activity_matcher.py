"""
Activity Matcher Service for semantic search of activities.

Uses sentence-transformers to match user activity descriptions to
reference activities from libelle_activite.txt, then looks up NAF codes.
"""

import json
import pickle
from pathlib import Path
from typing import List, Optional, Tuple, Dict

# Lazy imports - only load when needed
_model = None
_embeddings_cache = None
_naf_mapping_cache = None

# Configuration
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
DATA_DIR = Path(__file__).parent.parent / "data"
ACTIVITIES_FILE = DATA_DIR / "libelle_activite.txt"
EMBEDDINGS_FILE = DATA_DIR / "activites_embeddings.pkl"
NAF_MAPPING_FILE = DATA_DIR / "naf_mapping.json"


def get_model():
    """
    Load sentence-transformers model (lazy loading).

    Returns:
        SentenceTransformer model or None if unavailable
    """
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(MODEL_NAME)
            print(f"[ActivityMatcher] Loaded embedding model: {MODEL_NAME}")
        except ImportError:
            print("[ActivityMatcher] sentence-transformers not installed, falling back to text matching")
            return None
        except Exception as e:
            print(f"[ActivityMatcher] Failed to load embedding model: {e}")
            return None
    return _model


def load_activities() -> List[str]:
    """
    Load activity labels from libelle_activite.txt.

    Returns:
        List of activity labels (729 entries)
    """
    if not ACTIVITIES_FILE.exists():
        raise FileNotFoundError(f"Activities file not found: {ACTIVITIES_FILE}")

    with open(ACTIVITIES_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def load_naf_mapping() -> Dict[str, List[str]]:
    """
    Load NAF code mapping from JSON file.

    Returns:
        Dict mapping activity labels to NAF code arrays
    """
    global _naf_mapping_cache

    if _naf_mapping_cache is not None:
        return _naf_mapping_cache

    if not NAF_MAPPING_FILE.exists():
        print(f"[ActivityMatcher] NAF mapping file not found: {NAF_MAPPING_FILE}")
        return {}

    try:
        with open(NAF_MAPPING_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Filter out comment keys
            _naf_mapping_cache = {k: v for k, v in data.items() if not k.startswith('_')}
            print(f"[ActivityMatcher] Loaded NAF mapping: {len(_naf_mapping_cache)} entries")
            return _naf_mapping_cache
    except Exception as e:
        print(f"[ActivityMatcher] Failed to load NAF mapping: {e}")
        return {}


def load_or_create_embeddings(activities: List[str], force_recreate: bool = False):
    """
    Load embeddings from cache or generate them.

    Args:
        activities: List of activity labels to embed
        force_recreate: Force regeneration of embeddings

    Returns:
        numpy array of shape (n_activities, embedding_dim) or None if failed
    """
    global _embeddings_cache

    if _embeddings_cache is not None and not force_recreate:
        return _embeddings_cache

    # Try to load from file
    if EMBEDDINGS_FILE.exists() and not force_recreate:
        try:
            with open(EMBEDDINGS_FILE, 'rb') as f:
                data = pickle.load(f)
                # Verify activities match
                if data.get('activities') == activities:
                    _embeddings_cache = data['embeddings']
                    print(f"[ActivityMatcher] Loaded embeddings from cache: {len(activities)} activities")
                    return _embeddings_cache
                else:
                    print("[ActivityMatcher] Activities changed, regenerating embeddings...")
        except Exception as e:
            print(f"[ActivityMatcher] Failed to load embeddings cache: {e}")

    # Generate embeddings
    model = get_model()
    if model is None:
        return None

    try:
        import numpy as np
        print(f"[ActivityMatcher] Generating embeddings for {len(activities)} activities...")
        embeddings = model.encode(activities, convert_to_numpy=True, show_progress_bar=False)

        # Save to cache
        EMBEDDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EMBEDDINGS_FILE, 'wb') as f:
            pickle.dump({'activities': activities, 'embeddings': embeddings}, f)
        print(f"[ActivityMatcher] Saved embeddings to {EMBEDDINGS_FILE}")

        _embeddings_cache = embeddings
        return embeddings

    except Exception as e:
        print(f"[ActivityMatcher] Failed to generate embeddings: {e}")
        return None


def semantic_search(query: str, activities: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
    """
    Semantic search among activities using embeddings.

    Args:
        query: User search query (activity description)
        activities: List of reference activities
        top_k: Number of top results to return

    Returns:
        List of (activity_label, similarity_score) tuples, sorted by score descending
    """
    model = get_model()
    embeddings = load_or_create_embeddings(activities)

    if model is None or embeddings is None:
        return []  # Fallback to text matching in caller

    try:
        import numpy as np

        # Encode query
        query_embedding = model.encode([query], convert_to_numpy=True, show_progress_bar=False)

        # Cosine similarity
        similarities = np.dot(embeddings, query_embedding.T).flatten()

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [(activities[i], float(similarities[i])) for i in top_indices]

    except Exception as e:
        print(f"[ActivityMatcher] Semantic search failed: {e}")
        return []


class ActivityMatcher:
    """
    Matches user activity descriptions to NAF codes using semantic search.

    Uses embeddings to find the best matching activities from libelle_activite.txt,
    then looks up corresponding NAF codes from naf_mapping.json.
    """

    def __init__(self):
        self.activities = load_activities()
        self.naf_mapping = load_naf_mapping()
        self._initialized = False

    def initialize(self):
        """Pre-load embeddings (call on startup for better performance)."""
        if not self._initialized:
            load_or_create_embeddings(self.activities)
            self._initialized = True

    def find_matching_activities(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[str, float, List[str]]]:
        """
        Find activities matching the user's query with their NAF codes.

        Args:
            query: User's activity description (e.g., "services informatiques")
            top_k: Number of top results to return
            threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of (activity_label, similarity_score, naf_codes) tuples
        """
        if not query:
            return []

        results = semantic_search(query, self.activities, top_k)

        matched = []
        for activity, score in results:
            if score >= threshold:
                naf_codes = self.naf_mapping.get(activity, [])
                matched.append((activity, score, naf_codes))

        return matched

    def get_naf_codes_for_query(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = 0.3
    ) -> List[str]:
        """
        Get NAF codes for a user query.

        Args:
            query: User's activity description
            top_k: Number of top activities to consider
            threshold: Minimum similarity score

        Returns:
            List of unique NAF codes from matched activities
        """
        matches = self.find_matching_activities(query, top_k, threshold)

        # Collect unique NAF codes
        naf_codes = []
        seen = set()
        for _, _, codes in matches:
            for code in codes:
                if code not in seen:
                    naf_codes.append(code)
                    seen.add(code)

        return naf_codes

    def get_best_match(
        self,
        query: str,
        threshold: float = 0.3
    ) -> Optional[Tuple[str, float, List[str]]]:
        """
        Get the single best matching activity.

        Args:
            query: User's activity description
            threshold: Minimum similarity score

        Returns:
            (activity_label, score, naf_codes) or None if no match above threshold
        """
        matches = self.find_matching_activities(query, top_k=1, threshold=threshold)
        return matches[0] if matches else None


# Module-level singleton
_activity_matcher: Optional[ActivityMatcher] = None


def get_activity_matcher() -> ActivityMatcher:
    """Get or create the singleton ActivityMatcher instance."""
    global _activity_matcher
    if _activity_matcher is None:
        _activity_matcher = ActivityMatcher()
    return _activity_matcher


# Script to pre-generate embeddings
if __name__ == "__main__":
    print("Generating activity embeddings...")

    matcher = get_activity_matcher()
    matcher.initialize()

    # Test searches
    test_queries = [
        "informatique",
        "restaurant",
        "batiment",
        "coiffure",
        "comptable",
        "avocat",
        "boulangerie",
    ]

    print("\nTest searches:")
    for query in test_queries:
        results = matcher.find_matching_activities(query, top_k=3)
        print(f"\n'{query}':")
        for activity, score, naf_codes in results:
            codes_str = ", ".join(naf_codes) if naf_codes else "(no NAF code)"
            print(f"  {score:.3f} - {activity} [{codes_str}]")
