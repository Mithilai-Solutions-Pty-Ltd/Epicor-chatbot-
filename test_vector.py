from dotenv import load_dotenv
load_dotenv()
import os
import requests

# Test locally first
os.environ['SIMILARITY_THRESHOLD'] = '0.3'
from backend.services.vector_service import init_pinecone, query_index
init_pinecone()

print("=" * 60)
print("LOCAL VECTOR SEARCH TEST")
print("=" * 60)

test_questions = [
    "what is BAQ",
    "BPM",
    "Epicor",
    "how to",
    "guide",
    "user",
]

for q in test_questions:
    results = query_index(q, top_k=3)
    status = "✅" if len(results) > 0 else "❌"
    print(f"{status} '{q}' → {len(results)} results", end="")
    if results:
        print(f" | top score: {results[0]['score']}")
    else:
        print()

print()
print("=" * 60)
print("RENDER API TEST")
print("=" * 60)

API = "https://epicor-chatbot-6sb5.onrender.com"

questions = [
    "what is BAQ",
    "what is BPM",
    "what is Epicor",
    "how to create a report",
]

for q in questions:
    try:
        resp = requests.post(
            f"{API}/api/chat/message",
            json={
                "question": q,
                "environment": "prod",
                "user_id": "test"
            },
            timeout=60
        )
        data = resp.json()
        answer = data.get('answer', '')[:100]
        confidence = data.get('confidence', '')
        sources = len(data.get('sources', []))
        found = "✅" if "couldn't find" not in answer else "❌"
        print(f"{found} '{q}'")
        print(f"   Confidence: {confidence} | Sources: {sources}")
        print(f"   Answer: {answer[:80]}")
    except Exception as e:
        print(f"❌ '{q}' → Error: {e}")