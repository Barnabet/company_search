"""
Activity Matcher Service for semantic search of activities.

Uses file-based embeddings with OpenAI API for similarity search.
"""

import json
import os
import pickle
import unicodedata
import requests
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import numpy as np

# ============================================================================
# Configuration
# ============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

DATA_DIR = Path(__file__).parent.parent / "data"
ACTIVITIES_FILE = DATA_DIR / "libelle_activite.txt"
NAF_MAPPING_FILE = DATA_DIR / "naf_mapping.json"
EMBEDDINGS_FILE = DATA_DIR / "activites_embeddings_openai.pkl"


# ============================================================================
# Text Normalization
# ============================================================================

def normalize_text(text: str) -> str:
    """
    Normalize text for consistent matching.
    Removes accents, converts to lowercase, strips whitespace.
    """
    nfkd = unicodedata.normalize('NFKD', text)
    without_accents = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return without_accents.lower().strip()


# ============================================================================
# OpenAI Embeddings API
# ============================================================================

def get_openai_embedding(text: str) -> Optional[List[float]]:
    """Get embedding for a single text from OpenAI API."""
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
                "input": text,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    except Exception as e:
        print(f"[ActivityMatcher] OpenAI API error: {e}")
        return None


def get_openai_embeddings_batch(texts: List[str]) -> Optional[List[List[float]]]:
    """Get embeddings for multiple texts from OpenAI API."""
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
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        # Sort by index to maintain order
        embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
        return embeddings

    except Exception as e:
        print(f"[ActivityMatcher] OpenAI API error: {e}")
        return None


# ============================================================================
# Activity Matcher
# ============================================================================

class ActivityMatcher:
    """Activity matcher using file-based embeddings."""

    def __init__(self):
        self.activities: List[str] = []
        self.naf_mapping: Dict[str, List[str]] = {}
        self._naf_mapping_normalized: Dict[str, List[str]] = {}  # Normalized key lookup
        self.embeddings: Optional[np.ndarray] = None
        self._initialized = False

    def _get_naf_codes(self, activity: str) -> List[str]:
        """Get NAF codes for an activity, using normalized lookup."""
        # Try exact match first
        if activity in self.naf_mapping:
            return self.naf_mapping[activity]
        # Fall back to normalized lookup
        normalized = normalize_text(activity)
        return self._naf_mapping_normalized.get(normalized, [])

    def initialize(self) -> bool:
        """Load activities, NAF mapping, and embeddings from files."""
        # Load activities
        if not ACTIVITIES_FILE.exists():
            print(f"[ActivityMatcher] Activities file not found: {ACTIVITIES_FILE}")
            return False

        with open(ACTIVITIES_FILE, 'r', encoding='utf-8') as f:
            self.activities = [line.strip() for line in f if line.strip()]

        print(f"[ActivityMatcher] Loaded {len(self.activities)} activities")

        # Load NAF mapping
        if NAF_MAPPING_FILE.exists():
            try:
                with open(NAF_MAPPING_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.naf_mapping = {k: v for k, v in data.items() if not k.startswith('_')}
                    # Build normalized lookup for accent-insensitive matching
                    self._naf_mapping_normalized = {
                        normalize_text(k): v for k, v in self.naf_mapping.items()
                    }
                print(f"[ActivityMatcher] Loaded {len(self.naf_mapping)} NAF mappings")
            except Exception as e:
                print(f"[ActivityMatcher] Failed to load NAF mapping: {e}")

        # Load or create embeddings
        self.embeddings = self._load_or_create_embeddings()
        self._initialized = self.embeddings is not None

        return self._initialized

    def _load_or_create_embeddings(self) -> Optional[np.ndarray]:
        """Load embeddings from cache or generate via OpenAI API."""
        # Try to load from cache
        if EMBEDDINGS_FILE.exists():
            try:
                with open(EMBEDDINGS_FILE, 'rb') as f:
                    data = pickle.load(f)
                    if (data.get('activities') == self.activities and
                        data.get('model') == OPENAI_EMBEDDING_MODEL):
                        print(f"[ActivityMatcher] Loaded embeddings from cache")
                        return data['embeddings']
                    else:
                        print("[ActivityMatcher] Cache outdated, regenerating...")
            except Exception as e:
                print(f"[ActivityMatcher] Failed to load cache: {e}")

        # Generate embeddings
        print(f"[ActivityMatcher] Generating embeddings for {len(self.activities)} activities...")

        all_embeddings = []
        batch_size = 100

        for i in range(0, len(self.activities), batch_size):
            batch = self.activities[i:i + batch_size]
            print(f"[ActivityMatcher] Processing batch {i // batch_size + 1}...")

            embeddings = get_openai_embeddings_batch(batch)
            if embeddings is None:
                print("[ActivityMatcher] Failed to generate embeddings")
                return None

            all_embeddings.extend(embeddings)

        embeddings_array = np.array(all_embeddings, dtype=np.float32)

        # Save to cache
        try:
            EMBEDDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(EMBEDDINGS_FILE, 'wb') as f:
                pickle.dump({
                    'activities': self.activities,
                    'embeddings': embeddings_array,
                    'model': OPENAI_EMBEDDING_MODEL,
                }, f)
            print(f"[ActivityMatcher] Saved embeddings to cache")
        except Exception as e:
            print(f"[ActivityMatcher] Failed to save cache: {e}")

        return embeddings_array

    def find_similar_activities(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[str, float, List[str]]]:
        """Find activities similar to query using cosine similarity."""
        if self.embeddings is None:
            return []

        # Get query embedding
        query_embedding = get_openai_embedding(query)
        if not query_embedding:
            return []

        query_vec = np.array(query_embedding, dtype=np.float32)

        # Cosine similarity
        query_norm = query_vec / np.linalg.norm(query_vec)
        embeddings_norm = self.embeddings / np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        similarities = np.dot(embeddings_norm, query_norm)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            similarity = float(similarities[idx])
            if similarity >= threshold:
                activity = self.activities[idx]
                naf_codes = self._get_naf_codes(activity)
                results.append((activity, similarity, naf_codes))

        return results

    def get_naf_codes_for_query(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = 0.3
    ) -> List[str]:
        """Get NAF codes for a user query."""
        matches = self.find_similar_activities(query, top_k, threshold)

        naf_codes = []
        seen = set()
        for _, _, codes in matches:
            for code in codes:
                if code not in seen:
                    naf_codes.append(code)
                    seen.add(code)

        return naf_codes


# ============================================================================
# Module-level Singleton
# ============================================================================

_activity_matcher: Optional[ActivityMatcher] = None


async def get_activity_matcher() -> ActivityMatcher:
    """Get or create the singleton ActivityMatcher instance."""
    global _activity_matcher

    if _activity_matcher is None:
        _activity_matcher = ActivityMatcher()
        _activity_matcher.initialize()

    return _activity_matcher


def get_activity_matcher_sync() -> ActivityMatcher:
    """Get or create the singleton ActivityMatcher (sync version)."""
    global _activity_matcher

    if _activity_matcher is None:
        _activity_matcher = ActivityMatcher()
        _activity_matcher.initialize()

    return _activity_matcher


# ============================================================================
# CLI for testing
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def test():
        print("Testing ActivityMatcher...")

        matcher = await get_activity_matcher()

        test_queries = [
            "informatique",
            "restaurant",
            "batiment",
            "coiffure",
            "comptable",
        ]

        print("\nTest searches:")
        for query in test_queries:
            results = matcher.find_similar_activities(query, top_k=3)
            print(f"\n'{query}':")
            for activity, score, naf_codes in results:
                codes_str = ", ".join(naf_codes) if naf_codes else "(no NAF code)"
                print(f"  {score:.3f} - {activity} [{codes_str}]")

    asyncio.run(test())
