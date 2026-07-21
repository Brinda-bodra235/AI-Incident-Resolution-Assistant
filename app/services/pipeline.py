from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from app.config import settings
from app.models.db_models import Incident, IncidentStatus, Resolution, ResolutionGeneratedBy, Escalation, EscalationStatus
from app.services.log_parser import LogParser
from app.services.embeddings import EmbeddingService
from app.services.qdrant_client import QdrantService
from app.services.llm_agent import LLMAgent

class IncidentResolutionPipeline:
    def __init__(self, db: Session, qdrant_service: QdrantService):
        self.db = db
        self.qdrant_service = qdrant_service
        self.embedding_service = EmbeddingService()
        self.llm_agent = LLMAgent()

    def process_incident(self, raw_log: str, submitted_by: uuid.UUID) -> Incident:
        # Step 1: Log Parsing
        parsed_summary = LogParser.parse(raw_log)

        # Step 2: Embedding + Retrieval
        embedding = self.embedding_service.get_embedding(parsed_summary)
        similar_payloads = self.qdrant_service.search_similar_incidents(embedding, limit=5)

        # Retrieve full resolutions from database for similar incidents
        past_resolutions = []
        similar_incidents_for_llm = []
        for payload in similar_payloads:
            inc_id = payload.get("incident_id")
            if inc_id:
                similar_incidents_for_llm.append(payload)
                res_records = self.db.query(Resolution).filter(Resolution.incident_id == uuid.UUID(inc_id)).all()
                for res in res_records:
                    past_resolutions.append(res.steps)

        # Step 3: Root Cause Agent (LLM Call #1)
        root_cause, confidence_score = self.llm_agent.analyze_root_cause(parsed_summary, similar_incidents_for_llm)

        # Step 4: Solution Generator Agent (LLM Call #2)
        steps = self.llm_agent.generate_solution(root_cause, past_resolutions)

        # Step 5 & 6: Decision and Storage
        incident_id = uuid.uuid4()
        status = IncidentStatus.resolved if confidence_score >= settings.CONFIDENCE_THRESHOLD else IncidentStatus.escalated
        resolved_at = datetime.utcnow() if status == IncidentStatus.resolved else None

        # Create Incident record
        db_incident = Incident(
            id=incident_id,
            submitted_by=submitted_by,
            raw_log=raw_log,
            parsed_summary=parsed_summary,
            status=status,
            root_cause=root_cause,
            confidence_score=confidence_score,
            qdrant_point_id=incident_id,
            created_at=datetime.utcnow(),
            resolved_at=resolved_at
        )
        self.db.add(db_incident)
        self.db.flush()

        # Create Resolution record
        db_resolution = Resolution(
            id=uuid.uuid4(),
            incident_id=incident_id,
            steps=steps,
            generated_by=ResolutionGeneratedBy.ai,
            accepted=True if status == IncidentStatus.resolved else False,
            created_at=datetime.utcnow()
        )
        self.db.add(db_resolution)

        # If confidence score is below threshold, create Escalation record
        if status == IncidentStatus.escalated:
            db_escalation = Escalation(
                id=uuid.uuid4(),
                incident_id=incident_id,
                reason=f"Confidence score {confidence_score:.2f} is below threshold {settings.CONFIDENCE_THRESHOLD:.2f}",
                status=EscalationStatus.pending,
                created_at=datetime.utcnow()
            )
            self.db.add(db_escalation)

        self.db.commit()
        self.db.refresh(db_incident)

        # Store in Qdrant
        tags = []
        for word in parsed_summary.split():
            clean_word = "".join(c for c in word if c.isalnum()).lower()
            if "error" in clean_word or "exception" in clean_word:
                tags.append(clean_word)
        tags = list(set(tags))[:3]

        try:
            self.qdrant_service.upsert_incident(
                incident_id=incident_id,
                embedding=embedding,
                root_cause=root_cause,
                status=status.value,
                tags=tags
            )
        except Exception as e:
            # Handle potential Qdrant connection issue gracefully during execution
            print(f"Failed to upsert to Qdrant during pipeline: {e}")

        return db_incident
