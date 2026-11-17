"""Density index and infestation severity scoring.

Everything here is a transparent, configurable heuristic. It is NOT a validated
agronomic model, and the API and UI say so.

DENSITY (per pest class, per detection)
  * field_photo / leaf_sample -> value = number of detections of that pest in the image.
    Unit "pests/image". This is a relative, image-based count — no area is known,
    so we never report pests per m².
  * sticky_trap with trap_area_cm2 AND observation_hours ->
    value = count / (trap_area_cm2 / 100) / (observation_hours / 24)
    Unit "pests/100cm²/day" — a normalised trap-catch rate comparable across traps.
  The value is compared with the user's threshold for that pest (or the system
  default, or the "*" wildcard) to give a level: none/low/moderate/high/critical.

SEVERITY (per detection, 0–100)
  1. Density component  D = 60 × min(value / critical_threshold, 1) for the worst pest.
  2. Species weight     W ∈ [0.7, 1.4] from the treatment knowledge base (how damaging the pest is).
  3. Growth-stage factor S ∈ [0.7, 1.4] from the crop table (sensitive stages weigh more).
  4. Trend component    T ∈ {0, 8, 15}: +15 if this pest's density rose in each of the last
                        three scans within 14 days, +8 if it was already ≥ high last time.
  5. Diversity          V = 5 per extra pest species, max 10.
  6. Confidence factor  C = 0.85 if mean confidence < 0.5, else 1.
  score = clamp((D × W × S + T + V) × C, 0, 100)
  Level: 0 detections → safe; <25 low; <50 moderate; <75 high; ≥75 critical.
"""
from dataclasses import dataclass, field

LEVELS = ["none", "low", "moderate", "high", "critical"]
LEVEL_RANK = {l: i for i, l in enumerate(LEVELS)}


@dataclass
class Threshold:
    low: float
    moderate: float
    high: float
    critical: float


def density_value(count: int, sample_type: str, trap_area_cm2: float | None,
                  observation_hours: float | None) -> tuple[float, str, str]:
    if sample_type == "sticky_trap" and trap_area_cm2 and observation_hours:
        v = count / (trap_area_cm2 / 100.0) / (observation_hours / 24.0)
        return round(v, 3), "pests/100cm²/day", "trap_rate"
    return float(count), "pests/image", "image_count"


def density_level(value: float, t: Threshold) -> str:
    if value <= 0:
        return "none"
    if value >= t.critical:
        return "critical"
    if value >= t.high:
        return "high"
    if value >= t.moderate:
        return "moderate"
    return "low"


@dataclass
class SeverityInput:
    densities: list[dict]              # [{pest, value, unit, level, threshold: Threshold, weight}]
    total_count: int
    mean_confidence: float | None
    stage: str | None
    stage_factor: float = 1.0
    history: dict[str, list[float]] = field(default_factory=dict)  # pest -> previous values (oldest→newest)
    crop_name: str | None = None


def severity(inp: SeverityInput) -> dict:
    if inp.total_count == 0 or not inp.densities:
        return {"score": 0.0, "level": "safe", "factors": [
            {"name": "Detections", "value": 0, "effect": "No pests detected above the confidence threshold."}],
            "explanation": "No pests were detected in this image.",
            "recommended_action": "No action needed. Keep scouting regularly (at least weekly during the season)."}

    worst = max(inp.densities, key=lambda d: d["value"] / max(d["threshold"].critical, 1e-6))
    ratio = min(worst["value"] / max(worst["threshold"].critical, 1e-6), 1.0)
    D = 60 * ratio
    W = max(0.7, min(1.4, worst.get("weight", 1.0)))
    S = max(0.7, min(1.4, inp.stage_factor))
    hist = inp.history.get(worst["pest"], [])
    T, trend_note = 0, "Not enough history for a trend (needs 3 earlier scans in 14 days)."
    if len(hist) >= 3 and hist[-3] < hist[-2] < hist[-1] < worst["value"]:
        T, trend_note = 15, "Density rose in each of the last 3 scans."
    elif hist and hist[-1] >= worst["threshold"].high:
        T, trend_note = 8, "Density was already high in the previous scan."
    elif hist:
        trend_note = "No rising trend in recent scans."
    n_species = len({d["pest"] for d in inp.densities})
    V = min(10, 5 * (n_species - 1))
    C = 0.85 if (inp.mean_confidence or 1) < 0.5 else 1.0
    score = round(max(0.0, min(100.0, (D * W * S + T + V) * C)), 1)
    level = "low" if score < 25 else "moderate" if score < 50 else "high" if score < 75 else "critical"

    factors = [
        {"name": "Density", "value": f'{worst["value"]:g} {worst["unit"]} ({worst["pest"]})',
         "effect": f"{D:.1f} pts — {ratio * 100:.0f}% of the critical threshold ({worst['threshold'].critical:g})."},
        {"name": "Pest species weight", "value": f"×{W:.2f}", "effect": "Relative damage potential from the knowledge base."},
        {"name": "Crop growth stage", "value": f"×{S:.2f}",
         "effect": f"{inp.stage or 'stage not given'}{' of ' + inp.crop_name if inp.crop_name else ''}."},
        {"name": "Trend", "value": f"+{T}", "effect": trend_note},
        {"name": "Pest diversity", "value": f"+{V}", "effect": f"{n_species} species detected."},
        {"name": "Confidence", "value": f"×{C:.2f}",
         "effect": "Low mean confidence reduces the score." if C < 1 else "Detections are reasonably confident."},
    ]
    explanation = (f"{level.capitalize()} risk: {worst['pest']} is at {worst['value']:g} {worst['unit']}, "
                   f"which is '{worst['level']}' against its threshold. "
                   f"Score = (D {D:.1f} × W {W:.2f} × S {S:.2f} + T {T} + V {V}) × C {C:.2f} = {score}. "
                   "This is a rule-based index to prioritise scouting, not a yield-loss prediction.")
    actions = {
        "low": "Keep monitoring every 5–7 days. Use preventive and cultural measures; no spraying needed yet.",
        "moderate": "Scout the whole field within 2–3 days to confirm. Start non-chemical controls "
                    "(mechanical removal, botanicals, conserving natural enemies).",
        "high": "Confirm with a field-level count against the economic threshold. Apply IPM measures now. "
                "If a chemical is needed, choose one registered for this crop and pest and follow the label.",
        "critical": "Act immediately: confirm in the field and contact your local KVK / agriculture officer. "
                    "Follow IPM with label-registered products only, wear PPE and observe pre-harvest intervals.",
    }
    return {"score": score, "level": level, "factors": factors,
            "explanation": explanation, "recommended_action": actions[level]}
