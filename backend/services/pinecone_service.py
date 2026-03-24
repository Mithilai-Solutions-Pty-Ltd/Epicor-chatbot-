"""
============================================================
Pinecone Service
============================================================
Handles:
  • Initialising the Pinecone client
  • Upserting document chunks (called by zoho_sync)
  • Querying the index for RAG retrieval
  • IMPORTANT: Pinecone Serverless indexes are PERSISTENT –
    your chunks are never auto-deleted even on the free tier
    as long as you don't call delete() explicitly.
============================================================
"""

import os
import logging
from typing import List, Dict, Any

from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

logger = logging.getLogger("botzi.pinecone")

# ── Module-level singletons (initialised once on startup) ─
_pinecone_client: Pinecone | None = None
_index = None
_openai_client: OpenAI | None = None


# ── Initialisation ────────────────────────────────────────
def init_pinecone():
    """
    Called once during FastAPI lifespan startup.
    Creates the index if it doesn't exist yet.
    """
    global _pinecone_client, _index, _openai_client

    api_key   = os.environ["PINECONE_API_KEY"]
    index_name = os.environ["PINECONE_INDEX_NAME"]
    environment = os.environ.get("PINECONE_ENVIRONMENT", "us-east-1-aws")

    _pinecone_client = Pinecone(api_key=api_key)
    _openai_client   = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # Create the index on first run (free tier: 1 index, 100k vectors)
    existing = [idx.name for idx in _pinecone_client.list_indexes()]
    if index_name not in existing:
        logger.info(f"Creating Pinecone index: {index_name}")
        # text-embedding-3-small produces 1536-dim vectors
        _pinecone_client.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=environment.replace("-aws", "").replace("us-east-1", "us-east-1"),
            ),
        )
        logger.info("Index created ✅")
    else:
        logger.info(f"Pinecone index '{index_name}' already exists ✅")

    _index = _pinecone_client.Index(index_name)


def get_index():
    """Return the active Pinecone index (raises if not initialised)."""
    if _index is None:
        raise RuntimeError("Pinecone has not been initialised. Call init_pinecone() first.")
    return _index


# ── Embedding helper ──────────────────────────────────────
def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of text strings via OpenAI.
    Returns a list of float vectors (1536 dims each).
    """
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
    response = _openai_client.embeddings.create(input=texts, model=model)
    return [item.embedding for item in response.data]


# ── Upsert (called by zoho_sync) ─────────────────────────
def upsert_chunks(chunks: List[Dict[str, Any]]) -> int:
    """
    Upsert document chunks into Pinecone.

    Each chunk dict must have:
      id       – unique string ID
      text     – the raw text content
      metadata – dict with: source, page, doc_type, file_id, file_name

    Returns number of vectors upserted.
    """
    index = get_index()
    batch_size = 100  # Pinecone recommended batch size

    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    vectors = []
    for chunk, embedding in zip(chunks, embeddings):
        vectors.append({
            "id": chunk["id"],
            "values": embedding,
            "metadata": {
                **chunk["metadata"],
                # Store text for retrieval (max 40 KB metadata per vector)
                "text": chunk["text"][:38000],
            },
        })

    total_upserted = 0
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        index.upsert(vectors=batch)
        total_upserted += len(batch)
        logger.info(f"  Upserted batch {i//batch_size + 1} ({len(batch)} vectors)")

    return total_upserted


# ── Query (called by chat service) ───────────────────────
def query_index(question: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Embed the user's question and retrieve the top-k most similar chunks.

    Returns a list of match dicts:
      {
        "id":    str,
        "score": float,        # cosine similarity 0-1
        "text":  str,
        "source": str,
        "page":   int,
        "file_name": str,
        "doc_type":  str,
      }
    """
    index = get_index()
    threshold = float(os.environ.get("SIMILARITY_THRESHOLD", "0.72"))

    # Embed the question
    [q_embedding] = embed_texts([question])

    # Query Pinecone
    result = index.query(
        vector=q_embedding,
        top_k=top_k,
        include_metadata=True,
    )

    matches = []
    for match in result.matches:
        if match.score < threshold:
            continue  # discard low-confidence chunks
        meta = match.metadata or {}
        matches.append({
            "id":        match.id,
            "score":     round(match.score, 4),
            "text":      meta.get("text", ""),
            "source":    meta.get("source", "Unknown"),
            "page":      int(meta.get("page", 1)),        # Always integer
            "file_name": meta.get("file_name", ""),
            "doc_type":  meta.get("doc_type", ""),
        })

    return matches


# ── Delete by file_id (called on doc update/delete) ──────
def delete_chunks_for_file(file_id: str):
    """
    Remove all vectors whose metadata.file_id matches.
    Called when zoho_sync detects an updated or deleted doc.
    """
    index = get_index()
    # Pinecone free tier supports delete by metadata filter
    index.delete(filter={"file_id": {"$eq": file_id}})
    logger.info(f"Deleted vectors for file_id={file_id}")
