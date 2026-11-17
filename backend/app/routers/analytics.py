from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..deps import get_current_user
from ..models import DensityObservation, Detection, Notification, User, utcnow

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
LEVELS = ["safe", "low", "moderate", "high", "critical"]


def _dets(db: Session, user: User, start: datetime | None, end: datetime | None, pest: str | None, crop_id: int | None):
    q = select(Detection).where(Detection.user_id == user.id).options(
        selectinload(Detection.instances), selectinload(Detection.severity), selectinload(Detection.crop))
    if start:
        q = q.where(Detection.created_at >= start)
    if end:
        q = q.where(Detection.created_at <= end)
    if crop_id:
        q = q.where(Detection.crop_id == crop_id)
    rows = db.scalars(q.order_by(Detection.created_at)).all()
    if pest:
        rows = [d for d in rows if any(i.pest_class == pest for i in d.instances)]
    return rows


@router.get("/overview")
def overview(start: datetime | None = None, end: datetime | None = None, pest: str | None = None,
             crop_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dets = _dets(db, user, start, end, pest, crop_id)
    pests = Counter(i.pest_class for d in dets for i in d.instances)
    sev = Counter(d.severity.level for d in dets if d.severity)
    crops = defaultdict(lambda: {"scans": 0, "pests": 0, "high_risk": 0})
    for d in dets:
        c = crops[d.crop.name if d.crop else "Not specified"]
        c["scans"] += 1
        c["pests"] += d.total_count
        c["high_risk"] += int(bool(d.severity and d.severity.level in ("high", "critical")))
    confs = [i.confidence for d in dets for i in d.instances]
    unread = db.scalar(select(Notification.id).where(Notification.user_id == user.id, Notification.is_read.is_(False)).limit(1))
    recent = sorted(dets, key=lambda d: d.created_at, reverse=True)[:6]
    return {
        "total_scans": len(dets),
        "total_pests": sum(d.total_count for d in dets),
        "scans_with_pests": sum(1 for d in dets if d.total_count),
        "most_frequent_pest": pests.most_common(1)[0][0] if pests else None,
        "high_risk_detections": sev.get("high", 0) + sev.get("critical", 0),
        "average_confidence": round(sum(confs) / len(confs), 4) if confs else None,
        "pest_distribution": [{"pest": p, "count": n} for p, n in pests.most_common(12)],
        "severity_distribution": [{"level": l, "count": sev.get(l, 0)} for l in LEVELS],
        "crop_stats": [{"crop": k, **v} for k, v in sorted(crops.items(), key=lambda kv: -kv[1]["scans"])],
        "recent": [{"id": d.id, "created_at": d.created_at, "total_count": d.total_count,
                    "top_pest": Counter(i.pest_class for i in d.instances).most_common(1)[0][0] if d.instances else None,
                    "severity_level": d.severity.level if d.severity else None,
                    "severity_score": d.severity.score if d.severity else None} for d in recent],
        "has_unread_alerts": unread is not None,
    }


@router.get("/trends")
def trends(period: str = Query("daily", pattern="^(daily|weekly|monthly)$"), days: int = Query(90, ge=1, le=730),
           pest: str | None = None, crop_id: int | None = None,
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start = utcnow() - timedelta(days=days)
    dets = _dets(db, user, start, None, pest, crop_id)

    def bucket(dt: datetime) -> str:
        if period == "monthly":
            return dt.strftime("%Y-%m")
        if period == "weekly":
            y, w, _ = dt.isocalendar()
            return f"{y}-W{w:02d}"
        return dt.strftime("%Y-%m-%d")

    agg = defaultdict(lambda: {"scans": 0, "pests": 0, "high_risk": 0, "conf_sum": 0.0, "conf_n": 0, "sev_sum": 0.0})
    for d in dets:
        a = agg[bucket(d.created_at)]
        a["scans"] += 1
        a["pests"] += d.total_count if not pest else sum(i.pest_class == pest for i in d.instances)
        if d.severity:
            a["sev_sum"] += d.severity.score
            a["high_risk"] += d.severity.level in ("high", "critical")
        for i in d.instances:
            a["conf_sum"] += i.confidence
            a["conf_n"] += 1
    series = [{"period": k, "scans": v["scans"], "pests": v["pests"], "high_risk": v["high_risk"],
               "avg_severity": round(v["sev_sum"] / v["scans"], 1) if v["scans"] else 0,
               "avg_confidence": round(v["conf_sum"] / v["conf_n"], 4) if v["conf_n"] else None}
              for k, v in sorted(agg.items())]
    # density history per pest (for the population graph)
    q = select(DensityObservation).where(DensityObservation.user_id == user.id, DensityObservation.created_at >= start)
    if pest:
        q = q.where(DensityObservation.pest_class == pest)
    dens = [{"date": o.created_at, "pest": o.pest_class, "value": o.value, "unit": o.unit, "level": o.level,
             "detection_id": o.detection_id} for o in db.scalars(q.order_by(DensityObservation.created_at))]
    return {"period": period, "series": series, "density": dens}


@router.get("/filters")
def filters(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dets = _dets(db, user, None, None, None, None)
    return {"pests": sorted({i.pest_class for d in dets for i in d.instances}),
            "crops": sorted({(d.crop.id, d.crop.name) for d in dets if d.crop}, key=lambda c: c[1])}
