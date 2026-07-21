from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database.postgres import get_db
from app.models.db_models import Escalation, EscalationStatus, User
from app.models.schemas import EscalationResponse
from app.routers.auth import get_current_user

router = APIRouter(prefix="/escalations", tags=["escalations"])

@router.get("/", response_model=List[EscalationResponse])
def list_escalations(
    status: EscalationStatus = EscalationStatus.pending,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Escalation).filter(Escalation.status == status)
    return query.all()
