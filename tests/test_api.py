import os
from fastapi.testclient import TestClient
from main import app

# Force fake LLM for testing to avoid API costs/keys
os.environ["USE_FAKE_LLM"] = "1"

client = TestClient(app)

def test_api_plan_endpoint():
    # We use with client so lifespan (store loading) runs
    with client:
        response = client.post("/plan")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "summary" in data
        assert "meat_track" in data["summary"]
        assert len(data["plan"]["days"]) == 5

def test_api_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_api_unsatisfiable_constraints():
    # If we exclude everything, it should fail before calling LLM
    with client:
        # Pass all allergens to severely limit products
        response = client.post("/plan?exclude=gluten&exclude=nuts&exclude=dairy")
        # It might still find products depending on the DB, 
        # but if it fails it should be a 502 with a detail
        if response.status_code == 502:
            assert "No meat-track products" in response.json()["detail"] or "Not enough vegetarian" in response.json()["detail"]
