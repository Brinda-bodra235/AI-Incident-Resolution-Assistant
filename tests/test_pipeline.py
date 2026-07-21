import pytest
from unittest.mock import MagicMock
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.postgres import Base
from app.services.log_parser import LogParser
from app.services.pipeline import IncidentResolutionPipeline
from app.models.db_models import IncidentStatus, Escalation

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_log_parser():
    raw_log = "2026-07-20T12:15:25 ERROR ConnectionTimeoutException: Unable to connect to postgres database at port 5432\n  at db.py line 45\n  at main.py line 12"
    summary = LogParser.parse(raw_log)
    
    assert "[ERROR]" in summary
    assert "ConnectionTimeoutException" in summary
    assert "2026-07-20T12:15:25" in summary
    assert "Stack Trace" in summary

def test_pipeline_escalation_logic(db_session, monkeypatch):
    mock_qdrant = MagicMock()
    mock_qdrant.search_similar_incidents.return_value = []
    mock_qdrant.upsert_incident.return_value = None

    monkeypatch.setattr("app.services.embeddings.EmbeddingService.get_embedding", lambda self, text: [0.1] * 1536)
    monkeypatch.setattr("app.services.llm_agent.LLMAgent.analyze_root_cause", lambda self, parsed_summary, similar_incidents: ("Mock Database Issue", 0.50))
    monkeypatch.setattr("app.services.llm_agent.LLMAgent.generate_solution", lambda self, root_cause, resolutions: ["Check db url", "Restart db"])

    pipeline = IncidentResolutionPipeline(db_session, mock_qdrant)
    user_id = uuid.uuid4()
    
    incident = pipeline.process_incident("ERROR: database disconnected", user_id)
    
    assert incident.status == IncidentStatus.escalated
    assert incident.confidence_score == 0.50
    
    escalation = db_session.query(Escalation).filter(Escalation.incident_id == incident.id).first()
    assert escalation is not None
    assert "Confidence score" in escalation.reason

def test_pipeline_resolved_logic(db_session, monkeypatch):
    mock_qdrant = MagicMock()
    mock_qdrant.search_similar_incidents.return_value = []
    mock_qdrant.upsert_incident.return_value = None

    monkeypatch.setattr("app.services.embeddings.EmbeddingService.get_embedding", lambda self, text: [0.1] * 1536)
    monkeypatch.setattr("app.services.llm_agent.LLMAgent.analyze_root_cause", lambda self, parsed_summary, similar_incidents: ("Mock Database Issue", 0.95))
    monkeypatch.setattr("app.services.llm_agent.LLMAgent.generate_solution", lambda self, root_cause, resolutions: ["Check db url", "Restart db"])

    pipeline = IncidentResolutionPipeline(db_session, mock_qdrant)
    user_id = uuid.uuid4()
    
    incident = pipeline.process_incident("ERROR: database disconnected", user_id)
    
    assert incident.status == IncidentStatus.resolved
    assert incident.confidence_score == 0.95
    
    escalation = db_session.query(Escalation).filter(Escalation.incident_id == incident.id).first()
    assert escalation is None
