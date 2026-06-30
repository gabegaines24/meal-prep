"""
Routes for managing the ChromaDB vector index.

POST /ingest/backfill          — embed all existing cached recipes
POST /ingest/document          — upload + chunk + embed a PDF or text file
GET  /ingest/documents         — list indexed documents
DELETE /ingest/documents/{id}  — remove a document from the index
"""

import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import Recipe
from backend.services import embeddings as embed_svc

router = APIRouter()

CHUNK_SIZE = 500      # characters per chunk
CHUNK_OVERLAP = 80    # character overlap between adjacent chunks


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------

def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping character-level chunks."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if c]


def _extract_text(content: bytes, filename: str) -> str:
    """Extract plain text from a PDF or text file."""
    if filename.lower().endswith(".pdf"):
        try:
            import pypdf  # type: ignore
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Could not parse PDF: {exc}",
            )
    # Treat everything else as UTF-8 text
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


# ---------------------------------------------------------------------------
# In-memory document registry (maps doc_id → metadata)
# Persisted implicitly via ChromaDB metadata; reconstructed on query.
# ---------------------------------------------------------------------------

class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    chunks: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/backfill")
def backfill_recipes(db: Session = Depends(get_db)):
    """Embed every cached recipe that is not yet in the vector store."""
    recipes = db.query(Recipe).all()
    if not recipes:
        return {"embedded": 0, "message": "No recipes in database yet."}

    col_ids = set()
    try:
        # Peek at existing IDs to avoid redundant re-embeds
        existing = embed_svc._collection("recipes").get(include=[])
        col_ids = set(existing["ids"])
    except Exception:
        pass

    count = 0
    for recipe in recipes:
        if f"recipe-{recipe.id}" not in col_ids:
            try:
                embed_svc.upsert_recipe(recipe)
                count += 1
            except Exception:
                pass

    return {"embedded": count, "total": len(recipes)}


@router.post("/document", response_model=DocumentInfo)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF or text file, chunk it, and embed it into the documents collection."""
    allowed = {
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/csv",
    }
    if file.content_type and file.content_type not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Use PDF or plain text.",
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File must be smaller than 10 MB.")

    text = _extract_text(content, file.filename or "upload.txt")
    if not text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from the file.")

    chunks = _chunk_text(text)
    doc_id = str(uuid.uuid4())
    filename = file.filename or "upload.txt"

    try:
        embed_svc.upsert_document_chunks(doc_id, filename, chunks)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}")

    return DocumentInfo(doc_id=doc_id, filename=filename, chunks=len(chunks))


@router.get("/documents", response_model=list[DocumentInfo])
def list_documents():
    """Return all documents currently indexed."""
    try:
        col = embed_svc._collection("documents")
        result = col.get(include=["metadatas"])
    except Exception:
        return []

    # Deduplicate by doc_id and count chunks
    seen: dict[str, DocumentInfo] = {}
    for meta in result["metadatas"]:
        doc_id = meta.get("doc_id", "")
        filename = meta.get("filename", "")
        if doc_id not in seen:
            seen[doc_id] = DocumentInfo(doc_id=doc_id, filename=filename, chunks=0)
        seen[doc_id].chunks += 1

    return list(seen.values())


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    """Remove a document and all its chunks from the index."""
    try:
        embed_svc.delete_document(doc_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"deleted": doc_id}
