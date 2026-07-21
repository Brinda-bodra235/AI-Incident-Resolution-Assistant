import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import uuid

from app.main import app
from app.database.postgres import Base, get_db
from app.services.qdrant_client import get_qdrant_service
from app.models.db_models import User, Incident, Resolution, Escalation

# Use a file-based SQLite inside /tmp (Docker container) to avoid
# cross-connection issues that plague :memory: with TestClient.
SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/test_endpoints.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    test_user = User(
        id=uuid.uuid4(),
        email="testoperator@example.com",
        name="Test Operator",
        role="operator"
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_submit_incident_endpoint(db_session, monkeypatch):
    app.dependency_overrides[get_db] = lambda: db_session

    mock_qdrant = MagicMock()
    mock_qdrant.search_similar_incidents.return_value = []
    mock_qdrant.upsert_incident.return_value = None
    app.dependency_overrides[get_qdrant_service] = lambda: mock_qdrant

    monkeypatch.setattr("app.services.embeddings.EmbeddingService.get_embedding", lambda self, text: [0.1] * 1536)
    monkeypatch.setattr("app.services.llm_agent.LLMAgent.analyze_root_cause", lambda self, parsed_summary, similar_incidents: ("Mock Connection Issue", 0.90))
    monkeypatch.setattr("app.services.llm_agent.LLMAgent.generate_solution", lambda self, root_cause, resolutions: ["Check connection", "Retry"])

    login_response = client.post(
        "/auth/login",
        data={"username": "testoperator@example.com", "password": "password"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"raw_log": "CRITICAL: unable to connect to db"}
    response = client.post("/incidents/", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["raw_log"] == "CRITICAL: unable to connect to db"
    assert data["status"] == "resolved"
    assert data["confidence_score"] == 0.90
    assert data["root_cause"] == "Mock Connection Issue"

    app.dependency_overrides.clear()
