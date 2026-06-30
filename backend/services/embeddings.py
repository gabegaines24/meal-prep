"""
ChromaDB vector store for the meal planner RAG layer.

Collections
-----------
recipes   — one document per cached Recipe row
documents — user-uploaded file chunks (PDF / text)
memory    — condensed per-session conversation summaries

Embedding model: all-MiniLM-L6-v2 (sentence-transformers, local, no API key needed)
"""

import json
import os

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

_CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
_EMBED_MODEL = "all-MiniLM-L6-v2"

_client: chromadb.PersistentClient | None = None
_embed_fn: SentenceTransformerEmbeddingFunction | None = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=_CHROMA_PATH)
    return _client


def _get_embed_fn() -> SentenceTransformerEmbeddingFunction:
    global _embed_fn
    if _embed_fn is None:
        _embed_fn = SentenceTransformerEmbeddingFunction(model_name=_EMBED_MODEL)
    return _embed_fn


def _collection(name: str) -> chromadb.Collection:
    return _get_client().get_or_create_collection(
        name=name,
        embedding_function=_get_embed_fn(),
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Recipe helpers
# ---------------------------------------------------------------------------

def _recipe_doc(recipe) -> str:
    """Build the text that gets embedded for a recipe ORM object."""
    parts = [recipe.title]

    macros: list[str] = []
    if recipe.calories is not None:
        macros.append(f"{recipe.calories:.0f} kcal")
    if recipe.protein is not None:
        macros.append(f"{recipe.protein:.0f}g protein")
    if recipe.carbs is not None:
        macros.append(f"{recipe.carbs:.0f}g carbs")
    if recipe.fat is not None:
        macros.append(f"{recipe.fat:.0f}g fat")
    if macros:
        parts.append("Macros: " + ", ".join(macros))

    if recipe.ingredients_json:
        try:
            ingredients = json.loads(recipe.ingredients_json)
            if ingredients:
                parts.append("Ingredients: " + ", ".join(ingredients[:30]))
        except json.JSONDecodeError:
            pass

    if recipe.instructions_json:
        try:
            steps = json.loads(recipe.instructions_json)
            if steps:
                # Include first few steps so semantic search can match on technique
                parts.append("Instructions: " + " ".join(steps[:5]))
        except json.JSONDecodeError:
            pass

    return ". ".join(parts)


def upsert_recipe(recipe) -> None:
    """Embed and upsert a single Recipe ORM object into the recipes collection."""
    col = _collection("recipes")
    doc = _recipe_doc(recipe)
    meta = {
        "recipe_id": recipe.id,
        "title": recipe.title,
        "calories": float(recipe.calories or 0),
        "protein": float(recipe.protein or 0),
        "carbs": float(recipe.carbs or 0),
        "fat": float(recipe.fat or 0),
        "favorited": bool(recipe.favorited),
    }
    col.upsert(
        ids=[f"recipe-{recipe.id}"],
        documents=[doc],
        metadatas=[meta],
    )


def delete_recipe(recipe_id: int) -> None:
    col = _collection("recipes")
    col.delete(ids=[f"recipe-{recipe_id}"])


def query_recipes(
    text: str,
    n_results: int = 6,
    where: dict | None = None,
) -> list[dict]:
    """
    Semantic search over the recipe collection.

    Returns a list of metadata dicts enriched with `distance` and `document`.
    Lower distance = more similar.
    """
    col = _collection("recipes")
    count = col.count()
    if count == 0:
        return []

    kwargs: dict = {"query_texts": [text], "n_results": min(n_results, count)}
    if where:
        kwargs["where"] = where

    result = col.query(**kwargs)
    hits = []
    for i, meta in enumerate(result["metadatas"][0]):
        hits.append(
            {
                **meta,
                "distance": result["distances"][0][i],
                "document": result["documents"][0][i],
            }
        )
    return hits


# ---------------------------------------------------------------------------
# Document helpers (user-uploaded PDFs / text)
# ---------------------------------------------------------------------------

def upsert_document_chunks(
    doc_id: str,
    filename: str,
    chunks: list[str],
) -> int:
    """Embed and upsert text chunks from an uploaded document."""
    col = _collection("documents")
    ids = [f"doc-{doc_id}-chunk-{i}" for i in range(len(chunks))]
    metas = [{"doc_id": doc_id, "filename": filename, "chunk": i} for i in range(len(chunks))]
    col.upsert(ids=ids, documents=chunks, metadatas=metas)
    return len(chunks)


def delete_document(doc_id: str) -> None:
    col = _collection("documents")
    existing = col.get(where={"doc_id": doc_id})
    if existing["ids"]:
        col.delete(ids=existing["ids"])


def query_documents(text: str, n_results: int = 4) -> list[dict]:
    col = _collection("documents")
    count = col.count()
    if count == 0:
        return []
    result = col.query(
        query_texts=[text],
        n_results=min(n_results, count),
    )
    hits = []
    for i, meta in enumerate(result["metadatas"][0]):
        hits.append(
            {
                **meta,
                "distance": result["distances"][0][i],
                "document": result["documents"][0][i],
            }
        )
    return hits


# ---------------------------------------------------------------------------
# Memory helpers (conversation summaries)
# ---------------------------------------------------------------------------

def upsert_memory(session_id: str, summary: str) -> None:
    col = _collection("memory")
    col.upsert(
        ids=[f"memory-{session_id}"],
        documents=[summary],
        metadatas=[{"session_id": session_id}],
    )


def query_memory(text: str, n_results: int = 3) -> list[str]:
    col = _collection("memory")
    count = col.count()
    if count == 0:
        return []
    result = col.query(
        query_texts=[text],
        n_results=min(n_results, count),
    )
    return result["documents"][0] if result["documents"] else []
