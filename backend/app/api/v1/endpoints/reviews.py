import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_reviewer
from app.schemas.review import ReviewActionRequest
from app.services.review import get_review_queue, process_review_action

router = APIRouter()

@router.get("/queue")
def read_review_queue(
    db: Session = Depends(get_db),
    reviewer_id: str = Depends(get_current_reviewer)
):
    """
    Returns recommendations requiring human action.
    """
    try:
        return {"queue": get_review_queue(db)}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch review queue")

@router.post("/{recommendation_id}/action")
def perform_review_action(
    recommendation_id: uuid.UUID,
    req: ReviewActionRequest,
    db: Session = Depends(get_db),
    reviewer_id: str = Depends(get_current_reviewer)
):
    """
    Performs a human review action (ACCEPT, REJECT, MARK_DIFFERENT, OVERRIDE).
    """
    try:
        result = process_review_action(
            db=db,
            recommendation_id=recommendation_id,
            action=req.action,
            reason=req.reason or "",
            national_material_id=req.national_material_id,
            actor=reviewer_id
        )
        return result
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Review action failed")
