from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.models.db_models import IncidentStatus, ResolutionGeneratedBy, EscalationStatus

class UserBase(BaseModel):
    email: str
    name: Optional[str] = None
    role: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class IncidentBase(BaseModel):
    raw_log: str

class IncidentCreate(IncidentBase):
    pass

class IncidentResponse(IncidentBase):
    id: UUID
    submitted_by: Optional[UUID] = None
    parsed_summary: Optional[str] = None
    status: IncidentStatus
    root_cause: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class ResolutionBase(BaseModel):
    steps: List[str]
    generated_by: ResolutionGeneratedBy
    accepted: Optional[bool] = None

class ResolutionCreate(ResolutionBase):
    pass

class ResolutionResponse(ResolutionBase):
    id: UUID
    incident_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class EscalationBase(BaseModel):
    reason: str

class EscalationCreate(EscalationBase):
    pass

class EscalationResponse(EscalationBase):
    id: UUID
    incident_id: UUID
    assigned_to: Optional[UUID] = None
    status: EscalationStatus
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
