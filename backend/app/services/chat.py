"""AI Kisan assistant.

* With LLM_PROVIDER + LLM_API_KEY set: calls the provider (Anthropic, OpenAI or
  Gemini) with a safety-focused system prompt plus the user's recent detections
  and the matching knowledge-base entries as grounding context.
* Without a key, or if the provider fails: answers from the curated knowledge
  base (intent + entity matching, templated in English / Hinglish / Hindi).
  Replies are labelled with their source so the UI can show which one answered.
"""
import logging
import re

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..data.treatments_kb import SAFETY
from ..models import ChatMessage, Detection, TreatmentRecommendation, User

settings = get_settings()
log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are "AI Kisan", the farming assistant inside AgriGuard AI, helping Indian farmers with crop pests.
Rules:
- Reply in the user's language and script: Hindi (Devanagari) if they write Hindi, Hinglish (Roman Hindi) if they write Hinglish, else simple English. Keep answers short, practical and friendly; use bullet points.
- Prefer Integrated Pest Management: monitoring, cultural, mechanical, biological and botanical methods first.
- NEVER invent pesticide brand names, doses, dilutions or spray schedules. You may mention insecticide classes (IRAC groups) only, and always say: use a product registered by CIB&RC for this crop and pest, follow the label, wear PPE and respect the pre-harvest interval.
- Say clearly when the farmer should contact the local KVK / agriculture officer (unsure identification, critical infestation, quarantine pests, locust swarms).
- Detection results come from an AI model and may be wrong; suggest confirming in the field.
- If you don't know, say so. Do not make up facts or weather."""

HINGLISH_WORDS = {"kya", "hai", "kaise", "kaun", "mein", "meri", "mera", "mere", "karu", "karna", "chahiye", "fasal", "keeda",
                  "kida", "kide", "dawa", "upay", "ilaj", "kab", "kitna", "nahi", "aur", "ka", "ki", "ke", "ho", "raha", "lag",
                  "laga", "batao", "bataiye", "khet", "ab", "liye", "ke liye", "hota"}


def detect_language(text: str) -> str:
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    words = set(re.findall(r"[a-z]+", text.lower()))
    return "hinglish" if len(words & HINGLISH_WORDS) >= 2 else "en"


def _recent_context(db: Session, user: User, limit: int = 5) -> tuple[str, list[str]]:
    dets = db.scalars(select(Detection).where(Detection.user_id == user.id)
                      .order_by(Detection.created_at.desc()).limit(limit)).all()
    lines, pests = [], []
    for d in dets:
        counts: dict[str, int] = {}
        for i in d.instances:
            counts[i.pest_class] = counts.get(i.pest_class, 0) + 1
        pests += list(counts)
        sev = f"{d.severity.level} ({d.severity.score:.0f}/100)" if d.severity else "n/a"
        crop = d.crop.name if d.crop else "crop not specified"
        lines.append(f"- {d.created_at:%Y-%m-%d}: {crop}, stage {d.growth_stage or 'n/a'}; "
                     f"pests {counts or 'none'}; severity {sev}")
    return "\n".join(lines), list(dict.fromkeys(pests))


def _kb_lookup(db: Session, text: str, fallback_pests: list[str]) -> list[TreatmentRecommendation]:
    low = text.lower()
    found = []
    for t in db.scalars(select(TreatmentRecommendation).where(TreatmentRecommendation.curated.is_(True))):
        keys = [t.pest_key.lower(), t.common_name.lower()] + ([t.common_name_hi] if t.common_name_hi else [])
        keys += [k.split(" (")[0] for k in keys]
        if any(k and k in low for k in keys):
            found.append(t)
    alias = {"white fly": "Trialeurodes vaporariorum", "whitefly": "Trialeurodes vaporariorum", "safed makhi": "Trialeurodes vaporariorum",
             "mahu": "aphids", "chepa": "aphids", "aphid": "aphids", "thrips": "Thrips", "stem borer": "yellow rice borer",
             "tana chhedak": "yellow rice borer", "bph": "brown plant hopper", "fruit fly": "Dacus dorsalis(Hendel)",
             "mealy": "Pseudococcus comstocki Kuwana", "mite": "red spider", "cutworm": "black cutworm",
             "armyworm": "army worm", "sundi": "Prodenia litura", "illi": "Prodenia litura", "tidda": "Locustoidea",
             "locust": "Locustoidea"}
    for k, v in alias.items():
        if k in low:
            t = db.scalar(select(TreatmentRecommendation).where(TreatmentRecommendation.pest_key == v))
            if t and t not in found:
                found.append(t)
    if not found:
        for p in fallback_pests[:2]:
            t = db.scalar(select(TreatmentRecommendation).where(TreatmentRecommendation.pest_key == p))
            if t:
                found.append(t)
    return found[:3]


def _kb_text(t: TreatmentRecommendation) -> str:
    chem = "; ".join(c["class"] for c in t.chemical_categories)
    return (f"{t.common_name} ({t.scientific_name or t.pest_key}) — crops: {', '.join(t.crops)}\n"
            f"Symptoms: {'; '.join(t.symptoms)}\nOrganic: {'; '.join(t.organic)}\n"
            f"Biological: {'; '.join(t.biological)}\nChemical classes: {chem}\n"
            f"Prevention: {'; '.join(t.preventive)}\nMonitoring: {t.monitoring}\n"
            f"{'ETL: ' + t.etl_note if t.etl_note else ''}{'' if t.curated else ' (NOT curated — expert advice needed)'}")


# ---------------- LLM providers ----------------
def _call_llm(system: str, history: list[dict]) -> str:
    p, key = settings.llm_provider.lower(), settings.llm_api_key
    with httpx.Client(timeout=45) as c:
        if p == "anthropic":
            r = c.post("https://api.anthropic.com/v1/messages", headers={
                "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": settings.llm_model or "claude-haiku-5-5", "max_tokens": 900,
                      "system": system, "messages": history})
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"])
        if p == "openai":
            r = c.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {key}"},
                       json={"model": settings.llm_model or "gpt-4o-mini", "max_tokens": 900,
                             "messages": [{"role": "system", "content": system}] + history})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        if p == "gemini":
            model = settings.llm_model or "gemini-2.0-flash"
            contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                        for m in history]
            r = c.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                       headers={"x-goog-api-key": key},
                       json={"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
                             "generationConfig": {"maxOutputTokens": 900}})
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    raise RuntimeError(f"Unsupported LLM provider '{p}'")


def llm_enabled() -> bool:
    return settings.llm_provider.lower() in ("anthropic", "openai", "gemini") and bool(settings.llm_api_key)


# ---------------- knowledge-base fallback ----------------
T = {
    "en": {"no_det": "I don't see any scans in your history yet. Upload a photo on the Detect page and I'll tell you which pest it is.",
           "latest": "Your latest scans:", "treat": "Here is what the AgriGuard knowledge base says about",
           "organic": "Organic options", "bio": "Biological control", "chem": "If chemicals are needed (classes only)",
           "prev": "Prevention", "mon": "Monitoring", "safety": "Safety",
           "unknown": "I can help with pest identification, treatment options (organic, biological, IPM), neem oil use, and what to do when infestation is high. Try: \"How do I control aphids organically?\"",
           "kb_note": "(Answer from AgriGuard's curated knowledge base — the AI language model is not configured.)",
           "expert": "Please confirm with your local KVK / agriculture officer before spraying."},
    "hinglish": {"no_det": "Aapki history mein abhi koi scan nahi hai. Detect page par photo upload karein, main bata dunga kaun sa keeda hai.",
                 "latest": "Aapke recent scans:", "treat": "AgriGuard knowledge base ke anusaar",
                 "organic": "Organic upay", "bio": "Jaivik (biological) niyantran", "chem": "Agar dawa zaroori ho (sirf class)",
                 "prev": "Bachav", "mon": "Nigrani (monitoring)", "safety": "Suraksha",
                 "unknown": "Main keede ki pehchaan, organic/jaivik/IPM upay, neem oil ka use aur high infestation mein kya karna hai — in sab mein madad kar sakta hoon. Puchiye: \"Mahu ka organic ilaj kya hai?\"",
                 "kb_note": "(Yeh jawab AgriGuard ke curated knowledge base se hai — AI model abhi configure nahi hai.)",
                 "expert": "Spray karne se pehle apne KVK / krishi adhikari se zaroor salah lein."},
    "hi": {"no_det": "आपकी हिस्ट्री में अभी कोई स्कैन नहीं है। Detect पेज पर फोटो अपलोड करें, मैं बताऊँगा कौन सा कीड़ा है।",
           "latest": "आपके हाल के स्कैन:", "treat": "AgriGuard ज्ञानकोश के अनुसार",
           "organic": "जैविक/ऑर्गेनिक उपाय", "bio": "जैविक नियंत्रण", "chem": "यदि दवा ज़रूरी हो (केवल वर्ग)",
           "prev": "बचाव", "mon": "निगरानी", "safety": "सुरक्षा",
           "unknown": "मैं कीट पहचान, ऑर्गेनिक/जैविक/IPM उपाय, नीम तेल के उपयोग और अधिक प्रकोप में क्या करें — इनमें मदद कर सकता हूँ।",
           "kb_note": "(यह उत्तर AgriGuard के क्यूरेटेड ज्ञानकोश से है — AI मॉडल अभी कॉन्फ़िगर नहीं है।)",
           "expert": "छिड़काव से पहले अपने KVK / कृषि अधिकारी से सलाह ज़रूर लें।"},
}

NEEM = {
    "en": ("**Neem oil — how to use safely**\n- Use a neem (azadirachtin) product and follow the dilution on its label; add a little soap/emulsifier if the label says so.\n"
           "- Spray in the early morning or evening, covering leaf undersides where pests hide.\n- Works best on young, soft-bodied pests (aphids, whitefly, mites, young caterpillars) — it repels and disrupts feeding/growth, it is not an instant kill.\n"
           "- Repeat as the label advises; test on a few plants first for leaf burn.\n- Avoid spraying open flowers when bees are active."),
    "hinglish": ("**Neem oil ka sahi upyog**\n- Neem (azadirachtin) product lein aur label par likhe anusaar paani mein milayein; label kahe to thoda sabun/emulsifier milayein.\n"
                 "- Subah jaldi ya shaam ko spray karein, patton ke neeche bhi achhe se.\n- Mahu, safed makhi, mite, chhoti illi jaise naram keedon par zyada asar — yeh dheere kaam karta hai, turant nahi maarta.\n"
                 "- Label ke anusaar dohrayein; pehle kuch paudhon par test karein.\n- Phool khile hon aur madhumakkhi ho to spray na karein."),
    "hi": ("**नीम तेल का सही उपयोग**\n- नीम (एज़ाडिरेक्टिन) उत्पाद लें और लेबल के अनुसार पानी में मिलाएँ।\n- सुबह जल्दी या शाम को छिड़कें, पत्तियों के नीचे भी।\n"
           "- माहू, सफ़ेद मक्खी, माइट, छोटी इल्ली पर अधिक असरदार — यह धीरे काम करता है।\n- लेबल के अनुसार दोहराएँ; पहले कुछ पौधों पर परखें।\n- फूल खिले हों और मधुमक्खियाँ हों तो छिड़काव न करें।"),
}

ORGANIC_GENERAL = {
    "en": "**Common organic / non-chemical options**\n- Neem-based sprays (NSKE / neem oil)\n- Yellow (whitefly, aphids) and blue (thrips) sticky traps; pheromone traps for moths\n- Biopesticides: Bt for caterpillars, Beauveria / Metarhizium / Lecanicillium fungi, NPV viruses\n- Release / conserve natural enemies: Trichogramma, ladybirds, lacewings, spiders\n- Field sanitation, crop rotation, balanced fertiliser, resistant varieties",
    "hinglish": "**Aam organic upay**\n- Neem spray (NSKE / neem oil)\n- Peele (safed makhi, mahu) aur neele (thrips) sticky trap; patango ke liye pheromone trap\n- Jaivik dawa: illi ke liye Bt, Beauveria / Metarhizium fungus, NPV virus\n- Mitra keet: Trichogramma, ladybird, lacewing, makdi — inhe bachayein\n- Khet ki safai, fasal chakra, santulit khad, rog-rodhi kism",
    "hi": "**सामान्य ऑर्गेनिक उपाय**\n- नीम स्प्रे (NSKE / नीम तेल)\n- पीले (सफ़ेद मक्खी, माहू) और नीले (थ्रिप्स) चिपचिपे ट्रैप; पतंगों के लिए फेरोमोन ट्रैप\n- जैविक दवाएँ: इल्ली के लिए Bt, ब्यूवेरिया / मेटाराइज़ियम फफूँद, NPV\n- मित्र कीट: ट्राइकोग्रामा, लेडीबर्ड, लेसविंग, मकड़ी\n- खेत की सफ़ाई, फसल चक्र, संतुलित खाद, प्रतिरोधी किस्में",
}

HIGH = {
    "en": "**When infestation is high**\n1. Confirm in the field: count pests on 10–20 plants across the field, not just one photo.\n2. Compare with the economic threshold for your crop (ask KVK if unsure).\n3. Start IPM now: remove heavily infested parts, traps, biopesticides/neem.\n4. If a chemical is needed, use only a CIB&RC-registered product for this crop + pest, at label dose, with PPE.\n5. Re-scan after 3–5 days to check the trend.",
    "hinglish": "**Infestation high ho to kya karein**\n1. Khet mein confirm karein: alag-alag jagah ke 10–20 paudhon par keede ginein, sirf ek photo par na rukein.\n2. Apni fasal ke ETL (aarthik kshati star) se milayein — KVK se puchein.\n3. IPM shuru karein: zyada sankramit hisse hatayein, trap lagayein, jaivik dawa/neem.\n4. Dawa zaroori ho to sirf CIB&RC registered product, label ki matra mein, PPE pehen kar.\n5. 3–5 din baad dobara scan karke trend dekhein.",
    "hi": "**प्रकोप अधिक हो तो क्या करें**\n1. खेत में पुष्टि करें: अलग-अलग जगह के 10–20 पौधों पर कीट गिनें।\n2. अपनी फसल के आर्थिक क्षति स्तर (ETL) से तुलना करें — KVK से पूछें।\n3. IPM शुरू करें: अधिक संक्रमित भाग हटाएँ, ट्रैप, जैविक दवा/नीम।\n4. दवा ज़रूरी हो तो केवल CIB&RC पंजीकृत उत्पाद, लेबल की मात्रा में, PPE पहनकर।\n5. 3–5 दिन बाद फिर स्कैन करें।",
}


def _section(title: str, items: list[str]) -> str:
    return f"**{title}**\n" + "\n".join(f"- {i}" for i in items) if items else ""


def kb_answer(db: Session, user: User, text: str, lang: str) -> str:
    L = T[lang]
    low = text.lower()
    ctx, recent_pests = _recent_context(db, user)
    parts = []
    which_pest = any(k in low for k in ["kaun sa keeda", "kaun sa kida", "kon sa", "which pest", "what pest", "कौन सा", "kya laga", "keeda laga", "kida laga"])
    wants_treat = any(k in low for k in ["treat", "ilaj", "upay", "dawa", "control", "kya karu", "kya karun", "spray", "उपाय", "इलाज", "दवा", "manage"])
    if which_pest:
        parts.append(f"{L['latest']}\n{ctx}" if ctx else L["no_det"])
    if "neem" in low or "नीम" in text:
        parts.append(NEEM[lang])
    if any(k in low for k in ["high", "zyada", "jyada", "critical", "बहुत", "अधिक", "badh"]) and "infest" in low or "प्रकोप" in text:
        parts.append(HIGH[lang])
    if "organic" in low or "jaivik" in low or "ऑर्गेनिक" in text or "जैविक" in text:
        if not _kb_lookup(db, text, []):
            parts.append(ORGANIC_GENERAL[lang])
    entries = _kb_lookup(db, text, recent_pests if (wants_treat or which_pest) else [])
    for t in entries:
        name = t.common_name_hi if lang == "hi" and t.common_name_hi else t.common_name
        block = [f"{L['treat']} **{name}** ({t.scientific_name or t.pest_key}):"]
        block.append(_section(L["organic"], t.organic))
        block.append(_section(L["bio"], t.biological))
        block.append(_section(L["chem"], [c["class"] + " — " + c["note"] for c in t.chemical_categories]))
        block.append(_section(L["prev"], t.preventive))
        block.append(f"**{L['mon']}:** {t.monitoring}" + (f"\n_{t.etl_note}_" if t.etl_note else ""))
        parts.append("\n\n".join(b for b in block if b))
    if entries or any(p in parts for p in HIGH.values()):
        parts.append(f"**{L['safety']}:** {SAFETY[0]} {SAFETY[1]}\n\n{L['expert']}")
    if not parts:
        parts.append(L["unknown"])
    parts.append(f"_{L['kb_note']}_")
    return "\n\n".join(parts)


def answer(db: Session, user: User, text: str, history: list[ChatMessage], include_detections: bool) -> tuple[str, str, str]:
    lang = detect_language(text)
    if llm_enabled():
        ctx, recent = _recent_context(db, user) if include_detections else ("", [])
        kb = "\n\n".join(_kb_text(t) for t in _kb_lookup(db, text, recent))
        system = SYSTEM_PROMPT + (f"\n\nUser: {user.full_name}. Preferred language setting: {user.language}. "
                                  f"Detected message language: {lang}.")
        if ctx:
            system += f"\n\nThe user's recent AgriGuard scans (AI detections, may contain errors):\n{ctx}"
        if kb:
            system += f"\n\nRelevant entries from the AgriGuard curated knowledge base (prefer these facts):\n{kb}"
        msgs = [{"role": m.role, "content": m.content} for m in history[-10:]] + [{"role": "user", "content": text}]
        try:
            return _call_llm(system, msgs).strip(), lang, f"llm:{settings.llm_provider.lower()}"
        except Exception as e:
            log.warning("LLM call failed, using knowledge base: %s", e)
    return kb_answer(db, user, text, lang), lang, "knowledge_base"
