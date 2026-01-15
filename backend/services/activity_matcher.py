"""
Activity Matcher Service for semantic search of activities.

Uses OpenAI embeddings API to match user activity descriptions to
reference activities from libelle_activite.txt, then looks up NAF codes.
"""

import json
import os
import pickle
import requests
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import numpy as np

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
DATA_DIR = Path(__file__).parent.parent / "data"
ACTIVITIES_FILE = DATA_DIR / "libelle_activite.txt"
EMBEDDINGS_FILE = DATA_DIR / "activites_embeddings_openai.pkl"
NAF_MAPPING_FILE = DATA_DIR / "naf_mapping.json"

# Cache
_embeddings_cache = None
_activities_cache = None
_naf_mapping_cache = None


def load_activities() -> List[str]:
    """Load activity labels from libelle_activite.txt."""
    global _activities_cache
    if _activities_cache is not None:
        return _activities_cache

    if not ACTIVITIES_FILE.exists():
        raise FileNotFoundError(f"Activities file not found: {ACTIVITIES_FILE}")

    with open(ACTIVITIES_FILE, 'r', encoding='utf-8') as f:
        _activities_cache = [line.strip() for line in f if line.strip()]

    print(f"[ActivityMatcher] Loaded {len(_activities_cache)} activities")
    return _activities_cache


def load_naf_mapping() -> Dict[str, List[str]]:
    """Load NAF code mapping from JSON file."""
    global _naf_mapping_cache

    if _naf_mapping_cache is not None:
        return _naf_mapping_cache

    if not NAF_MAPPING_FILE.exists():
        print(f"[ActivityMatcher] NAF mapping file not found: {NAF_MAPPING_FILE}")
        return {}

    try:
        with open(NAF_MAPPING_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _naf_mapping_cache = {k: v for k, v in data.items() if not k.startswith('_')}
            print(f"[ActivityMatcher] Loaded NAF mapping: {len(_naf_mapping_cache)} entries")
            return _naf_mapping_cache
    except Exception as e:
        print(f"[ActivityMatcher] Failed to load NAF mapping: {e}")
        return {}


def get_openai_embeddings(texts: List[str]) -> Optional[np.ndarray]:
    """
    Get embeddings from OpenAI API.

    Args:
        texts: List of texts to embed

    Returns:
        numpy array of embeddings or None if failed
    """
    if not OPENAI_API_KEY:
        print("[ActivityMatcher] OPENAI_API_KEY not set")
        return None

    try:
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_EMBEDDING_MODEL,
                "input": texts,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        # Extract embeddings in order
        embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
        return np.array(embeddings, dtype=np.float32)

    except Exception as e:
        print(f"[ActivityMatcher] OpenAI API error: {e}")
        return None


def load_or_create_embeddings(activities: List[str], force_recreate: bool = False) -> Optional[np.ndarray]:
    """
    Load embeddings from cache or generate them via OpenAI API.
    """
    global _embeddings_cache

    if _embeddings_cache is not None and not force_recreate:
        return _embeddings_cache

    # Try to load from file
    if EMBEDDINGS_FILE.exists() and not force_recreate:
        try:
            with open(EMBEDDINGS_FILE, 'rb') as f:
                data = pickle.load(f)
                if data.get('activities') == activities and data.get('model') == OPENAI_EMBEDDING_MODEL:
                    _embeddings_cache = data['embeddings']
                    print(f"[ActivityMatcher] Loaded embeddings from cache: {len(activities)} activities")
                    return _embeddings_cache
                else:
                    print("[ActivityMatcher] Cache outdated, regenerating embeddings...")
        except Exception as e:
            print(f"[ActivityMatcher] Failed to load embeddings cache: {e}")

    # Generate embeddings via OpenAI API
    print(f"[ActivityMatcher] Generating embeddings for {len(activities)} activities via OpenAI...")

    # OpenAI has a limit, batch if needed
    batch_size = 100
    all_embeddings = []

    for i in range(0, len(activities), batch_size):
        batch = activities[i:i + batch_size]
        print(f"[ActivityMatcher] Processing batch {i // batch_size + 1}/{(len(activities) + batch_size - 1) // batch_size}")
        embeddings = get_openai_embeddings(batch)
        if embeddings is None:
            print("[ActivityMatcher] Failed to generate embeddings")
            return None
        all_embeddings.append(embeddings)

    _embeddings_cache = np.vstack(all_embeddings)

    # Save to cache
    try:
        EMBEDDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EMBEDDINGS_FILE, 'wb') as f:
            pickle.dump({
                'activities': activities,
                'embeddings': _embeddings_cache,
                'model': OPENAI_EMBEDDING_MODEL,
            }, f)
        print(f"[ActivityMatcher] Saved embeddings to {EMBEDDINGS_FILE}")
    except Exception as e:
        print(f"[ActivityMatcher] Failed to save embeddings: {e}")

    return _embeddings_cache


def semantic_search(query: str, activities: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
    """
    Semantic search among activities using OpenAI embeddings.
    """
    embeddings = load_or_create_embeddings(activities)
    if embeddings is None:
        return []

    # Get query embedding
    query_embedding = get_openai_embeddings([query])
    if query_embedding is None:
        return []

    # Cosine similarity
    query_norm = query_embedding / np.linalg.norm(query_embedding)
    embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    similarities = np.dot(embeddings_norm, query_norm.T).flatten()

    # Get top-k indices
    top_indices = np.argsort(similarities)[::-1][:top_k]

    return [(activities[i], float(similarities[i])) for i in top_indices]


class ActivityMatcher:
    """
    Matches user activity descriptions to NAF codes using semantic search.
    """

    def __init__(self):
        self.activities = load_activities()
        self.naf_mapping = load_naf_mapping()

    def initialize(self):
        """Pre-load embeddings (call on startup)."""
        load_or_create_embeddings(self.activities)

    def find_matching_activities(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[str, float, List[str]]]:
        """
        Find activities matching the user's query with their NAF codes.
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
        """Get NAF codes for a user query."""
        matches = self.find_matching_activities(query, top_k, threshold)

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
        """Get the single best matching activity."""
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


if __name__ == "__main__":
    print("Testing ActivityMatcher with OpenAI embeddings...")

    matcher = get_activity_matcher()

    test_queries = [
        "informatique",
        "restaurant",
        "batiment",
        "coiffure",
        "comptable",
    ]

    print("\nTest searches:")
    for query in test_queries:
        results = matcher.find_matching_activities(query, top_k=3)
        print(f"\n'{query}':")
        for activity, score, naf_codes in results:
            codes_str = ", ".join(naf_codes) if naf_codes else "(no NAF code)"
            print(f"  {score:.3f} - {activity} [{codes_str}]")
