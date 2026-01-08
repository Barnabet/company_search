"""
Embedding service for semantic search.

Uses sentence-transformers to compare user input with reference sectors.
Falls back to text matching if embeddings are unavailable.
"""

import pickle
from pathlib import Path
from typing import List, Optional, Tuple

# Lazy imports - only load when needed
_model = None
_embeddings_cache = None

# Model configuration
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDINGS_FILE = Path(__file__).parent.parent / "data" / "secteurs_embeddings.pkl"


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
            print(f"Loaded embedding model: {MODEL_NAME}")
        except ImportError:
            print("sentence-transformers not installed, falling back to text matching")
            return None
        except Exception as e:
            print(f"Failed to load embedding model: {e}")
            return None
    return _model


def load_or_create_embeddings(sectors: List[str], force_recreate: bool = False):
    """
    Load embeddings from cache or generate them.

    Args:
        sectors: List of sector names to embed
        force_recreate: Force regeneration of embeddings

    Returns:
        numpy array of shape (n_sectors, embedding_dim) or None if failed
    """
    global _embeddings_cache

    if _embeddings_cache is not None and not force_recreate:
        return _embeddings_cache

    # Try to load from file
    if EMBEDDINGS_FILE.exists() and not force_recreate:
        try:
            with open(EMBEDDINGS_FILE, 'rb') as f:
                data = pickle.load(f)
                # Verify sectors match
                if data.get('sectors') == sectors:
                    _embeddings_cache = data['embeddings']
                    print(f"Loaded embeddings from cache: {len(sectors)} sectors")
                    return _embeddings_cache
                else:
                    print("Sectors changed, regenerating embeddings...")
        except Exception as e:
            print(f"Failed to load embeddings cache: {e}")

    # Generate embeddings
    model = get_model()
    if model is None:
        return None

    try:
        import numpy as np
        print(f"Generating embeddings for {len(sectors)} sectors...")
        embeddings = model.encode(sectors, convert_to_numpy=True, show_progress_bar=False)

        # Save to cache
        EMBEDDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EMBEDDINGS_FILE, 'wb') as f:
            pickle.dump({'sectors': sectors, 'embeddings': embeddings}, f)
        print(f"Saved embeddings to {EMBEDDINGS_FILE}")

        _embeddings_cache = embeddings
        return embeddings

    except Exception as e:
        print(f"Failed to generate embeddings: {e}")
        return None


def semantic_search(query: str, sectors: List[str], top_k: int = 3) -> List[Tuple[str, float]]:
    """
    Semantic search among sectors using embeddings.

    Args:
        query: User search query
        sectors: List of reference sectors
        top_k: Number of top results to return

    Returns:
        List of (sector, similarity_score) tuples, sorted by score descending
    """
    model = get_model()
    embeddings = load_or_create_embeddings(sectors)

    if model is None or embeddings is None:
        return []  # Fallback to text matching

    try:
        import numpy as np

        # Encode query
        query_embedding = model.encode([query], convert_to_numpy=True, show_progress_bar=False)

        # Cosine similarity
        similarities = np.dot(embeddings, query_embedding.T).flatten()

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [(sectors[i], float(similarities[i])) for i in top_indices]

    except Exception as e:
        print(f"Semantic search failed: {e}")
        return []


def find_best_sector(query: str, sectors: List[str], threshold: float = 0.4) -> Optional[str]:
    """
    Find the best matching sector for a query.

    Args:
        query: User search query
        sectors: List of reference sectors
        threshold: Minimum similarity score to consider a match

    Returns:
        Best matching sector or None if no good match
    """
    results = semantic_search(query, sectors, top_k=1)

    if results and results[0][1] >= threshold:
        return results[0][0]

    return None


# Script to pre-generate embeddings
if __name__ == "__main__":
    from pathlib import Path
    import sys

    # Load sectors
    sectors_file = Path(__file__).parent.parent / "data" / "libelle_secteur.txt"
    if not sectors_file.exists():
        print(f"Sectors file not found: {sectors_file}")
        sys.exit(1)

    with open(sectors_file, 'r', encoding='utf-8') as f:
        sectors = [line.strip() for line in f if line.strip()]

    print(f"Loaded {len(sectors)} sectors from {sectors_file}")

    # Generate embeddings
    embeddings = load_or_create_embeddings(sectors, force_recreate=True)

    if embeddings is not None:
        print(f"Successfully generated embeddings: shape {embeddings.shape}")

        # Test search
        test_queries = ["informatique", "restaurant", "batiment", "santé", "conseil"]
        print("\nTest searches:")
        for query in test_queries:
            results = semantic_search(query, sectors, top_k=3)
            print(f"\n'{query}':")
            for sector, score in results:
                print(f"  {score:.3f} - {sector}")
    else:
        print("Failed to generate embeddings")
        sys.exit(1)
