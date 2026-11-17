"""Seeding of reference data and lookups into the treatment knowledge base."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..data.treatments_kb import CURATED, REFS, SAFETY, SUPERCLASS, generic_entry
from ..models import AlertThreshold, Crop, TreatmentRecommendation

CROPS = [
    # key, English, Hindi, stages, sensitivity multipliers
    ("rice", "Rice (Paddy)", "धान", ["nursery", "tillering", "panicle initiation", "flowering", "grain filling", "maturity"],
     {"nursery": 1.1, "tillering": 1.0, "panicle initiation": 1.3, "flowering": 1.4, "grain filling": 1.1, "maturity": 0.7}),
    ("wheat", "Wheat", "गेहूं", ["seedling", "tillering", "jointing", "heading", "grain filling", "maturity"],
     {"seedling": 1.1, "tillering": 1.0, "jointing": 1.1, "heading": 1.3, "grain filling": 1.1, "maturity": 0.7}),
    ("maize", "Maize (Corn)", "मक्का", ["seedling", "knee-high", "tasseling", "silking", "grain filling", "maturity"],
     {"seedling": 1.3, "knee-high": 1.1, "tasseling": 1.3, "silking": 1.3, "grain filling": 1.0, "maturity": 0.7}),
    ("cotton", "Cotton", "कपास", ["seedling", "squaring", "flowering", "boll formation", "boll opening"],
     {"seedling": 1.2, "squaring": 1.2, "flowering": 1.4, "boll formation": 1.3, "boll opening": 0.8}),
    ("sugarcane", "Sugarcane", "गन्ना", ["germination", "tillering", "grand growth", "maturity"],
     {"germination": 1.2, "tillering": 1.2, "grand growth": 1.0, "maturity": 0.7}),
    ("vegetables", "Vegetables (tomato, brinjal, chilli, cabbage)", "सब्ज़ियाँ", ["nursery", "vegetative", "flowering", "fruiting", "harvest"],
     {"nursery": 1.3, "vegetative": 1.0, "flowering": 1.3, "fruiting": 1.3, "harvest": 0.8}),
    ("pulses", "Pulses", "दालें", ["seedling", "vegetative", "flowering", "pod formation", "maturity"],
     {"seedling": 1.1, "vegetative": 1.0, "flowering": 1.4, "pod formation": 1.3, "maturity": 0.7}),
    ("mustard", "Mustard", "सरसों", ["seedling", "vegetative", "flowering", "siliqua formation", "maturity"],
     {"seedling": 1.1, "vegetative": 1.0, "flowering": 1.4, "siliqua formation": 1.2, "maturity": 0.7}),
    ("sugar beet", "Sugar beet", "चुकंदर", ["seedling", "leaf development", "root growth", "maturity"],
     {"seedling": 1.3, "leaf development": 1.1, "root growth": 1.0, "maturity": 0.7}),
    ("alfalfa", "Alfalfa / Lucerne", "रिजका", ["seedling", "vegetative", "bud", "flowering"],
     {"seedling": 1.3, "vegetative": 1.0, "bud": 1.1, "flowering": 1.2}),
    ("grape", "Grape", "अंगूर", ["dormant", "bud break", "flowering", "berry development", "ripening"],
     {"dormant": 0.7, "bud break": 1.2, "flowering": 1.4, "berry development": 1.2, "ripening": 1.1}),
    ("citrus", "Citrus", "नींबू वर्गीय", ["new flush", "flowering", "fruit set", "fruit development", "harvest"],
     {"new flush": 1.3, "flowering": 1.3, "fruit set": 1.2, "fruit development": 1.1, "harvest": 0.8}),
    ("mango", "Mango", "आम", ["vegetative flush", "panicle emergence", "flowering", "fruit set", "fruit development", "harvest"],
     {"vegetative flush": 1.0, "panicle emergence": 1.3, "flowering": 1.4, "fruit set": 1.3, "fruit development": 1.2, "harvest": 0.9}),
]

# Starting-point thresholds (pests/image and pests/100cm²/day). NOT agronomic ETLs —
# farmers/admins should tune them. Small, colony-forming pests get higher image thresholds.
SMALL_PESTS = ["aphids", "Thrips", "red spider", "Trialeurodes vaporariorum", "brown plant hopper",
               "white backed plant hopper", "small brown plant hopper", "Scirtothrips dorsalis Hood",
               "english grain aphid", "green bug", "bird cherry-oataphid", "Toxoptera citricidus",
               "Toxoptera aurantii", "Aphis citricola Vander Goot", "Panonchus citri McGregor",
               "longlegged spider mite", "Pseudococcus comstocki Kuwana"]
DEFAULT_IMAGE = (1, 3, 6, 10)
SMALL_IMAGE = (1, 10, 25, 50)
DEFAULT_TRAP = (0.5, 2, 5, 10)


def seed_reference_data(db: Session, class_names: list[str]) -> None:
    if not db.scalar(select(Crop.id).limit(1)):
        for key, name, hi, stages, sens in CROPS:
            db.add(Crop(key=key, name=name, name_hi=hi, growth_stages=stages, stage_sensitivity=sens))

    existing = set(db.scalars(select(TreatmentRecommendation.pest_key)))
    curated = {c["pest_key"]: c for c in CURATED}
    names = class_names or list(curated)
    for i, pest in enumerate(names, start=1):
        if pest in existing:
            continue
        if pest in curated:
            e = dict(curated[pest]); e["curated"] = True
        else:
            crop = next((c for r, c in SUPERCLASS if i in r), "field crops")
            e = generic_entry(pest, crop)
        db.add(_to_row(e))
        existing.add(pest)
    for pest, e in curated.items():  # curated entries even if not a model class
        if pest not in existing:
            db.add(_to_row(dict(e, curated=True)))

    if not db.scalar(select(AlertThreshold.id).where(AlertThreshold.user_id.is_(None)).limit(1)):
        db.add(AlertThreshold(user_id=None, pest_class="*", basis="image", **dict(zip(("low", "moderate", "high", "critical"), DEFAULT_IMAGE))))
        db.add(AlertThreshold(user_id=None, pest_class="*", basis="trap_day", **dict(zip(("low", "moderate", "high", "critical"), DEFAULT_TRAP))))
        for p in SMALL_PESTS:
            db.add(AlertThreshold(user_id=None, pest_class=p, basis="image", **dict(zip(("low", "moderate", "high", "critical"), SMALL_IMAGE))))
    db.commit()


def _to_row(e: dict) -> TreatmentRecommendation:
    return TreatmentRecommendation(
        pest_key=e["pest_key"], common_name=e["common_name"], common_name_hi=e.get("common_name_hi"),
        scientific_name=e.get("scientific_name"), crops=e["crops"], symptoms=e["symptoms"], organic=e["organic"],
        biological=e["biological"], chemical_categories=e["chemical_categories"], preventive=e["preventive"],
        ipm=e["ipm"], monitoring=e["monitoring"], etl_note=e.get("etl_note"),
        references=[REFS[r] for r in e.get("refs", [])] + [REFS["cibrc"]],
        severity_weight=e.get("severity_weight", 1.0), curated=e.get("curated", True))


def treatment_payload(t: TreatmentRecommendation) -> dict:
    expert = (not t.curated) or any("quarantine" in c.get("note", "").lower() or "Locust" in c.get("note", "")
                                      for c in t.chemical_categories)
    return {
        "pest_key": t.pest_key, "common_name": t.common_name, "common_name_hi": t.common_name_hi,
        "scientific_name": t.scientific_name, "crops": t.crops, "symptoms": t.symptoms, "organic": t.organic,
        "biological": t.biological, "chemical_categories": t.chemical_categories, "preventive": t.preventive,
        "ipm": t.ipm, "monitoring": t.monitoring, "etl_note": t.etl_note, "references": t.references,
        "curated": t.curated, "safety": SAFETY, "expert_advice_required": expert,
    }


def find_treatment(db: Session, pest: str) -> TreatmentRecommendation | None:
    t = db.scalar(select(TreatmentRecommendation).where(TreatmentRecommendation.pest_key == pest))
    if t:
        return t
    low = pest.lower().strip()
    for t in db.scalars(select(TreatmentRecommendation)):
        if low in (t.pest_key.lower(), t.common_name.lower()) or (t.scientific_name and low == t.scientific_name.lower()):
            return t
    return None
