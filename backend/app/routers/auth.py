from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import get_current_user
from ..limiter import limiter
from ..models import User, utcnow
from ..schemas import ForgotIn, LoginIn, PasswordChange, RegisterIn, ResetIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, hash_reset_token, new_reset_token, verify_password
from ..services.alerts import send_email

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=TokenOut, status_code=201)
@limiter.limit(settings.rate_limit_auth)
def register(request: Request, body: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=body.email.lower(), hashed_password=hash_password(body.password), full_name=body.full_name.strip(),
                phone=body.phone, language=body.language)
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
@limiter.limit(settings.rate_limit_auth)
def login(request: Request, body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    return TokenOut(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, body: ForgotIn, db: Session = Depends(get_db)):
    """Always returns the same message so the endpoint can't be used to discover accounts."""
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    resp = {"message": "If an account exists for this email, a reset link has been sent."}
    if user:
        token, hashed = new_reset_token()
        user.reset_token_hash = hashed
        user.reset_token_expires = utcnow() + timedelta(minutes=settings.reset_token_expire_minutes)
        db.commit()
        link = f"{settings.frontend_url}/reset-password?token={token}"
        sent = send_email(user.email, "Reset your AgriGuard AI password",
                          f"Hello {user.full_name},\n\nReset your password using this link (valid "
                          f"{settings.reset_token_expire_minutes} minutes):\n{link}\n\nIf you did not ask for this, ignore this email.")
        if not sent and settings.environment == "development":
            resp["dev_reset_link"] = link  # only in local development when SMTP isn't configured
    return resp


@router.post("/reset-password")
def reset_password(body: ResetIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.reset_token_hash == hash_reset_token(body.token)))
    expires = user.reset_token_expires if user else None
    if expires is not None and expires.tzinfo is None:
        from datetime import timezone
        expires = expires.replace(tzinfo=timezone.utc)
    if not user or not expires or expires < utcnow():
        raise HTTPException(400, "Reset link is invalid or has expired")
    user.hashed_password = hash_password(body.new_password)
    user.reset_token_hash = None
    user.reset_token_expires = None
    db.commit()
    return {"message": "Password updated. You can now log in."}


@router.post("/change-password")
def change_password(body: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")
    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"message": "Password changed"}
