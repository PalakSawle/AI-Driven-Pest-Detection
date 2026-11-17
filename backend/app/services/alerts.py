"""Notification creation (in-app, optional email) driven by detection results."""
import logging
import smtplib
from datetime import timedelta
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AlertThreshold, Detection, Notification, User, utcnow
from .scoring import Threshold

settings = get_settings()
log = logging.getLogger(__name__)


def get_threshold(db: Session, user_id: int, pest: str, basis: str) -> Threshold:
    q = select(AlertThreshold).where(AlertThreshold.basis == basis)
    rows = db.scalars(q.where(AlertThreshold.pest_class.in_([pest, "*"]),
                              (AlertThreshold.user_id == user_id) | AlertThreshold.user_id.is_(None))).all()

    def rank(r):  # user+pest > system+pest > user+* > system+*
        return (r.pest_class == pest) * 2 + (r.user_id is not None)

    if not rows:
        return Threshold(1, 3, 6, 10)
    r = max(rows, key=rank)
    return Threshold(r.low, r.moderate, r.high, r.critical)


def send_email(to: str, subject: str, body: str) -> bool:
    if not (settings.smtp_host and settings.smtp_from):
        return False
    try:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
        msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        return True
    except Exception as e:  # never fail the request because of email
        log.warning("email failed: %s", e)
        return False


def notify_for_detection(db: Session, user: User, det: Detection) -> list[Notification]:
    out = []
    sev = det.severity
    if det.total_count == 0:
        out.append(Notification(user_id=user.id, type="new_detection", level="info", detection_id=det.id,
                                title="Scan complete — no pests found",
                                message="No pests were detected above the confidence threshold."))
    else:
        pests = ", ".join(sorted({i.pest_class for i in det.instances}))
        out.append(Notification(user_id=user.id, type="new_detection", level="info", detection_id=det.id,
                                title=f"{det.total_count} pest(s) detected",
                                message=f"Detected: {pests}. Severity: {sev.level if sev else 'n/a'}."))
    worst_density = max((d.level for d in det.densities), key=lambda l: ["none", "low", "moderate", "high", "critical"].index(l),
                        default="none")
    if sev and (sev.level == "critical" or worst_density == "critical"):
        out.append(Notification(user_id=user.id, type="critical_infestation", level="critical", detection_id=det.id,
                                title="Critical infestation alert",
                                message=f"Severity score {sev.score:.0f}/100. {sev.recommended_action}"))
    elif sev and (sev.level == "high" or worst_density == "high"):
        out.append(Notification(user_id=user.id, type="high_infestation", level="high", detection_id=det.id,
                                title="High infestation alert",
                                message=f"Severity score {sev.score:.0f}/100. {sev.recommended_action}"))
    if sev and sev.level in ("moderate", "high", "critical"):
        days = 3 if sev.level != "moderate" else 7
        out.append(Notification(user_id=user.id, type="follow_up", level="info", detection_id=det.id,
                                due_at=utcnow() + timedelta(days=days),
                                title="Treatment follow-up reminder",
                                message=f"Re-scan the same area {days} days after treatment to check whether the infestation is falling."))
    for n in out:
        db.add(n)
    db.flush()
    if user.email_alerts:
        for n in out:
            if n.level in ("high", "critical"):
                n.emailed = send_email(user.email, f"[AgriGuard] {n.title}", n.message)
    return out
