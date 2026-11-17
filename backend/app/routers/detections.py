from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..config import get_settings
from ..db import get_db
from ..deps import get_current_user
from ..limiter import limiter
from ..models import Detection, DetectedInstance, SeverityAssessment, User
from ..schemas import DetectionOut, DetectionSummary, Paginated
from ..services import detector, pipeline, reports, storage
from ..services.knowledge import find_treatment, treatment_payload

router = APIRouter(prefix="/api/detections", tags=["detections"])
settings = get_settings()
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
SAMPLE_TYPES = {"field_photo", "sticky_trap", "leaf_sample"}


def summary(d: Detection) -> dict:
    counts = Counter(i.pest_class for i in d.instances)
    return dict(id=d.id, created_at=d.created_at, total_count=d.total_count, status=d.status,
                crop_name=d.crop.name if d.crop else None, growth_stage=d.growth_stage,
                severity_level=d.severity.level if d.severity else None,
                severity_score=d.severity.score if d.severity else None,
                top_pest=counts.most_common(1)[0][0] if counts else None, mean_confidence=d.mean_confidence,
                image_url=storage.signed_url(d.image_key), annotated_url=storage.signed_url(d.annotated_key))


def full(d: Detection, warnings: list[str] | None = None) -> DetectionOut:
    return DetectionOut(**summary(d), image_width=d.image_width, image_height=d.image_height,
                        inference_ms=d.inference_ms, low_confidence_count=d.low_confidence_count,
                        sample_type=d.sample_type, trap_area_cm2=d.trap_area_cm2, observation_hours=d.observation_hours,
                        notes=d.notes, class_counts=dict(Counter(i.pest_class for i in d.instances).most_common()),
                        instances=d.instances, severity=d.severity, densities=d.densities,
                        model_version=d.model_version.version if d.model_version else None, warnings=warnings or [])


def _owned(db: Session, user: User, det_id: int) -> Detection:
    d = db.get(Detection, det_id)
    if not d or (d.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Detection not found")
    return d


async def _read_upload(f: UploadFile) -> bytes:
    if f.content_type not in ALLOWED:
        raise HTTPException(415, f"Unsupported file type '{f.content_type}'. Upload JPEG, PNG or WebP.")
    data = await f.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image larger than {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(400, "Empty file")
    return data


def _run(db, user, data, crop_id, growth_stage, farm_id, sample_type, trap_area_cm2, observation_hours, notes):
    if sample_type not in SAMPLE_TYPES:
        raise HTTPException(422, f"sample_type must be one of {sorted(SAMPLE_TYPES)}")
    if farm_id and not any(f.id == farm_id for f in user.farms):
        raise HTTPException(404, "Farm not found")
    try:
        return pipeline.analyze(db, user, data, crop_id=crop_id, growth_stage=growth_stage, farm_id=farm_id,
                                sample_type=sample_type, trap_area_cm2=trap_area_cm2,
                                observation_hours=observation_hours, notes=notes)
    except detector.InvalidImage as e:
        raise HTTPException(422, str(e))
    except detector.ModelUnavailable as e:
        raise HTTPException(503, str(e))
    except storage.StorageError as e:
        raise HTTPException(502, f"Could not store image: {e}")


@router.post("/analyze", response_model=DetectionOut, status_code=201)
@limiter.limit(settings.rate_limit_detect)
async def analyze(request: Request, image: UploadFile = File(...), crop_id: int | None = Form(None),
                  growth_stage: str | None = Form(None), farm_id: int | None = Form(None),
                  sample_type: str = Form("field_photo"), trap_area_cm2: float | None = Form(None, gt=0),
                  observation_hours: float | None = Form(None, gt=0), notes: str | None = Form(None, max_length=500),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = await _read_upload(image)
    det, warnings = _run(db, user, data, crop_id, growth_stage, farm_id, sample_type, trap_area_cm2, observation_hours, notes)
    return full(det, warnings)


@router.post("/batch", response_model=list[DetectionOut], status_code=201)
@limiter.limit("5/minute")
async def batch(request: Request, images: list[UploadFile] = File(...), crop_id: int | None = Form(None),
                growth_stage: str | None = Form(None), sample_type: str = Form("field_photo"),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if len(images) > 10:
        raise HTTPException(400, "Maximum 10 images per batch")
    out = []
    for f in images:
        data = await _read_upload(f)
        det, warnings = _run(db, user, data, crop_id, growth_stage, None, sample_type, None, None, f.filename)
        out.append(full(det, warnings))
    return out


def _filtered(db: Session, user: User, start: datetime | None, end: datetime | None, pest: str | None,
              crop_id: int | None, severity: str | None):
    q = select(Detection).where(Detection.user_id == user.id)
    if start:
        q = q.where(Detection.created_at >= start)
    if end:
        q = q.where(Detection.created_at <= end)
    if crop_id:
        q = q.where(Detection.crop_id == crop_id)
    if pest:
        q = q.where(Detection.id.in_(select(DetectedInstance.detection_id).where(DetectedInstance.pest_class == pest)))
    if severity:
        q = q.where(Detection.id.in_(select(SeverityAssessment.detection_id).where(SeverityAssessment.level == severity)))
    return q


@router.get("/history", response_model=Paginated)
def history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), start: datetime | None = None,
            end: datetime | None = None, pest: str | None = None, crop_id: int | None = None,
            severity: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = _filtered(db, user, start, end, pest, crop_id, severity)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.options(selectinload(Detection.instances), selectinload(Detection.severity),
                                selectinload(Detection.crop))
                      .order_by(Detection.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return Paginated(items=[DetectionSummary(**summary(d)) for d in rows], total=total, page=page, page_size=page_size)


@router.get("/export.csv")
def export_csv(start: datetime | None = None, end: datetime | None = None, pest: str | None = None,
               crop_id: int | None = None, severity: str | None = None,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(_filtered(db, user, start, end, pest, crop_id, severity).order_by(Detection.created_at.desc())).all()
    return Response(reports.detections_csv(rows), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="agriguard_detections.csv"'})


@router.get("/{det_id}", response_model=DetectionOut)
def get_detection(det_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return full(_owned(db, user, det_id))


@router.get("/{det_id}/report.pdf")
def report_pdf(det_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = _owned(db, user, det_id)
    trs = []
    for pest in dict.fromkeys(i.pest_class for i in d.instances):
        t = find_treatment(db, pest)
        if t:
            trs.append(treatment_payload(t))
    pdf = reports.detection_pdf(d, d.user_id == user.id and user.full_name or "—", trs[:3])
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="agriguard_report_{d.id}.pdf"'})


@router.delete("/{det_id}", status_code=204)
def delete_detection(det_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = _owned(db, user, det_id)
    db.delete(d)
    db.commit()
