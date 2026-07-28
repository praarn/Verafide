from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Prediction, User
from app.schemas import PredictionOut

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[PredictionOut])
def list_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        db.query(Prediction)
        .filter(Prediction.owner_id == user.id)
        .order_by(Prediction.created_at.desc())
        .offset(offset)
        .limit(min(limit, 200))
    )
    return query.all()


@router.delete("/{prediction_id}", status_code=204)
def delete_history_item(prediction_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = (
        db.query(Prediction)
        .filter(Prediction.id == prediction_id, Prediction.owner_id == user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Prediction not found.")
    db.delete(item)
    db.commit()
    return None


@router.delete("", status_code=204)
def clear_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Prediction).filter(Prediction.owner_id == user.id).delete()
    db.commit()
    return None
