import os
import sys
import logging
import gc
import tempfile
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("botzi.sync_one")


def process_one(
    file_id: str,
    file_name: str,
    modified: str,
    doc_type: str,
    is_update: bool,
):
    from zoho_sync.sync_service import (
        get_zoho_access_token,
        download_file_to_path,
        extract_text_from_path,
        split_into_chunks,
        update_sync_log,
    )
    from backend.services.vector_service import (
        init_pinecone,
        upsert_chunks,
        delete_chunks_for_file,
    )

    init_pinecone()
    token = get_zoho_access_token()

    chunk_size = int(os.getenv("CHUNK_SIZE", "800"))
    overlap    = int(os.getenv("CHUNK_OVERLAP", "100"))

    logger.info("Processing: %s", file_name)

    # Download to temp file on disk — never loads full bytes into RAM
    with tempfile.NamedTemporaryFile(suffix=f".{doc_type}", delete=True) as tmp:
        download_file_to_path(file_id, token, tmp.name)
        pages = extract_text_from_path(tmp.name, doc_type)
    # tmp file deleted here automatically

    gc.collect()

    if not pages:
        logger.warning("No text extracted from %s — marking as synced", file_name)
        update_sync_log(file_id, file_name, modified, 0)
        return

    # Split into chunks
    chunks = split_into_chunks(
        pages, file_id, file_name, doc_type,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    del pages
    gc.collect()

    # Delete old vectors if updating
    if is_update:
        delete_chunks_for_file(file_id)
        logger.info("Deleted old vectors for %s", file_name)

    # Upsert new vectors
    upserted = upsert_chunks(chunks)
    del chunks
    gc.collect()

    # Update sync log
    update_sync_log(file_id, file_name, modified, upserted)
    logger.info("✅ %s — %d vectors upserted", file_name, upserted)


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python -m zoho_sync.sync_one_file file_id file_name modified doc_type is_update")
        sys.exit(1)

    file_id   = sys.argv[1]
    file_name = sys.argv[2]
    modified  = sys.argv[3]
    doc_type  = sys.argv[4]
    is_update = sys.argv[5].lower() == "true"

    process_one(file_id, file_name, modified, doc_type, is_update)