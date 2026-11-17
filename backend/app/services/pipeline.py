"""Full analysis of one uploaded image: inference → storage → density → severity → alerts."""
import uuid
from collections import Counter
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (Crop, DensityObservation, DetectedInstance, Detection, ModelVersion, SeverityAssessment,
                      TreatmentRecommendation, User, utcnow)
from . import alerts, detector, storage
from .scoring import SeverityInput, density_level, density_value, severity


def active_model_version(db: Session) -> ModelVersion | None:
    return db.scalar(select(ModelVersion).where(ModelVersion.is_active.is_(True)).order_by(ModelVersion.id.desc()))


def analyze(db: Session, user: User, data: bytes, *, crop_id: int | None, growth_stage: str | None,
            farm_id: int | None, sample_type: str, trap_area_cm2: float | None,
            observation_hours: float | None, notes: str | None) -> tuple[Detection, list[str]]:
    result = detector.detect(data)
    warnings = []
    crop = db.get(Crop, crop_id) if crop_id else None
    if growth_stage and crop and growth_stage not in crop.growth_stages:
        growth_stage = None
        warnings.append("Growth stage not valid for this crop; ignored.")
    if sample_type == "sticky_trap" and not (trap_area_cm2 and observation_hours):
        warnings.append("Sticky-trap mode needs trap area and observation hours for a trap-catch rate; "
                        "falling back to an image-based count.")

    key_base = f"{user.id}/{utcnow():%Y%m}/{uuid.uuid4().hex}"
    image_key = storage.save(f"{key_base}.jpg", result.original_jpeg)
    annotated_key = storage.save(f"{key_base}_annotated.jpg", result.annotated_jpeg)

    confs = [b.confidence for b in result.boxes]
    det = Detection(
        user_id=user.id, farm_id=farm_id, crop_id=crop.id if crop else None, growth_stage=growth_stage,
        model_version_id=(mv.id if (mv := active_model_version(db)) else None),
        sample_type=sample_type, trap_area_cm2=trap_area_cm2, observation_hours=observation_hours,
        image_key=image_key, annotated_key=annotated_key, image_width=result.width, image_height=result.height,
        total_count=len(result.boxes), low_confidence_count=sum(b.low_confidence for b in result.boxes),
        mean_confidence=round(sum(confs) / len(confs), 4) if confs else None, inference_ms=result.inference_ms,
        status="completed" if result.boxes else "no_pests", notes=notes)
    db.add(det)
    db.flush()
    for b in result.boxes:
        db.add(DetectedInstance(detection_id=det.id, pest_class=b.pest_class, confidence=b.confidence,
                                x1=b.x1, y1=b.y1, x2=b.x2, y2=b.y2, low_confidence=b.low_confidence))
    if result.boxes and all(b.low_confidence for b in result.boxes):
        warnings.append("All detections are low-confidence. The image may not show a pest from the 102 trained "
                        "classes, or may be blurry — retake a close, sharp photo.")
    elif not result.boxes:
        warnings.append("No pests detected. If you can see insects, retake a closer, well-lit photo. "
                        "The model only knows the 102 IP102 pest classes.")

    # Density per pest (low-confidence boxes are counted but flagged in the UI)
    counts = Counter(b.pest_class for b in result.boxes)
    basis = "trap_day" if (sample_type == "sticky_trap" and trap_area_cm2 and observation_hours) else "image"
    since = utcnow() - timedelta(days=14)
    dens_inputs, history = [], {}
    for pest, n in counts.items():
        value, unit, method = density_value(n, sample_type, trap_area_cm2, observation_hours)
        th = alerts.get_threshold(db, user.id, pest, basis)
        level = density_level(value, th)
        db.add(DensityObservation(detection_id=det.id, user_id=user.id, pest_class=pest, count=n, value=value,
                                  unit=unit, method=method, level=level))
        tr = db.scalar(select(TreatmentRecommendation).where(TreatmentRecommendation.pest_key == pest))
        dens_inputs.append({"pest": pest, "value": value, "unit": unit, "level": level, "threshold": th,
                            "weight": tr.severity_weight if tr else 1.0})
        prev = db.scalars(select(DensityObservation.value).where(
            DensityObservation.user_id == user.id, DensityObservation.pest_class == pest,
            DensityObservation.unit == unit, DensityObservation.created_at >= since,
            DensityObservation.detection_id != det.id).order_by(DensityObservation.created_at)).all()
        history[pest] = list(prev)[-3:]

    stage_factor = (crop.stage_sensitivity or {}).get(growth_stage, 1.0) if crop and growth_stage else 1.0
    sev = severity(SeverityInput(densities=dens_inputs, total_count=det.total_count, mean_confidence=det.mean_confidence,
                                 stage=growth_stage, stage_factor=stage_factor, history=history,
                                 crop_name=crop.name if crop else None))
    db.add(SeverityAssessment(detection_id=det.id, **sev))
    db.flush()
    db.refresh(det)
    alerts.notify_for_detection(db, user, det)
    db.commit()
    db.refresh(det)
    return det, warnings
