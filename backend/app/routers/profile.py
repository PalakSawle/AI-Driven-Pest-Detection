from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Crop, Farm, User, UserCrop
from ..schemas import CropOut, FarmIn, FarmOut, ProfileOut, ProfileUpdate

router = APIRouter(prefix="/api", tags=["profile"])


def _profile(user: User) -> ProfileOut:
    return ProfileOut(**{k: getattr(user, k) for k in ("id", "email", "full_name", "phone", "role", "language",
                                                        "email_alerts", "created_at")},
                      farms=[FarmOut.model_validate(f) for f in user.farms],
                      crops=[CropOut.model_validate(uc.crop) for uc in user.crop_preferences])


@router.get("/crops", response_model=list[CropOut])
def list_crops(db: Session = Depends(get_db)):
    return db.scalars(select(Crop).order_by(Crop.name)).all()


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user)):
    return _profile(user)


@router.patch("/profile", response_model=ProfileOut)
def update_profile(body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("full_name", "phone", "language", "email_alerts"):
        v = getattr(body, f)
        if v is not None:
            setattr(user, f, v)
    if body.crop_ids is not None:
        valid = set(db.scalars(select(Crop.id).where(Crop.id.in_(body.crop_ids))))
        user.crop_preferences.clear()
        db.flush()
        for cid in valid:
            user.crop_preferences.append(UserCrop(user_id=user.id, crop_id=cid))
    if body.farm is not None:
        farm = user.farms[0] if user.farms else None
        if farm is None:
            farm = Farm(user_id=user.id, **body.farm.model_dump())
            db.add(farm)
        else:
            for k, v in body.farm.model_dump().items():
                setattr(farm, k, v)
    db.commit()
    db.refresh(user)
    return _profile(user)


@router.post("/farms", response_model=FarmOut, status_code=201)
def add_farm(body: FarmIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    farm = Farm(user_id=user.id, **body.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.delete("/farms/{farm_id}", status_code=204)
def delete_farm(farm_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    farm = db.get(Farm, farm_id)
    if not farm or farm.user_id != user.id:
        raise HTTPException(404, "Farm not found")
    db.delete(farm)
    db.commit()
