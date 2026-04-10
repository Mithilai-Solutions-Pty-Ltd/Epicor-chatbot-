from dotenv import load_dotenv
load_dotenv()
import os, requests

API = "http://localhost:8000"

print("=" * 60)
print("BOTZI FULL LOCAL TEST")
print("=" * 60)

# Check 1 - Health
print("\n1. Health check...")
try:
    r = requests.get(f"{API}/api/health", timeout=30)
    data = r.json()
    status = data.get('status')
    print(f"   Status: {status}")
    print(f"   Uptime: {data.get('uptime_s')} seconds")
    print(f"   Result: {'✅ OK' if status == 'healthy' else '❌ FAIL'}")
except Exception as e:
    print(f"   Result: ❌ FAIL — {e}")

# Check 2 - Ping
print("\n2. Ping check...")
try:
    r = requests.get(f"{API}/api/ping", timeout=30)
    print(f"   Status code: {r.status_code}")
    print(f"   Result: {'✅ OK' if r.status_code == 200 else '❌ FAIL'}")
except Exception as e:
    print(f"   Result: ❌ FAIL — {e}")

# Check 3 - BAQ question
print("\n3. BAQ question...")
try:
    r = requests.post(f"{API}/api/chat/message",
        json={"question": "What is BAQ in Epicor?",
              "environment": "prod", "user_id": "localtest"},
        timeout=60)
    data = r.json()
    answer = data.get('answer', '')
    found = "couldn't find" not in answer.lower()
    print(f"   Confidence: {data.get('confidence')}")
    print(f"   Sources: {len(data.get('sources', []))}")
    print(f"   Answer: {answer[:100]}")
    print(f"   Result: {'✅ OK' if found else '❌ NO ANSWER'}")
except Exception as e:
    print(f"   Result: ❌ FAIL — {e}")

# Check 4 - BPM question
print("\n4. BPM question...")
try:
    r = requests.post(f"{API}/api/chat/message",
        json={"question": "How to create BPM method directive?",
              "environment": "prod", "user_id": "localtest"},
        timeout=60)
    data = r.json()
    answer = data.get('answer', '')
    found = "couldn't find" not in answer.lower()
    print(f"   Confidence: {data.get('confidence')}")
    print(f"   Sources: {len(data.get('sources', []))}")
    print(f"   Answer: {answer[:100]}")
    print(f"   Result: {'✅ OK' if found else '❌ NO ANSWER'}")
except Exception as e:
    print(f"   Result: ❌ FAIL — {e}")

# Check 5 - App Studio question
print("\n5. App Studio question...")
try:
    r = requests.post(f"{API}/api/chat/message",
        json={"question": "What is Application Studio in Epicor?",
              "environment": "prod", "user_id": "localtest"},
        timeout=60)
    data = r.json()
    answer = data.get('answer', '')
    found = "couldn't find" not in answer.lower()
    print(f"   Confidence: {data.get('confidence')}")
    print(f"   Sources: {len(data.get('sources', []))}")
    print(f"   Answer: {answer[:100]}")
    print(f"   Result: {'✅ OK' if found else '❌ NO ANSWER'}")
except Exception as e:
    print(f"   Result: ❌ FAIL — {e}")

# Check 6 - Scheduling question
print("\n6. Scheduling question...")
try:
    r = requests.post(f"{API}/api/chat/message",
        json={"question": "How does scheduling work in Epicor?",
              "environment": "prod", "user_id": "localtest"},
        timeout=60)
    data = r.json()
    answer = data.get('answer', '')
    found = "couldn't find" not in answer.lower()
    print(f"   Confidence: {data.get('confidence')}")
    print(f"   Sources: {len(data.get('sources', []))}")
    print(f"   Result: {'✅ OK' if found else '❌ NO ANSWER'}")
except Exception as e:
    print(f"   Result: ❌ FAIL — {e}")

# Check 7 - Cliq endpoint
print("\n7. Cliq endpoint...")
try:
    r = requests.post(f"{API}/api/cliq/message",
        json={"message": "test", "user_id": "localtest"},
        timeout=30)
    print(f"   Status code: {r.status_code}")
    print(f"   Result: {'✅ OK' if r.status_code == 200 else '⚠️ CHECK CLIQ'}")
except Exception as e:
    print(f"   Result: ❌ FAIL — {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print(f"\nLocal API:    {API}/api/health")
print(f"Swagger UI:   {API}/docs")
print(f"Render API:   https://epicor-chatbot-6sb5.onrender.com/api/health")