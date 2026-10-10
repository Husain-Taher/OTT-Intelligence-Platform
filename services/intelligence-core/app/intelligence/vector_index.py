"""
Dense Vector Index for OTT Intelligence Platform.
Replaces legacy TF-IDF word overlap with dense semantic embeddings (BAAI/bge-small-en-v1.5).
Provides vector indexing, persistent caching via SQLite/Postgres content_embeddings,
and high-speed vectorized cosine similarity search.
"""
import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from app.models.schemas import CanonicalContent
from app.db.database import save_embedding, get_all_embeddings

MODEL_NAME = "BAAI/bge-small-en-v1.5"
VECTOR_DIM = 384


class DenseVectorIndex:
    _instance = None

    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self._model = None
        self.content_ids: List[str] = []
        self.embeddings_matrix: Optional[np.ndarray] = None  # shape (N, 384)
        self.id_to_idx: Dict[str, int] = {}

    @property
    def model(self):
        if self._model is None:
            try:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(model_name=self.model_name)
            except Exception as e:
                print(f"[VectorIndex] Warning: could not load fastembed ({e}). Using deterministic fallback.")
                self._model = None
        return self._model

    def build_document_corpus(self, item: CanonicalContent) -> str:
        """Constructs rich narrative, thematic, and directorial text representation."""
        parts = [f"{item.title}."]
        if item.tagline:
            parts.append(f"\"{item.tagline}\".")
        if item.overview:
            parts.append(item.overview)
        if item.genres:
            parts.append(f"Genres: {', '.join(item.genres)}.")
        if item.keywords:
            parts.append(f"Keywords: {', '.join(item.keywords[:8])}.")
        if item.directors:
            parts.append(f"Directed by {', '.join(item.directors)}.")
        if item.cast:
            parts.append(f"Starring {', '.join(item.cast[:4])}.")

        prof = item.profile
        if prof and prof.emotions:
            top_emotions = [k for k, v in prof.emotions.items() if v >= 0.4]
            if top_emotions:
                parts.append(f"Emotional tone: {', '.join(top_emotions)}.")

        return " ".join(parts)

    def _fallback_embed(self, text: str) -> np.ndarray:
        """Deterministic pseudo-semantic vector when offline/fallback is active."""
        vec = np.zeros(VECTOR_DIM, dtype=np.float32)
        words = text.lower().split()
        for i, w in enumerate(words):
            h = hash(w) % VECTOR_DIM
            vec[h] += 1.0 / (1.0 + i * 0.1)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def embed_text(self, text: str) -> np.ndarray:
        """Generates a 384-dimensional normalized dense embedding for an input string."""
        if not text.strip():
            return np.zeros(VECTOR_DIM, dtype=np.float32)

        if self.model is not None:
            try:
                res = list(self.model.embed([text]))
                vec = np.array(res[0], dtype=np.float32)
                norm = np.linalg.norm(vec)
                return (vec / norm) if norm > 0 else vec
            except Exception as e:
                print(f"[VectorIndex] Inference error: {e}")

        return self._fallback_embed(text)

    def index_items(self, items: List[CanonicalContent], force_recompute: bool = False) -> int:
        """
        Indexes items into the dense vector space.
        Re-uses stored vectors from content_embeddings when available.
        """
        if not items:
            return 0

        stored_map = {} if force_recompute else get_all_embeddings()
        new_items_to_embed = []
        new_texts_to_embed = []

        self.content_ids = [item.content_id for item in items]
        self.id_to_idx = {cid: idx for idx, cid in enumerate(self.content_ids)}
        matrix_rows = []

        for item in items:
            cid = item.content_id
            if cid in stored_map and len(stored_map[cid]) == VECTOR_DIM:
                vec = np.array(stored_map[cid], dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec /= norm
                matrix_rows.append(vec)
            else:
                corpus = self.build_document_corpus(item)
                new_items_to_embed.append(item)
                new_texts_to_embed.append(corpus)
                matrix_rows.append(None)  # Placeholder

        # Compute missing embeddings in batch
        if new_items_to_embed:
            print(f"[VectorIndex] Computing dense embeddings for {len(new_items_to_embed)} titles...")
            computed_vectors = []
            if self.model is not None:
                try:
                    raw_embeds = list(self.model.embed(new_texts_to_embed))
                    for raw in raw_embeds:
                        v = np.array(raw, dtype=np.float32)
                        norm = np.linalg.norm(v)
                        computed_vectors.append((v / norm) if norm > 0 else v)
                except Exception as e:
                    print(f"[VectorIndex] Batch embed error ({e}), falling back")
                    computed_vectors = [self._fallback_embed(t) for t in new_texts_to_embed]
            else:
                computed_vectors = [self._fallback_embed(t) for t in new_texts_to_embed]

            # Store to DB and fill matrix rows
            for item, corpus, vec in zip(new_items_to_embed, new_texts_to_embed, computed_vectors):
                save_embedding(item.content_id, vec.tolist(), corpus, self.model_name)
                idx = self.id_to_idx[item.content_id]
                matrix_rows[idx] = vec

        self.embeddings_matrix = np.vstack(matrix_rows)
        return len(items)

    def search(self, query: str, top_k: int = 25) -> List[Tuple[str, float]]:
        """
        Executes semantic cosine search returning (content_id, similarity_score).
        """
        if self.embeddings_matrix is None or len(self.content_ids) == 0:
            return []

        q_vec = self.embed_text(query)
        # Cosine similarity via dot product (both normalized)
        sims = np.dot(self.embeddings_matrix, q_vec)

        top_indices = np.argsort(-sims)[:top_k]
        results = []
        for idx in top_indices:
            score = float(sims[idx])
            results.append((self.content_ids[idx], round(score, 4)))
        return results

    def find_similar(self, source_content_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Finds conceptually most similar films to a given content_id in vector space.
        """
        if self.embeddings_matrix is None or source_content_id not in self.id_to_idx:
            return []

        src_idx = self.id_to_idx[source_content_id]
        src_vec = self.embeddings_matrix[src_idx]

        sims = np.dot(self.embeddings_matrix, src_vec)
        top_indices = np.argsort(-sims)

        results = []
        for idx in top_indices:
            cid = self.content_ids[idx]
            if cid != source_content_id:
                results.append((cid, round(float(sims[idx]), 4)))
                if len(results) >= top_k:
                    break
        return results
