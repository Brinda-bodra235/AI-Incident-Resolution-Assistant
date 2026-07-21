import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database.postgres import Base

class IncidentStatus(str, enum.Enum):
    open = "open"
    analyzing = "analyzing"
    resolved = "resolved"
    escalated = "escalated"

class ResolutionGeneratedBy(str, enum.Enum):
    ai = "ai"
    human = "human"

class EscalationStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    closed = "closed"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    role = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    incidents = relationship("Incident", back_populates="submitter")
    escalations = relationship("Escalation", back_populates="assignee")

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    raw_log = Column(Text)
    parsed_summary = Column(Text)
    status = Column(SQLEnum(IncidentStatus), default=IncidentStatus.open)
    root_cause = Column(Text)
    confidence_score = Column(Float)
    qdrant_point_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)

    # Relationships
    submitter = relationship("User", back_populates="incidents")
    resolutions = relationship("Resolution", back_populates="incident")
    escalations = relationship("Escalation", back_populates="incident")

class Resolution(Base):
    __tablename__ = "resolutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"))
    steps = Column(JSON)
    generated_by = Column(SQLEnum(ResolutionGeneratedBy))
    accepted = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    incident = relationship("Incident", back_populates="resolutions")

class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"))
    reason = Column(Text)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status = Column(SQLEnum(EscalationStatus), default=EscalationStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    incident = relationship("Incident", back_populates="escalations")
    assignee = relationship("User", back_populates="escalations")
