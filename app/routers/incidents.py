import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.db_models import User, Incident, Resolution, Escalation, IncidentStatus, EscalationStatus
from app.models.schemas import IncidentResponse, IncidentCreate
from app.routers.auth import get_current_user
from app.services.qdrant_client import get_qdrant_service, QdrantService
from app.services.pipeline import IncidentResolutionPipeline

router = APIRouter(prefix="/incidents", tags=["incidents"])

@router.post("/", response_model=IncidentResponse)
def submit_incident(
    incident_in: IncidentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    qdrant_service: QdrantService = Depends(get_qdrant_service)
):
    pipeline = IncidentResolutionPipeline(db, qdrant_service)
    try:
        incident = pipeline.process_incident(incident_in.raw_log, current_user.id)
        return incident
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")

@router.get("/{id}")
def get_incident(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).filter(Incident.id == id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    resolutions = db.query(Resolution).filter(Resolution.incident_id == id).all()
    escalations = db.query(Escalation).filter(Escalation.incident_id == id).all()
    
    return {
        "incident": incident,
        "resolutions": resolutions,
        "escalations": escalations
    }

@router.get("/", response_model=List[IncidentResponse])
def list_incidents(
    status: Optional[IncidentStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Incident)
    if status:
        query = query.filter(Incident.status == status)
    if start_date:
        query = query.filter(Incident.created_at >= start_date)
    if end_date:
        query = query.filter(Incident.created_at <= end_date)
    return query.all()

@router.post("/{id}/escalate")
def escalate_incident(
    id: uuid.UUID,
    reason_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).filter(Incident.id == id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    incident.status = IncidentStatus.escalated
    
    escalation = db.query(Escalation).filter(Escalation.incident_id == id).first()
    if not escalation:
        escalation = Escalation(
            id=uuid.uuid4(),
            incident_id=id,
            reason=reason_data.get("reason", "Manually escalated"),
            status=EscalationStatus.pending,
            created_at=datetime.utcnow()
        )
        db.add(escalation)
    else:
        escalation.reason = reason_data.get("reason", escalation.reason)
        escalation.status = EscalationStatus.pending
        
    db.commit()
    return {"message": "Incident escalated successfully", "incident_id": id}

@router.post("/{id}/feedback")
def mark_feedback(
    id: uuid.UUID,
    feedback_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    qdrant_service: QdrantService = Depends(get_qdrant_service)
):
    incident = db.query(Incident).filter(Incident.id == id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    accepted = feedback_data.get("accepted", False)
    
    resolution = db.query(Resolution).filter(Resolution.incident_id == id).first()
    if resolution:
        resolution.accepted = accepted
        
    if accepted:
        incident.status = IncidentStatus.resolved
        incident.resolved_at = datetime.utcnow()
    else:
        incident.status = IncidentStatus.escalated
        escalation = db.query(Escalation).filter(Escalation.incident_id == id).first()
        if not escalation:
            escalation = Escalation(
                id=uuid.uuid4(),
                incident_id=id,
                reason="User rejected AI resolution suggestion.",
                status=EscalationStatus.pending,
                created_at=datetime.utcnow()
            )
            db.add(escalation)
            
    db.commit()

    try:
        qdrant_service.client.set_payload(
            collection_name="incident_logs",
            payload={"status": incident.status.value},
            points=[str(id)]
        )
    except Exception as e:
        print(f"Failed to update Qdrant payload: {e}")

    return {"message": "Feedback recorded successfully", "incident_status": incident.status}
