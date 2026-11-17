"""CSV export and PDF detection reports (ReportLab)."""
import csv
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models import Detection
from . import storage


def detections_csv(dets: list[Detection]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "date_utc", "crop", "growth_stage", "sample_type", "total_pests", "pest_counts",
                "mean_confidence", "severity_level", "severity_score", "inference_ms", "model_version"])
    for d in dets:
        counts: dict[str, int] = {}
        for i in d.instances:
            counts[i.pest_class] = counts.get(i.pest_class, 0) + 1
        w.writerow([d.id, d.created_at.isoformat(), d.crop.name if d.crop else "", d.growth_stage or "",
                    d.sample_type, d.total_count, "; ".join(f"{k}={v}" for k, v in counts.items()),
                    f"{d.mean_confidence:.3f}" if d.mean_confidence is not None else "",
                    d.severity.level if d.severity else "", d.severity.score if d.severity else "",
                    d.inference_ms, d.model_version.version if d.model_version else ""])
    return buf.getvalue()


GREEN = colors.HexColor("#14532d")


def detection_pdf(d: Detection, user_name: str, treatments: list[dict]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm,
                            bottomMargin=14 * mm, title=f"AgriGuard report #{d.id}")
    ss = getSampleStyleSheet()
    h1 = ss["Title"]; h1.textColor = GREEN
    h2 = ss["Heading2"]; h2.textColor = GREEN
    body = ss["BodyText"]
    small = ss["BodyText"].clone("small", fontSize=8, leading=10, textColor=colors.grey)
    el = [Paragraph("AgriGuard AI — Pest Detection Report", h1),
          Paragraph(f"Report #{d.id} · {d.created_at:%d %b %Y %H:%M} UTC · Farmer: {user_name}", body), Spacer(1, 6)]
    meta = [["Crop", d.crop.name if d.crop else "—", "Growth stage", d.growth_stage or "—"],
            ["Sample type", d.sample_type.replace("_", " "), "Model", d.model_version.version if d.model_version else "—"],
            ["Pests detected", str(d.total_count), "Inference time", f"{d.inference_ms:.0f} ms"],
            ["Severity", f"{d.severity.level.upper()} ({d.severity.score:.0f}/100)" if d.severity else "—",
             "Mean confidence", f"{(d.mean_confidence or 0) * 100:.1f}%"]]
    t = Table(meta, colWidths=[32 * mm, 55 * mm, 32 * mm, 55 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                           ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecfdf5")),
                           ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#ecfdf5")),
                           ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    el += [t, Spacer(1, 8)]
    try:
        img_bytes = storage.load(d.annotated_key or d.image_key)
        ratio = d.image_height / d.image_width if d.image_width else 0.75
        w = 120 * mm
        el += [Image(io.BytesIO(img_bytes), width=w, height=min(w * ratio, 110 * mm)), Spacer(1, 6)]
    except Exception:
        el.append(Paragraph("(Annotated image unavailable)", small))
    counts: dict[str, list[float]] = {}
    for i in d.instances:
        counts.setdefault(i.pest_class, []).append(i.confidence)
    if counts:
        el.append(Paragraph("Detected pests", h2))
        rows = [["Pest", "Count", "Avg confidence", "Density", "Level"]]
        dens = {x.pest_class: x for x in d.densities}
        for p, cs in sorted(counts.items(), key=lambda kv: -len(kv[1])):
            dn = dens.get(p)
            rows.append([p, len(cs), f"{sum(cs) / len(cs) * 100:.1f}%",
                         f"{dn.value:g} {dn.unit}" if dn else "—", dn.level if dn else "—"])
        tt = Table(rows, colWidths=[60 * mm, 18 * mm, 30 * mm, 42 * mm, 24 * mm])
        tt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), GREEN), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
        el += [tt, Spacer(1, 6)]
    if d.severity:
        el += [Paragraph("Severity assessment", h2), Paragraph(d.severity.explanation, body),
               Paragraph(f"<b>Recommended action:</b> {d.severity.recommended_action}", body)]
    for tr in treatments:
        el += [Paragraph(f"Management: {tr['common_name']}", h2)]
        for label, key in (("Organic", "organic"), ("Biological", "biological"), ("Prevention", "preventive"), ("IPM", "ipm")):
            if tr[key]:
                el.append(Paragraph(f"<b>{label}:</b> " + "; ".join(tr[key]), body))
        el.append(Paragraph("<b>Chemical classes (verify CIB&amp;RC registration and follow label):</b> "
                            + "; ".join(c["class"] for c in tr["chemical_categories"]), body))
    el += [Spacer(1, 10), Paragraph(
        "Disclaimer: detections are produced by an AI model and may contain errors; density and severity are a "
        "rule-based relative index, not a validated yield-loss prediction. Confirm in the field and consult your "
        "local KVK / agriculture officer before applying any pesticide. Use only CIB&amp;RC-registered products as per label, with PPE.",
        small)]
    doc.build(el)
    return buf.getvalue()
