import httpx
import asyncio
import json
import uuid

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_backend():
    print("--- Starting End-to-End Tests ---")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health Check
        print("\n1. Testing /health endpoint...")
        res = await client.get("http://127.0.0.1:8000/health")
        print(f"Status: {res.status_code}, Response: {res.text}")

        # 2. Session Init (Guest Mode)
        print("\n2. Testing /session/init (Guest)...")
        guest_session_id = f"guest-{uuid.uuid4()}"
        res = await client.post(f"{BASE_URL}/session/init", json={"mode": "guest", "guest_session_id": guest_session_id})
        print(f"Status: {res.status_code}")
        session_data = res.json()
        print(f"Response: {session_data}")
        session_id = session_data["session_id"]
        
        # 3. Chat (B2C)
        print("\n3. Testing /chat/message (B2C - Mixologist)...")
        res = await client.post(f"{BASE_URL}/chat/message", json={"session_id": session_id, "content": "I want a sweet cocktail for a date"}, headers={"Accept": "text/event-stream"})
        print(f"Status: {res.status_code}")
        print("SSE Output Stream (first 500 chars):")
        print(res.text[:500] + "...\n")
        
        # 4. Chat (B2B)
        print("\n4. Testing /chat/message (B2B - Cost Calculator)...")
        res = await client.post(f"{BASE_URL}/chat/message", json={"session_id": session_id, "content": "Can you calculate the cost for a Margarita?"}, headers={"Accept": "text/event-stream"})
        print(f"Status: {res.status_code}")
        print("SSE Output Stream (first 500 chars):")
        print(res.text[:500] + "...\n")

        # 5. Tool direct call: /tools/calculate_cost
        print("\n5. Testing /tools/calculate_cost...")
        recipe = [
            {"ingredient": "Tequila", "amount_ml": 50},
            {"ingredient": "Lime Juice", "amount_ml": 20},
            {"ingredient": "Cointreau", "amount_ml": 20}
        ]
        res = await client.post(f"{BASE_URL}/tools/calculate_cost", json={"recipe": recipe})
        print(f"Status: {res.status_code}, Response: {res.text}")
        
        # 6. User Migration (Guest to User)
        print("\n6. Testing /session/migrate (Guest to User)...")
        user_id = str(uuid.uuid4())
        res = await client.post(f"{BASE_URL}/session/migrate", json={"guest_session_id": session_id, "user_id": user_id})
        # Note: If the user doesn't exist in Supabase auth, it might return 400. Let's see what happens.
        print(f"Status: {res.status_code}, Response: {res.text}")

        # 7. Chat History
        print(f"\n7. Testing /chat/history?user_id={user_id}...")
        res = await client.get(f"{BASE_URL}/chat/history?user_id={user_id}")
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            history = res.json()
            print(f"Total Conversations: {len(history.get('conversations', []))}")
            if history.get('conversations'):
                print(f"First Conversation Title: {history['conversations'][0].get('title')}")

if __name__ == "__main__":
    asyncio.run(test_backend())
