import os
import logging
from typing import List, Dict, Any
from openai import OpenAI
from supabase import create_client

logger = logging.getLogger("botzi.vector")
_openai = None
_sb = None


def init_pinecone():
    global _openai, _sb
    _openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    _sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_KEY"]
    )
    logger.info("✅ Supabase pgvector initialized")


def get_index():
    return _sb


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
    response = _openai.embeddings.create(input=texts, model=model)
    return [item.embedding for item in response.data]


def upsert_chunks(chunks: List[Dict[str, Any]]) -> int:
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)
    rows = []
    for chunk, embedding in zip(chunks, embeddings):
        meta = chunk["metadata"]
        rows.append({
            "id":        chunk["id"],
            "file_id":   meta["file_id"],
            "file_name": meta["file_name"],
            "doc_type":  meta["doc_type"],
            "page":      int(meta["page"]),
            "source":    meta["source"],
            "content":   chunk["text"],
            "embedding": embedding,
        })
    batch_size = 50
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        _sb.table("documents").upsert(batch).execute()
        total += len(batch)
        logger.info(f"  Upserted batch {i//batch_size + 1} ({len(batch)} rows)")
    return total


def query_index(question: str, top_k: int = 5) -> List[Dict[str, Any]]:
    threshold = float(os.environ.get("SIMILARITY_THRESHOLD", "0.55"))
    [q_embedding] = embed_texts([question])
    result = _sb.rpc("match_documents", {
        "query_embedding": q_embedding,
        "match_threshold": threshold,
        "match_count":     top_k,
    }).execute()
    matches = []
    for row in (result.data or []):
        matches.append({
            "id":        row["id"],
            "score":     round(row["similarity"], 4),
            "text":      row["content"],
            "source":    row["source"],
            "page":      int(row["page"]),
            "file_name": row["file_name"],
            "doc_type":  "",
        })
    return matches


def delete_chunks_for_file(file_id: str):
    _sb.table("documents").delete().eq("file_id", file_id).execute()
    logger.info(f"Deleted vectors for file_id={file_id}")


def get_vector_stats() -> Dict:
    result = _sb.table("documents").select(
        "id", count="exact"
    ).execute()
    return {"total_vectors": result.count or 0}