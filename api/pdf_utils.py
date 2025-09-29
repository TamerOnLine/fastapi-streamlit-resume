from __future__ import annotations
from io import BytesIO
from typing import List, Tuple, Optional, Dict, Any

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ——— RTL (اختياري) ———
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    AR_OK = True
except Exception:
    AR_OK = False

# ===== ثوابت التباعد والخطوط =====
HEADING_SIZE = 12
TEXT_SIZE    = 10
LEADING_BODY       = 18
LEADING_BODY_RTL   = 19
GAP_AFTER_HEADING    = 10
GAP_BETWEEN_PARAS    = 5
GAP_BETWEEN_SECTIONS = 12
NAME_SIZE = 18
NAME_GAP  = 10  # mm

def rtl(txt: str) -> str:
    if not txt:
        return ""
    if AR_OK:
        return get_display(arabic_reshaper.reshape(txt))
    return txt

def register_font(path: str, name: str = "NotoNaskh") -> str:
    try:
        pdfmetrics.registerFont(TTFont(name, path))
        return name
    except Exception:
        return "Helvetica"

AR_FONT = register_font("assets/NotoNaskhArabic-Regular.ttf")

# ——— تغليف نص ———
def wrap_text(text: str, font: str, size: int, max_w: float) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        trial = f"{cur} {w}"
        if pdfmetrics.stringWidth(trial, font, size) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines

def wrap_lines(lines: List[str], font: str, size: int, max_w: float, do_rtl=False) -> List[str]:
    out: List[str] = []
    for ln in lines:
        t = rtl(ln) if do_rtl else ln
        out.extend(wrap_text(t, font, size, max_w))
    return out

def draw_par(
    c: canvas.Canvas,
    x: float,
    y: float,
    lines: List[str],
    font: str,
    size: int,
    max_w: float,
    align: str = "left",
    rtl_mode: bool = False,
    leading: int | None = None,
) -> float:
    """
    يرسم فقرة/فقرات. إذا لم تُمرَّر leading نحسبها تلقائياً من الثوابت.
    نضيف GAP_BETWEEN_PARAS بعد كل فقرة.
    """
    c.setFont(font, size)
    cur = y
    line_gap = leading if leading is not None else (
        LEADING_BODY_RTL if (rtl_mode and align == "right") else LEADING_BODY
    )

    for raw in lines:
        txt = rtl(raw) if (rtl_mode and align == "right") else raw
        wrapped = wrap_text(txt, font, size, max_w) if txt else [""]
        for ln in wrapped:
            if align == "right":
                c.drawRightString(x + max_w, cur, ln)
            else:
                c.drawString(x, cur, ln)
            cur -= line_gap
        cur -= GAP_BETWEEN_PARAS
    return cur


def draw_section(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    title: str,
    body: List[str],
    *,
    rtl_mode: bool = False,
    align: str = "left",
    title_size: int = HEADING_SIZE,
    text_size: int = TEXT_SIZE,
    body_leading: int | None = None,
) -> float:
    if not title and not body:
        return y

    # عنوان القسم
    c.setFont("Helvetica-Bold", title_size)
    if align == "right":
        c.drawRightString(x + w, y, rtl(title) if rtl_mode else title)
    else:
        c.drawString(x, y, title)
    y -= GAP_AFTER_HEADING

    # نصوص القسم
    y = draw_par(
        c=c,
        x=x,
        y=y,
        lines=body,
        font=(AR_FONT if (rtl_mode and align == "right") else "Helvetica"),
        size=text_size,
        max_w=w,
        align=align,
        rtl_mode=rtl_mode,
        leading=body_leading,
    )

    return y - GAP_BETWEEN_SECTIONS


# ——— المولّد ———
def build_resume_pdf(
    *,
    name: str = "",
    location: str = "",
    phone: str = "",
    email: str = "",
    github: str = "",
    linkedin: str = "",
    birthdate: str = "",
    skills: List[str] = (),
    languages: List[str] = (),
    projects: List[Tuple[str, str, Optional[str]]] = (),
    education_items: List[str] = (),
    photo_bytes: Optional[bytes] = None,
    rtl_mode: bool = False,
    sections_left: List[Dict[str, Any]] | None = None,
    sections_right: List[Dict[str, Any]] | None = None,
) -> bytes:
    sections_left = sections_left or []
    sections_right = sections_right or []

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4

    # تخطيط: 30% يسار / 70% يمين
    margin = 16 * mm
    gutter = 8 * mm
    left_w = 0.30 * (W - 2 * margin - gutter)
    right_w = 0.70 * (W - 2 * margin - gutter)
    left_x = margin
    right_x = margin + left_w + gutter

    y_top = H - margin

    # صورة
    if photo_bytes:
        try:
            img = ImageReader(BytesIO(photo_bytes))
            pw, ph = 28 * mm, 36 * mm
            c.drawImage(img, W - margin - pw, H - margin - ph, pw, ph, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    # الاسم
    if name:
        c.setFont("Helvetica-Bold", NAME_SIZE)
        c.drawString(left_x, y_top, name)
    yL = y_top - NAME_GAP * mm
    yR = y_top - NAME_GAP * mm

    # العمود الأيسر
    info_lines = []
    if location:  info_lines.append(f"Ort: {location}")
    if phone:     info_lines.append(f"Telefon: {phone}")
    if email:     info_lines.append(f"E-Mail: {email}")
    if birthdate: info_lines.append(f"Geburtsdatum: {birthdate}")
    if github:    info_lines.append(f"GitHub: {github}")
    if linkedin:  info_lines.append(f"LinkedIn: {linkedin}")

    if info_lines:
        yL = draw_section(c, left_x, yL, left_w, "Persönliche Informationen", info_lines)

    if skills:
        yL = draw_section(c, left_x, yL, left_w, "Technische Fähigkeiten", [", ".join(skills)])
    if languages:
        yL = draw_section(c, left_x, yL, left_w, "Sprachen", [", ".join(languages)])

    for sec in sections_left:
        title = (sec.get("title") or "").strip()
        lines = [str(x).strip() for x in (sec.get("lines") or []) if str(x).strip()]
        if title and lines:
            yL = draw_section(c, left_x, yL, left_w, title, lines)

    # العمود الأيمن
    if projects:
        c.setFont("Helvetica-Bold", HEADING_SIZE)
        c.drawString(right_x, yR, "Ausgewählte Projekte")
        yR -= GAP_AFTER_HEADING

        for title, desc, link in projects:
            # عنوان المشروع
            c.setFont("Helvetica-Bold", TEXT_SIZE + 1)
            c.drawString(right_x, yR, title or "")
            yR -= GAP_AFTER_HEADING // 2

            # وصف المشروع (← هنا كان الاستدعاء الخاطئ)
            yR = draw_par(
                c=c,
                x=right_x,
                y=yR,
                lines=(desc or "").split("\n"),
                font=(AR_FONT if rtl_mode else "Helvetica"),
                size=TEXT_SIZE,
                max_w=right_w,
                align=("right" if rtl_mode else "left"),
                rtl_mode=rtl_mode,
                # leading=None  ← يُحسب تلقائياً
            )

            # رابط (اختياري)
            if link:
                c.setFont("Helvetica-Oblique", TEXT_SIZE - 1)
                if rtl_mode:
                    c.drawRightString(right_x + right_w, yR, rtl(f"Repo/Link: {link}"))
                else:
                    c.drawString(right_x, yR, f"Repo/Link: {link}")
                yR -= GAP_BETWEEN_PARAS + 1

    if education_items:
        yR = draw_section(c, right_x, yR, right_w, "Berufliche Weiterbildung", education_items)

    for sec in sections_right:
        title = (sec.get("title") or "").strip()
        lines = [str(x).strip() for x in (sec.get("lines") or []) if str(x).strip()]
        if title and lines:
            yR = draw_section(
                c, right_x, yR, right_w, title, lines,
                rtl_mode=rtl_mode, align=("right" if rtl_mode else "left")
            )

    c.showPage()
    c.save()
    out = buffer.getvalue()
    buffer.close()
    return out
