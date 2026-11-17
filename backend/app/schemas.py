from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    language: Literal["en", "hi", "hinglish"] = "en"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class CropOut(ORM):
    id: int
    key: str
    name: str
    name_hi: str
    growth_stages: list[str]


class FarmIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location_name: str | None = None
    state: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area_hectares: float | None = Field(default=None, ge=0)


class FarmOut(ORM, FarmIn):
    id: int


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    phone: str | None
    role: str
    language: str
    email_alerts: bool
    created_at: datetime


class ProfileOut(UserOut):
    farms: list[FarmOut]
    crops: list[CropOut]


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    language: Literal["en", "hi", "hinglish"] | None = None
    email_alerts: bool | None = None
    crop_ids: list[int] | None = None
    farm: FarmIn | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


# ---------- detections ----------
class InstanceOut(ORM):
    id: int
    pest_class: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    low_confidence: bool


class SeverityOut(ORM):
    score: float
    level: str
    factors: list[dict]
    explanation: str
    recommended_action: str


class DensityOut(ORM):
    pest_class: str
    count: int
    value: float
    unit: str
    method: str
    level: str


class DetectionSummary(ORM):
    id: int
    created_at: datetime
    total_count: int
    status: str
    crop_name: str | None = None
    growth_stage: str | None
    severity_level: str | None = None
    severity_score: float | None = None
    top_pest: str | None = None
    mean_confidence: float | None
    image_url: str
    annotated_url: str | None


class DetectionOut(DetectionSummary):
    image_width: int
    image_height: int
    inference_ms: float
    low_confidence_count: int
    sample_type: str
    trap_area_cm2: float | None
    observation_hours: float | None
    notes: str | None
    class_counts: dict[str, int]
    instances: list[InstanceOut]
    severity: SeverityOut | None
    densities: list[DensityOut]
    model_version: str | None
    warnings: list[str] = []


class Paginated(BaseModel):
    items: list[DetectionSummary]
    total: int
    page: int
    page_size: int


# ---------- treatments ----------
class TreatmentOut(ORM):
    pest_key: str
    common_name: str
    common_name_hi: str | None
    scientific_name: str | None
    crops: list[str]
    symptoms: list[str]
    organic: list[str]
    biological: list[str]
    chemical_categories: list[dict]
    preventive: list[str]
    ipm: list[str]
    monitoring: str
    etl_note: str | None
    references: list[dict]
    curated: bool
    safety: list[str] = []
    expert_advice_required: bool = True


# ---------- alerts ----------
class NotificationOut(ORM):
    id: int
    type: str
    title: str
    message: str
    level: str
    detection_id: int | None
    is_read: bool
    due_at: datetime | None
    created_at: datetime


class ThresholdIn(BaseModel):
    pest_class: str = Field(min_length=1, max_length=80)
    low: float = Field(ge=0)
    moderate: float = Field(ge=0)
    high: float = Field(ge=0)
    critical: float = Field(ge=0)


class ThresholdOut(ORM, ThresholdIn):
    id: int
    user_id: int | None


# ---------- chat ----------
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = None
    include_detections: bool = True


class ChatMessageOut(ORM):
    id: int
    role: str
    content: str
    language: str | None
    source: str | None
    created_at: datetime


class ChatReply(BaseModel):
    conversation_id: int
    user_message: ChatMessageOut
    reply: ChatMessageOut


class ConversationOut(ORM):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


TokenOut.model_rebuild()
