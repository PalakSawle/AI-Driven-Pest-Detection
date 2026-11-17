"""Alerts, thresholds, treatments, chat, weather, files and model info routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import get_current_user
from ..limiter import limiter
from ..models import (AlertThreshold, ChatConversation, ChatMessage, Farm, ModelVersion, Notification,
                      TreatmentRecommendation, User, WeatherRecord, utcnow)
from ..schemas import (ChatIn, ChatMessageOut, ChatReply, ConversationOut, NotificationOut, ThresholdIn,
                       ThresholdOut, TreatmentOut)
from ..services import chat as chat_service
from ..services import detector, storage, weather
from ..services.knowledge import find_treatment, treatment_payload

settings = get_settings()

# ---------------- alerts ----------------
alerts = APIRouter(prefix="/api/alerts", tags=["alerts"])


@alerts.get("", response_model=list[NotificationOut])
def list_alerts(unread_only: bool = False, include_scheduled: bool = False, limit: int = Query(100, le=500),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    rows = db.scalars(q.order_by(Notification.created_at.desc()).limit(limit)).all()
    now = utcnow()

    def due(n):
        if n.due_at is None:
            return True
        d = n.due_at if n.due_at.tzinfo else n.due_at.replace(tzinfo=now.tzinfo)
        return d <= now
    return [n for n in rows if include_scheduled or due(n)]


@alerts.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list_alerts(True, False, 500, user, db)
    return {"count": len(rows)}


@alerts.patch("/{alert_id}/read", response_model=NotificationOut)
def mark_read(alert_id: int, read: bool = True, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, alert_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Alert not found")
    n.is_read = read
    db.commit()
    return n


@alerts.post("/read-all")
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
    db.commit()
    return {"ok": True}


@alerts.delete("/{alert_id}", status_code=204)
def delete_alert(alert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, alert_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Alert not found")
    db.delete(n)
    db.commit()


@alerts.get("/thresholds", response_model=list[ThresholdOut])
def get_thresholds(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(AlertThreshold).where(
        (AlertThreshold.user_id == user.id) | AlertThreshold.user_id.is_(None),
        AlertThreshold.basis == "image").order_by(AlertThreshold.user_id.is_(None), AlertThreshold.pest_class)).all()


@alerts.put("/thresholds", response_model=ThresholdOut)
def set_threshold(body: ThresholdIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not (body.low <= body.moderate <= body.high <= body.critical):
        raise HTTPException(422, "Thresholds must satisfy low ≤ moderate ≤ high ≤ critical")
    t = db.scalar(select(AlertThreshold).where(AlertThreshold.user_id == user.id, AlertThreshold.pest_class == body.pest_class,
                                               AlertThreshold.basis == "image"))
    if not t:
        t = AlertThreshold(user_id=user.id, pest_class=body.pest_class, basis="image")
        db.add(t)
    t.low, t.moderate, t.high, t.critical = body.low, body.moderate, body.high, body.critical
    db.commit()
    db.refresh(t)
    return t


@alerts.delete("/thresholds/{tid}", status_code=204)
def delete_threshold(tid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.get(AlertThreshold, tid)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "Custom threshold not found")
    db.delete(t)
    db.commit()


# ---------------- treatments ----------------
treatments = APIRouter(prefix="/api/treatments", tags=["treatments"])


@treatments.get("", response_model=list[TreatmentOut])
def list_treatments(curated_only: bool = True, db: Session = Depends(get_db)):
    q = select(TreatmentRecommendation)
    if curated_only:
        q = q.where(TreatmentRecommendation.curated.is_(True))
    return [treatment_payload(t) for t in db.scalars(q.order_by(TreatmentRecommendation.common_name))]


@treatments.get("/{pest}", response_model=TreatmentOut)
def get_treatment(pest: str, db: Session = Depends(get_db)):
    t = find_treatment(db, pest)
    if not t:
        raise HTTPException(404, f"No treatment information for '{pest}'")
    return treatment_payload(t)


# ---------------- chat ----------------
chat = APIRouter(prefix="/api/chat", tags=["chat"])


@chat.post("/message", response_model=ChatReply)
@limiter.limit(settings.rate_limit_chat)
def send_message(request: Request, body: ChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.conversation_id:
        conv = db.get(ChatConversation, body.conversation_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(404, "Conversation not found")
    else:
        conv = ChatConversation(user_id=user.id, title=body.message[:60])
        db.add(conv)
        db.flush()
    history = list(conv.messages)
    reply, lang, source = chat_service.answer(db, user, body.message, history, body.include_detections)
    um = ChatMessage(conversation_id=conv.id, role="user", content=body.message, language=lang)
    am = ChatMessage(conversation_id=conv.id, role="assistant", content=reply, language=lang, source=source)
    db.add_all([um, am])
    conv.updated_at = utcnow()
    db.commit()
    return ChatReply(conversation_id=conv.id, user_message=ChatMessageOut.model_validate(um),
                     reply=ChatMessageOut.model_validate(am))


@chat.get("/history", response_model=list[ChatMessageOut])
def chat_history(conversation_id: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if conversation_id is None:
        conv = db.scalar(select(ChatConversation).where(ChatConversation.user_id == user.id)
                         .order_by(ChatConversation.updated_at.desc()))
        if not conv:
            return []
    else:
        conv = db.get(ChatConversation, conversation_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(404, "Conversation not found")
    return conv.messages


@chat.get("/conversations", response_model=list[ConversationOut])
def conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(ChatConversation).where(ChatConversation.user_id == user.id)
                      .order_by(ChatConversation.updated_at.desc()).limit(50)).all()


@chat.delete("/conversations/{cid}", status_code=204)
def delete_conversation(cid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.get(ChatConversation, cid)
    if not conv or conv.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    db.delete(conv)
    db.commit()


@chat.get("/status")
def chat_status():
    return {"llm_enabled": chat_service.llm_enabled(),
            "provider": settings.llm_provider if chat_service.llm_enabled() else "knowledge_base"}


# ---------------- weather ----------------
weather_router = APIRouter(prefix="/api/weather", tags=["weather"])


@weather_router.get("")
def get_weather(lat: float | None = Query(None, ge=-90, le=90), lon: float | None = Query(None, ge=-180, le=180),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if lat is None or lon is None:
        farm = db.scalar(select(Farm).where(Farm.user_id == user.id, Farm.latitude.is_not(None)))
        if not farm:
            return {"status": "no_location", "message": "Add your farm location in Profile, or allow location access."}
        lat, lon = farm.latitude, farm.longitude
    try:
        w = weather.fetch(lat, lon)
    except weather.WeatherUnavailable as e:
        last = db.scalar(select(WeatherRecord).where(WeatherRecord.user_id == user.id).order_by(WeatherRecord.fetched_at.desc()))
        return {"status": "unavailable", "message": str(e),
                "last_known": None if not last else {"fetched_at": last.fetched_at, "temperature_c": last.temperature_c,
                                                     "humidity_pct": last.humidity_pct, "rainfall_mm": last.rainfall_mm,
                                                     "provider": last.provider}}
    c = w["current"]
    db.add(WeatherRecord(user_id=user.id, latitude=lat, longitude=lon, temperature_c=c.get("temperature_c"),
                         humidity_pct=c.get("humidity_pct"), rainfall_mm=c.get("rainfall_mm"), wind_kmh=c.get("wind_kmh"),
                         provider=w["provider"], payload={"daily": w["daily"]}))
    db.commit()
    return {"status": "ok", "provider": w["provider"], "latitude": lat, "longitude": lon, "current": c,
            "daily": w["daily"], "pest_risk": weather.pest_risk(c, w["daily"]),
            "note": "Weather-based pest risk is an advisory rule of thumb, not a forecast model."}


# ---------------- files & model ----------------
files = APIRouter(tags=["files"])


@files.get("/api/files/{key:path}")
def get_file(key: str, exp: int, sig: str):
    if not storage.verify_signature(key, exp, sig):
        raise HTTPException(403, "Link expired or invalid")
    try:
        data = storage.load(key)
    except storage.StorageError:
        raise HTTPException(404, "File not found")
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@files.get("/api/model/info", tags=["model"])
def model_info(db: Session = Depends(get_db)):
    mv = db.scalar(select(ModelVersion).where(ModelVersion.is_active.is_(True)).order_by(ModelVersion.id.desc()))
    meta = detector.model_meta()
    return {"available": detector.is_available(),
            "name": mv.name if mv else meta.get("name"), "version": mv.version if mv else meta.get("version"),
            "architecture": mv.architecture if mv else meta.get("architecture"),
            "dataset": mv.dataset if mv else meta.get("dataset"), "dataset_source": meta.get("dataset_source"),
            "num_classes": len(mv.classes) if mv else len(meta.get("classes", [])),
            "classes": mv.classes if mv else meta.get("classes", []),
            "metrics": {k: v for k, v in (mv.metrics if mv else meta.get("metrics", {})).items() if k != "per_class"},
            "per_class": (mv.metrics if mv else meta.get("metrics", {})).get("per_class", {}),
            "dataset_stats": meta.get("dataset_stats", {}),
            "thresholds": {"confidence": settings.conf_threshold, "low_confidence": settings.low_conf_threshold}}
