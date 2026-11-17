from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_admin
from ..models import Detection, DetectedInstance, Notification, SeverityAssessment, User

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None


@router.get("/stats")
def stats(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    pests = db.execute(select(DetectedInstance.pest_class, func.count()).group_by(DetectedInstance.pest_class)
                       .order_by(func.count().desc()).limit(10)).all()
    sev = db.execute(select(SeverityAssessment.level, func.count()).group_by(SeverityAssessment.level)).all()
    return {"users": db.scalar(select(func.count(User.id))),
            "active_users": db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))),
            "detections": db.scalar(select(func.count(Detection.id))),
            "pests_detected": db.scalar(select(func.coalesce(func.sum(Detection.total_count), 0))),
            "avg_inference_ms": round(db.scalar(select(func.avg(Detection.inference_ms))) or 0, 1),
            "top_pests": [{"pest": p, "count": n} for p, n in pests],
            "severity": {l: n for l, n in sev},
            "alerts_open": db.scalar(select(func.count(Notification.id)).where(
                Notification.is_read.is_(False), Notification.level.in_(["high", "critical"])))}


@router.get("/users")
def users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Detection.user_id, func.count()).group_by(Detection.user_id)).all())
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "is_active": u.is_active,
             "language": u.language, "created_at": u.created_at, "detections": counts.get(u.id, 0)}
            for u in db.scalars(select(User).order_by(User.created_at.desc()))]


@router.patch("/users/{uid}")
def patch_user(uid: int, body: UserPatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id and (body.role == "farmer" or body.is_active is False):
        raise HTTPException(400, "You cannot demote or disable yourself")
    if body.role is not None:
        if body.role not in ("farmer", "admin"):
            raise HTTPException(422, "role must be farmer or admin")
        u.role = body.role
    if body.is_active is not None:
        u.is_active = body.is_active
    db.commit()
    return {"ok": True}


@router.get("/alerts")
def alert_monitor(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(Notification, User.email).join(User, User.id == Notification.user_id)
                      .where(Notification.level.in_(["high", "critical"]))
                      .order_by(Notification.created_at.desc()).limit(100)).all()
    return [{"id": n.id, "user": email, "title": n.title, "level": n.level, "detection_id": n.detection_id,
             "is_read": n.is_read, "created_at": n.created_at} for n, email in rows]
