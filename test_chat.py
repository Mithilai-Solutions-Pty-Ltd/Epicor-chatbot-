from dotenv import load_dotenv
load_dotenv()
import requests

# Replace with your exact Render URL
API_URL = "https://epicor-chatbot-6sb5.onrender.com"

# First ping to wake up
print("Waking up server...")
try:
    ping = requests.get(f"{API_URL}/api/ping", timeout=60)
    print("Ping status:", ping.status_code)
except Exception as e:
    print("Ping failed:", e)

# Test chat
print("\nTesting chat...")
try:
    resp = requests.post(
        f"{API_URL}/api/chat/message",
        json={
            "question": "What is BAQ in Epicor?",
            "environment": "prod",
            "user_id": "test"
        },
        timeout=60
    )
    print("Status:", resp.status_code)
    print("Response:", resp.text[:500])
except Exception as e:
    print("Chat failed:", e)