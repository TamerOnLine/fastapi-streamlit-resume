from __future__ import annotations
from io import BytesIO
from typing import List, Tuple, Optional, Dict, Any

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from urllib.parse import urlparse


# ——— RTL (اختياري) ———
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    AR_OK = True
except Exception:
    AR_OK = False

# ===== ثوابت التباعد والخطوط =====
HEADING_SIZE = 14   # حجم العناوين الرئيسية/الثانوية
TEXT_SIZE    = 14   # حجم النص العادي
LEADING_BODY       = 12 # المسافة بين أسطر الفقرة (Lining)
LEADING_BODY_RTL   = 19 # في حالة RTL (عادة أكبر بسبب شكل الحروف)
GAP_AFTER_HEADING    = 10   # بعد العنوان الرئيسي/الثانوي
GAP_BETWEEN_PARAS    = 5    # بين الفقرات
GAP_BETWEEN_SECTIONS = 12   # بين أقسام السيرة
NAME_SIZE = 18  # حجم اسم المستخدم
NAME_GAP  = 10  # مسافة تحت الاسم

# ألوان/ستايل
LEFT_BG       = colors.HexColor("#f1f3f5")  # خلفية عمود اليسار
LEFT_BORDER   = colors.HexColor("#d0d4d9")
HEADING_COLOR = colors.black
SUBHEAD_COLOR = colors.HexColor("#0b7285")  # أزرق للعناوين (يمين)
MUTED         = colors.HexColor("#6c757d")

CARD_RADIUS   = 6     # نصف قطر زوايا الكارد
CARD_PAD      = 6 * mm  # حيز داخلي للكارد
RULE_COLOR    = colors.HexColor("#c9c9c9")  # لون الخط الفاصل

ICON_SIZE   = 6 * mm       # حجم الأيقونة (مربع)
ICON_PAD_X  = 6            # مسافة أفقية بين الأيقونة والنص
ICON_TEXT_DY = -6          # تزبيط بسيط لارتفاع النص
ICON_VALIGN = "middle"     # محاذاة عمودية للنص مع الأيقونة

LEFT_TEXT_SIZE = 12     # حجم نص عمود اليسار
LEFT_LINE_GAP  = 16     # المسافة بين أسطر نص عمود اليسار

LINKEDIN_REDIRECT_URL = "https://tamer.dev/in"
USE_LINKEDIN_REDIRECT = False 
USE_MOBILE_LINKEDIN   = False 

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

# ... RTL و register_font ...

AR_FONT = register_font("assets/NotoNaskhArabic-Regular.ttf")
# (اختياري) خط لعرض الإيموجي/الرموز

def register_ui_font(path: str, name: str = "DejaVuSans") -> str:
    try:
        pdfmetrics.registerFont(TTFont(name, path))
        return name
    except Exception:
        return "Helvetica"

UI_FONT = register_ui_font(r"C:\Windows\Fonts\seguisym.ttf", name="SegoeUISymbol")

ICONS = {
    "Ort": "📍",         # بديل آمن: "⌖"
    "Telefon": "☎",      # U+260E (آمن)
    "E-Mail": "✉",       # U+2709
    "Geburtsdatum": "🎂", # بديل آمن: "⌛"
    "GitHub": "🐙",       # أو "💻" (تجنّب  لأنه خط خاص)
    "LinkedIn": "🔗",     # أو "↗"
}

from urllib.parse import urlparse

def _canonical_linkedin_url(handle: str) -> str:
    """يعطي رابط لينكدإن موحّد من الـhandle فقط."""
    if USE_LINKEDIN_REDIRECT:
        return LINKEDIN_REDIRECT_URL
    if USE_MOBILE_LINKEDIN:
        return f"https://m.linkedin.com/in/{handle}/?trk=public_profile"
    return f"https://www.linkedin.com/in/{handle}/?trk=public_profile"

def _normalize_full_linkedin_url(raw: str) -> tuple[str, str] | None:
    """يأخذ رابط كامل (حتى لو بدون https) -> (handle, normalized_url)"""
    try:
        url = raw if "://" in raw else ("https://" + raw)
        p = urlparse(url)
        host = (p.netloc or "").lower()
        if "linkedin.com" not in host:
            return None
        parts = [seg for seg in (p.path or "").strip("/").split("/") if seg]
        # ندعم /in/<handle>/ أو /pub/ … الخ (نركز على in/)
        if parts and parts[0].lower() == "in" and len(parts) >= 2:
            handle = parts[1]
            # نكوّن رابطنا النهائي حسب الإعدادات
            final_url = _canonical_linkedin_url(handle)
            return handle, final_url
    except Exception:
        pass
    return None



def extract_social_handle(key: str, url_or_text: str) -> tuple[str, str] | None:
    raw = (url_or_text or "").strip()
    if not raw:
        return None

    # مجرد اسم مستخدم
    if "/" not in raw and " " not in raw and ":" not in raw:
        if key == "GitHub":
            return raw, f"https://github.com/{raw}"
        if key == "LinkedIn":
            return raw, _canonical_linkedin_url(raw)
        return None

    # رابط كامل
    if key == "GitHub":
        try:
            url = raw if "://" in raw else ("https://" + raw)
            p = urlparse(url)
            host = (p.netloc or "").lower()
            parts = [seg for seg in (p.path or "").strip("/").split("/") if seg]
            if "github.com" in host and parts:
                user = parts[0]
                return user, f"https://github.com/{user}"
        except Exception:
            pass
        return None

    if key == "LinkedIn":
        got = _normalize_full_linkedin_url(raw)
        if got:
            return got
        return None



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


def draw_round_rect(c: canvas.Canvas, x: float, y: float, w: float, h: float,
                    fill_color=LEFT_BG, stroke_color=LEFT_BORDER, radius=CARD_RADIUS):
    c.setFillColor(fill_color)
    c.setStrokeColor(stroke_color)
    c.roundRect(x, y, w, h, radius, stroke=1, fill=1)

def draw_rule(c: canvas.Canvas, x: float, y: float, w: float, color=RULE_COLOR):
    c.setStrokeColor(color)
    c.setLineWidth(0.7)
    c.line(x, y, x + w, y)

def draw_kv(c: canvas.Canvas, x: float, y: float, w: float,
            label: str, value: str, label_w: float = 28 * mm):
    """
    label: في عمود صغير غامق، value: في عمود أوسع
    يُعيد y بعد السطر.
    """
    c.setFont("Helvetica-Bold", TEXT_SIZE)
    c.setFillColor(HEADING_COLOR)
    c.drawString(x, y, f"{label}:")
    c.setFont("Helvetica", TEXT_SIZE)
    c.setFillColor(colors.black)
    c.drawString(x + label_w, y, value)
    return y - LEADING_BODY

def draw_icon_value(
    c: canvas.Canvas,
    x: float,
    y: float,
    icon: str,
    value: str,
    icon_box_w: float = 10 * mm,
    size: int = TEXT_SIZE,
) -> float:
    c.setFont(UI_FONT, size + 2)  # الرمز
    c.drawString(x, y, icon)
    c.setFont("Helvetica", size)  # النص
    c.drawString(x + icon_box_w, y, value)
    return y - LEADING_BODY



def draw_icon_img(c, x, y, img_path, value, icon_w=10*mm, icon_h=10*mm, size=TEXT_SIZE):
    try:
        img = ImageReader(img_path)
        # ملاحظة: y في ReportLab هي لأسفل الصورة
        c.drawImage(img, x, y - icon_h, width=icon_w, height=icon_h, mask='auto')
        c.setFont("Helvetica", size)
        c.setFillColor(colors.black)
        c.drawString(x + icon_w + 3, y, value)
        return y - LEADING_BODY
    except Exception:
        # لو الصورة مفقودة نرجع لطريقة الرمز النصّي
        return draw_icon_value(c, x, y, "•", value)

from reportlab.pdfbase import pdfmetrics

def draw_icon_line(
    c: canvas.Canvas,
    x: float,
    y: float,                  # baseline
    icon_path: str,
    value: str,
    *,
    icon_w: float = 8*mm,
    icon_h: float = 8*mm,
    pad_x: float = 6,
    size: int = TEXT_SIZE,
    valign: str = "middle",
    text_dy: float = 0,
    line_gap: int | None = None,
    max_w: float | None = None,
    halign: str = "left",
    container_w: float | None = None,
    link_url: str | None = None,          # ← جديد: رابط اختياري
) -> float:
    # قياس للتمركز العمودي
    font_name = "Helvetica"
    asc = pdfmetrics.getAscent(font_name) / 1000.0 * size
    dsc = abs(pdfmetrics.getDescent(font_name)) / 1000.0 * size

    # محاذاة أفقية (اختياري)
    text_w_nowrap = pdfmetrics.stringWidth(value, font_name, size)
    if halign in ("center", "right") and container_w:
        total_w = icon_w + pad_x + text_w_nowrap
        if halign == "center":
            x = x + (container_w - total_w) / 2.0
        else:
            x = x + (container_w - total_w)

    # 1) الأيقونة
    try:
        img = ImageReader(icon_path)
        c.drawImage(img, x, y - icon_h, width=icon_w, height=icon_h, mask="auto")
    except Exception:
        c.setFont(font_name, size + 2)
        c.drawString(x, y, "•")

    # 2) موضع النص
    text_x = x + icon_w + pad_x
    if valign == "top":
        baseline = y - icon_h + asc
    elif valign == "baseline":
        baseline = y
    else:  # middle
        half_text = (asc - dsc) / 2.0
        baseline = y - (icon_h / 2.0 - half_text)
    text_y = baseline + text_dy

    # 3) النص (+ رابط اختياري)
    c.setFont(font_name, size)
    if max_w is None:
        c.drawString(text_x, text_y, value)
        if link_url:
            tw = pdfmetrics.stringWidth(value, font_name, size)
            # مستطيل الرابط: من أسفل الحروف إلى أعلى بسيط
            c.linkURL(link_url, (text_x, text_y - dsc, text_x + tw, text_y + asc * 0.2), relative=0, thickness=0)
        used_h = max(icon_h, asc + dsc)
        gap = line_gap if line_gap is not None else max(LEADING_BODY, used_h + 2)
        return y - gap
    else:
        text_w = max_w - (text_x - x)
        lines = wrap_text(value, font_name, size, text_w)
        cur_y = text_y
        for i, ln in enumerate(lines):
            c.drawString(text_x, cur_y, ln)
            if link_url and i == 0:  # نربط السطر الأول فقط
                tw = pdfmetrics.stringWidth(ln, font_name, size)
                c.linkURL(link_url, (text_x, cur_y - dsc, text_x + tw, cur_y + asc * 0.2), relative=0, thickness=0)
            cur_y -= (line_gap if line_gap is not None else LEADING_BODY)
        block_h = (text_y - cur_y) + (line_gap if line_gap is not None else LEADING_BODY)
        used_h = max(icon_h, block_h)
        return y - used_h

# ——— معلومات شخصية مع أيقونات ———
# مسارات الأيقونات (PNG)

ICON_PATHS = {
    "Ort":          "assets/icons/pin.png",
    "Telefon":      "assets/icons/phone.png",
    "E-Mail":       "assets/icons/mail.png",
    "Geburtsdatum": "assets/icons/cake.png",
    "GitHub":       "assets/icons/github.png",
    "LinkedIn":     "assets/icons/linkedin.png",
}

def info_line(
    c: canvas.Canvas,
    x: float,
    y: float,
    key: str,              # "GitHub" | "LinkedIn" | ...
    value: str,
    max_w: float,
    align_h: str = "left",
    line_gap: int = LEFT_LINE_GAP,
    size: int = LEFT_TEXT_SIZE,
) -> float:
    if not value:
        return y

    # تحضير نص العرض والرابط (GitHub/LinkedIn)
    display = value
    link = None
    if key in ("GitHub", "LinkedIn"):
        got = extract_social_handle(key, value)
        if got:
            display, link = got  # display=username, link=full url

    path = ICON_PATHS.get(key)
    if not path:
        c.setFont("Helvetica", size)
        c.drawString(x, y, display)
        return y - line_gap

    return draw_icon_line(
        c=c, x=x, y=y, icon_path=path, value=display,
        icon_w=ICON_SIZE, icon_h=ICON_SIZE,
        pad_x=ICON_PAD_X, size=size,
        valign=ICON_VALIGN, text_dy=ICON_TEXT_DY,
        line_gap=line_gap, max_w=max_w,
        halign=align_h, container_w=max_w,
        link_url=link,                         # ← هنا نمرّر الرابط
    )


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
    left_w = 0.40 * (W - 2 * margin - gutter)
    right_w = 0.60 * (W - 2 * margin - gutter)
    left_x = margin
    right_x = margin + left_w + gutter

    y_top = H - margin

    # ------------------ كارد العمود اليسار (صورة + اسم + معلومات) ------------------
    CARD_TOP    = y_top
    CARD_W      = left_w
    CARD_H      = H - 2*margin
    CARD_X      = left_x
    CARD_Y      = margin

    # خلفية الكارد
    draw_round_rect(c, CARD_X, CARD_Y, CARD_W, CARD_H)

    # حيز داخلي
    inner_x = CARD_X + CARD_PAD
    inner_w = CARD_W - 2*CARD_PAD
    cursor  = CARD_TOP - CARD_PAD  # نبدأ من أعلى الكارد للداخل بقليل

    # الصورة في وسط الكارد
    if photo_bytes:
        try:
            img = ImageReader(BytesIO(photo_bytes))
            max_w, max_h = inner_w, 42*mm
            iw, ih = img.getSize()
            s = min(max_w/iw, max_h/ih)
            pw, ph = iw*s, ih*s
            px = inner_x + (inner_w - pw) / 2
            py = cursor - ph
            c.drawImage(img, px, py, width=pw, height=ph, preserveAspectRatio=True, mask="auto")
            cursor = py - 6*mm
        except Exception:
            pass

    # الاسم في وسط الكارد
    if name:
        c.setFont("Helvetica-Bold", NAME_SIZE)
        c.setFillColor(HEADING_COLOR)
        c.drawCentredString(inner_x + inner_w/2, cursor, name)
        cursor -= NAME_GAP*mm

    # عنوان فرعي + خط
    c.setFont("Helvetica-Bold", HEADING_SIZE)
    c.setFillColor(HEADING_COLOR)
    c.drawCentredString(inner_x + inner_w/2, cursor, "Persönliche Informationen")
    cursor -= 6
    draw_rule(c, inner_x, cursor, inner_w)
    cursor -= 6

    # معلومات (Label: Value)
    inner_w_available = inner_w  # عرض الكارد الداخلي

    if location:  cursor = info_line(c, inner_x, cursor, "Ort",          location,  inner_w_available)
    if phone:     cursor = info_line(c, inner_x, cursor, "Telefon",      phone,     inner_w_available)
    if email:     cursor = info_line(c, inner_x, cursor, "E-Mail",       email,     inner_w_available)
    if birthdate: cursor = info_line(c, inner_x, cursor, "Geburtsdatum", birthdate, inner_w_available)
    if github:    cursor = info_line(c, inner_x, cursor, "GitHub",       github,    inner_w_available)
    if linkedin:  cursor = info_line(c, inner_x, cursor, "LinkedIn",     linkedin,  inner_w_available)

    # مهارات داخل الكارد
    if skills:
        cursor -= 6
        c.setFont("Helvetica-Bold", HEADING_SIZE)
        c.setFillColor(HEADING_COLOR)
        c.drawCentredString(inner_x + inner_w/2, cursor, "Technische Fähigkeiten")
        cursor -= 6
        draw_rule(c, inner_x, cursor, inner_w)
        cursor -= 6

        c.setFont("Helvetica", TEXT_SIZE)
        c.setFillColor(colors.black)
        for sk in skills:
            # نقطة بسيطة كبولِت
            c.circle(inner_x + 2.5, cursor + 3, 1.2, stroke=1, fill=1)
            c.drawString(inner_x + 8, cursor, sk)
            cursor -= LEADING_BODY

    # لغات (اختياري داخل الكارد)
    if languages:
        cursor -= 6
        c.setFont("Helvetica-Bold", HEADING_SIZE)
        c.drawCentredString(inner_x + inner_w/2, cursor, "Sprachen")
        cursor -= 6
        draw_rule(c, inner_x, cursor, inner_w)
        cursor -= 6

        c.setFont("Helvetica", TEXT_SIZE)
        c.setFillColor(colors.black)
        lang_line = ", ".join(languages)
        cursor = draw_par(
            c=c, x=inner_x, y=cursor,
            lines=[lang_line], font="Helvetica", size=TEXT_SIZE,
            max_w=inner_w, align="left", rtl_mode=False
        )

    # لا نستخدم yL هنا لأن كل شيء صار داخل الكارد.
    # ابدأ العمود الأيمن من أعلى المحتوى
    yR = y_top - GAP_AFTER_HEADING
    # ---------------------------------------------------------------------------


    # ===== العمود الأيمن =====
    # عنوان رئيسي
    c.setFont("Helvetica-Bold", HEADING_SIZE)
    c.setFillColor(HEADING_COLOR)
    c.drawString(right_x, yR, "Ausgewählte Projekte")
    yR -= GAP_AFTER_HEADING
    draw_rule(c, right_x, yR, right_w)
    yR -= 8

    for title, desc, link in projects:
        # عنوان المشروع (أزرق)
        c.setFont("Helvetica-Bold", TEXT_SIZE + 1)
        c.setFillColor(SUBHEAD_COLOR)
        c.drawString(right_x, yR, title or "")
        yR -= (GAP_AFTER_HEADING // 2)

        # الوصف
        c.setFillColor(colors.black)
        yR = draw_par(
            c=c, x=right_x, y=yR,
            lines=(desc or "").split("\n"),
            font=(AR_FONT if rtl_mode else "Helvetica"),
            size=TEXT_SIZE, max_w=right_w,
            align=("right" if rtl_mode else "left"),
            rtl_mode=rtl_mode
        )

        # Repo
        if link:
            c.setFont("Helvetica-Bold", TEXT_SIZE)
            c.setFillColor(HEADING_COLOR)
            c.drawString(right_x, yR, "Repo:")
            c.setFont("Helvetica", TEXT_SIZE)
            c.setFillColor(colors.black)
            c.drawString(right_x + 30, yR, link)
            yR -= LEADING_BODY

        yR -= GAP_AFTER_HEADING

    # خط فاصل + عنوان التعليم
    draw_rule(c, right_x, yR, right_w)
    yR -= 10

    c.setFont("Helvetica-Bold", HEADING_SIZE)
    c.setFillColor(HEADING_COLOR)
    c.drawString(right_x, yR, "Berufliche Weiterbildung")
    yR -= GAP_AFTER_HEADING
    draw_rule(c, right_x, yR, right_w)
    yR -= 8

    if education_items:
        c.setFillColor(colors.black)
        yR = draw_par(
            c=c, x=right_x, y=yR,
            lines=education_items, font="Helvetica", size=TEXT_SIZE,
            max_w=right_w, align="left", rtl_mode=False
        )

    c.showPage()
    c.save()
    out = buffer.getvalue()
    buffer.close()
    return out
