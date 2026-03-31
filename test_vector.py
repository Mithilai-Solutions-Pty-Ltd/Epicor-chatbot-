from dotenv import load_dotenv
load_dotenv()
import os

# Force low threshold for testing
os.environ['SIMILARITY_THRESHOLD'] = '0.3'

from backend.services.vector_service import init_pinecone, query_index

init_pinecone()

questions = [
    "BPM method directive",
    "BAQ query",
    "Application Studio",
    "how to create job",
    "scheduling",
    "Epicor",
]

for question in questions:
    print(f"\nQuestion: {question}")
    results = query_index(question, top_k=3)
    print(f"Results found: {len(results)}")
    for r in results:
        print(f"  Score: {r['score']} | File: {r['file_name'][:50]}")