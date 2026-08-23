import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_authenticated_order_lifecycle():
    with TestClient(app) as client:
        email = f"test-{uuid.uuid4().hex[:10]}@example.com"
        registration = client.post("/api/auth/register", json={"email": email, "password": "safe-password-123"})
        assert registration.status_code == 201
        headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}

        assert client.get("/api/items").status_code == 401
        added = client.post("/api/command", headers=headers, json={"transcript": "Add 2 bottles of water", "language": "en-US"})
        assert added.status_code == 200
        assert added.json()["item"]["category"] == "Beverages"

        order = client.post("/api/orders", headers=headers)
        assert order.status_code == 201
        assert order.json()["status"] == "placed"
        assert order.json()["items"][0]["name"] == "Water"

        delivered = client.patch(f"/api/orders/{order.json()['id']}", headers=headers, json={"status": "delivered"})
        assert delivered.status_code == 200
        assert delivered.json()["status"] == "delivered"
        assert len(client.get("/api/orders", headers=headers).json()) == 1
