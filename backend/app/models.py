"""Normalized relational schema for AgriGuard AI."""
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(String(20), default="farmer")  # farmer | admin
    language: Mapped[str] = mapped_column(String(10), default="en")  # en | hi | hinglish
    email_alerts: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reset_token_hash: Mapped[str | None] = mapped_column(String(255))
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    farms: Mapped[list["Farm"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    crop_preferences: Mapped[list["UserCrop"]] = relationship(cascade="all, delete-orphan")


class Farm(Base):
    __tablename__ = "farms"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    location_name: Mapped[str | None] = mapped_column(String(200))
    state: Mapped[str | None] = mapped_column(String(80))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    area_hectares: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user: Mapped[User] = relationship(back_populates="farms")


class Crop(Base):
    """Reference table of crop types."""
    __tablename__ = "crops"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    name_hi: Mapped[str] = mapped_column(String(80))
    growth_stages: Mapped[list] = mapped_column(JSON, default=list)
    # Multiplier per growth stage for severity scoring, e.g. {"flowering": 1.3}
    stage_sensitivity: Mapped[dict] = mapped_column(JSON, default=dict)


class UserCrop(Base):
    __tablename__ = "user_crops"
    __table_args__ = (UniqueConstraint("user_id", "crop_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id", ondelete="CASCADE"))
    crop: Mapped[Crop] = relationship()


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(40))
    architecture: Mapped[str] = mapped_column(String(80))
    dataset: Mapped[str] = mapped_column(String(200))
    classes: Mapped[list] = mapped_column(JSON, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    weights_path: Mapped[str] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Detection(Base):
    __tablename__ = "detections"
    __table_args__ = (Index("ix_detections_user_created", "user_id", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    farm_id: Mapped[int | None] = mapped_column(ForeignKey("farms.id", ondelete="SET NULL"))
    crop_id: Mapped[int | None] = mapped_column(ForeignKey("crops.id", ondelete="SET NULL"))
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id", ondelete="SET NULL"))
    growth_stage: Mapped[str | None] = mapped_column(String(40))
    # Sampling metadata, needed before any physical density claim.
    sample_type: Mapped[str] = mapped_column(String(30), default="field_photo")  # field_photo | sticky_trap | leaf_sample
    trap_area_cm2: Mapped[float | None] = mapped_column(Float)
    observation_hours: Mapped[float | None] = mapped_column(Float)
    image_key: Mapped[str] = mapped_column(String(300))
    annotated_key: Mapped[str | None] = mapped_column(String(300))
    image_width: Mapped[int] = mapped_column(Integer, default=0)
    image_height: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    low_confidence_count: Mapped[int] = mapped_column(Integer, default=0)
    mean_confidence: Mapped[float | None] = mapped_column(Float)
    inference_ms: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(20), default="completed")  # completed | no_pests | failed
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    crop: Mapped[Crop | None] = relationship()
    farm: Mapped[Farm | None] = relationship()
    model_version: Mapped[ModelVersion | None] = relationship()
    instances: Mapped[list["DetectedInstance"]] = relationship(back_populates="detection", cascade="all, delete-orphan")
    severity: Mapped["SeverityAssessment | None"] = relationship(back_populates="detection", cascade="all, delete-orphan", uselist=False)
    densities: Mapped[list["DensityObservation"]] = relationship(back_populates="detection", cascade="all, delete-orphan")


class DetectedInstance(Base):
    __tablename__ = "detected_instances"
    id: Mapped[int] = mapped_column(primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("detections.id", ondelete="CASCADE"), index=True)
    pest_class: Mapped[str] = mapped_column(String(80), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    x1: Mapped[float] = mapped_column(Float)
    y1: Mapped[float] = mapped_column(Float)
    x2: Mapped[float] = mapped_column(Float)
    y2: Mapped[float] = mapped_column(Float)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    detection: Mapped[Detection] = relationship(back_populates="instances")


class SeverityAssessment(Base):
    __tablename__ = "severity_assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("detections.id", ondelete="CASCADE"), unique=True)
    score: Mapped[float] = mapped_column(Float)
    level: Mapped[str] = mapped_column(String(20), index=True)  # safe|low|moderate|high|critical
    factors: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    detection: Mapped[Detection] = relationship(back_populates="severity")


class DensityObservation(Base):
    __tablename__ = "density_observations"
    __table_args__ = (Index("ix_density_user_pest", "user_id", "pest_class", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("detections.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    pest_class: Mapped[str] = mapped_column(String(80))
    count: Mapped[int] = mapped_column(Integer)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40))  # "pests/image" | "pests/100cm2/day"
    method: Mapped[str] = mapped_column(String(40))  # image_count | trap_rate
    level: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    detection: Mapped[Detection] = relationship(back_populates="densities")


class AlertThreshold(Base):
    """Per-pest thresholds (pests per image or per trap-day). user_id NULL = system default."""
    __tablename__ = "alert_thresholds"
    __table_args__ = (UniqueConstraint("user_id", "pest_class", "basis"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    pest_class: Mapped[str] = mapped_column(String(80))  # "*" = any pest
    basis: Mapped[str] = mapped_column(String(20), default="image")  # image | trap_day
    low: Mapped[float] = mapped_column(Float, default=1)
    moderate: Mapped[float] = mapped_column(Float, default=5)
    high: Mapped[float] = mapped_column(Float, default=10)
    critical: Mapped[float] = mapped_column(Float, default=20)


class TreatmentRecommendation(Base):
    __tablename__ = "treatment_recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    pest_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    common_name: Mapped[str] = mapped_column(String(120))
    common_name_hi: Mapped[str | None] = mapped_column(String(120))
    scientific_name: Mapped[str | None] = mapped_column(String(120))
    crops: Mapped[list] = mapped_column(JSON, default=list)
    symptoms: Mapped[list] = mapped_column(JSON, default=list)
    organic: Mapped[list] = mapped_column(JSON, default=list)
    biological: Mapped[list] = mapped_column(JSON, default=list)
    chemical_categories: Mapped[list] = mapped_column(JSON, default=list)
    preventive: Mapped[list] = mapped_column(JSON, default=list)
    ipm: Mapped[list] = mapped_column(JSON, default=list)
    monitoring: Mapped[str] = mapped_column(Text, default="")
    etl_note: Mapped[str | None] = mapped_column(Text)
    references: Mapped[list] = mapped_column(JSON, default=list)
    severity_weight: Mapped[float] = mapped_column(Float, default=1.0)
    curated: Mapped[bool] = mapped_column(Boolean, default=True)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(30))  # new_detection|high_infestation|critical_infestation|follow_up
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(20), default="info")
    detection_id: Mapped[int | None] = mapped_column(ForeignKey("detections.id", ondelete="CASCADE"))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emailed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="ChatMessage.id")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("chat_conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(10))
    source: Mapped[str | None] = mapped_column(String(30))  # llm:<provider> | knowledge_base
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    conversation: Mapped[ChatConversation] = relationship(back_populates="messages")


class WeatherRecord(Base):
    __tablename__ = "weather_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    temperature_c: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    wind_kmh: Mapped[float | None] = mapped_column(Float)
    provider: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
