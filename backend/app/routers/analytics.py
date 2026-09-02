import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.ml.inference import ModelBundle
from app.models import Prediction, User
from app.schemas import AnalyticsSummary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base = db.query(Prediction).filter(Prediction.owner_id == user.id)
    total = base.count()
    fake_count = base.filter(Prediction.label == "fake").count()
    real_count = base.filter(Prediction.label == "real").count()
    avg_conf = (
        db.query(func.avg(Prediction.confidence)).filter(Prediction.owner_id == user.id).scalar()
        or 0.0
    )

    # Bucket the last 14 days by date in Python rather than SQL — it's a
    # tiny result set (one user, <=14 days) and sidesteps the date-cast
    # differences between SQLite and PostgreSQL entirely.
    since = datetime.datetime.utcnow() - datetime.timedelta(days=13)
    recent = (
        db.query(Prediction.created_at, Prediction.label)
        .filter(Prediction.owner_id == user.id, Prediction.created_at >= since)
        .all()
    )
    by_day_map: dict[str, dict[str, int]] = {}
    for created_at, label in recent:
        day_str = created_at.date().isoformat()
        row = by_day_map.setdefault(day_str, {"date": day_str, "fake": 0, "real": 0})
        if label in ("fake", "real"):
            row[label] += 1
    by_day = sorted(by_day_map.values(), key=lambda r: r["date"])

    by_mode = dict(
        db.query(Prediction.mode, func.count(Prediction.id))
        .filter(Prediction.owner_id == user.id)
        .group_by(Prediction.mode)
        .all()
    )
    by_modality = dict(
        db.query(Prediction.source_type, func.count(Prediction.id))
        .filter(Prediction.owner_id == user.id)
        .group_by(Prediction.source_type)
        .all()
    )

    return AnalyticsSummary(
        total_predictions=total,
        fake_count=fake_count,
        real_count=real_count,
        fake_ratio=round(fake_count / total, 4) if total else 0.0,
        average_confidence=round(float(avg_conf), 4),
        by_day=by_day,
        by_mode=by_mode,
        by_modality=by_modality,
        model_metrics=ModelBundle.metrics(),
    )
