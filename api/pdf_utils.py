from __future__ import annotations
from io import BytesIO
from typing import List, Tuple, Optional, Dict, Any

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from urllib.parse import urlparse


# ——— RTL (اختياري) ———
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    AR_OK = True
except Exception:
    AR_OK = False

# ===============================
# Typography & Spacing (A4 tuned)
# ===============================
HEADING_SIZE = 14           # عناوين الأقسام (يمين/يسار)
TEXT_SIZE    = 12           # نص الفقرات القياسي
NAME_SIZE    = 18           # اسم كبير أعلى الكارد اليسار
NAME_GAP     = 10           # (mm) فراغ تحت الاسم قبل المحتوى

# ===== ضبط خط نص العمود اليسار =====
LEFT_TEXT_FONT       = "Helvetica"
LEFT_TEXT_FONT_BOLD  = "Helvetica-Bold"
LEFT_TEXT_IS_BOLD    = True    # ← بدّلها إلى False لو تريد عادي


# مسافات الأسطر (line height)
LEADING_BODY      = 12      # ≈ 1.5× من 12pt — مريح للقراءة
LEADING_BODY_RTL  = 20      # RTL يحتاج مسافة أكبر قليلًا

# فراغات رأسية عامة
GAP_AFTER_HEADING    = 10   # بعد عنوان القسم
GAP_BETWEEN_PARAS    = 10    # بين الفقرات داخل نفس القسم
GAP_BETWEEN_SECTIONS = 12   # بين الأقسام المتتالية

# ===============
# Colors & Rules
# ===============
from reportlab.lib import colors
LEFT_BG       = colors.HexColor("#F7F8FA")  # خلفية الكارد اليسار فاتحة
LEFT_BORDER   = colors.HexColor("#E3E6EA")  # إطار خفيف للكارد
HEADING_COLOR = colors.black                # لون العناوين
SUBHEAD_COLOR = colors.HexColor("#0B7285")  # عناوين فرعية (مشاريع يمين)
MUTED         = colors.HexColor("#6C757D")  # ميتاداتا ثانوية
RULE_COLOR    = colors.HexColor("#D7DBE0")  # لون الخطوط الفاصلة
EDU_TITLE_COLOR = SUBHEAD_COLOR # لون عنوان التعليم

# =============
# Card Styling
# =============
from reportlab.lib.units import mm
CARD_RADIUS = 6            # زوايا الكارد اليسار
CARD_PAD    = 6 * mm       # حيز داخلي للكارد

# =========
# Icons Row
# =========
ICON_SIZE    = 6 * mm      # حجم الأيقونة (مربع)
ICON_PAD_X   = 4           # مسافة بين الأيقونة والنص
ICON_TEXT_DY = -5          # تصحيح بسيط لخط الأساس للنص بجانب الأيقونة
ICON_VALIGN  = "middle"    # محاذاة عمودية للنص مع وسط الأيقونة

# =======================================
# Left column (inside card) base text
# =======================================
LEFT_TEXT_SIZE = 12        # حجم النص داخل الكارد
LEFT_LINE_GAP  = 10        # مسافة السطر داخل الكارد (قوائم/بنود)

# =======================================
# Left extra sections (inside card)
# =======================================
LEFT_SEC_HEADING_SIZE      = 14   # عنوان القسم
LEFT_SEC_TEXT_SIZE         = 12   # بنود القسم
LEFT_SEC_TITLE_TOP_GAP     = 6    # قبل العنوان
LEFT_SEC_TITLE_BOTTOM_GAP  = 6    # بعد العنوان وقبل الخط
LEFT_SEC_RULE_COLOR        = RULE_COLOR # لون الخط
LEFT_SEC_RULE_WIDTH        = 1    # سمك الخط
LEFT_SEC_RULE_TO_LIST_GAP  = 15    # بعد الخط وقبل أول بند
LEFT_SEC_LINE_GAP          = 20   # مسافة بين البنود
LEFT_SEC_BULLET_RADIUS     = 1.2  # نقطة البولت
LEFT_SEC_BULLET_X_OFFSET   = 2.5  # إزاحة X للنقطة
LEFT_SEC_TEXT_X_OFFSET     = 8    # إزاحة نص البند عن النقطة
LEFT_SEC_SECTION_GAP       = 2    # فراغ بسيط بعد نهاية كل قسم
LEFT_AFTER_CONTACT_GAP = 10    # فراغ بعد معلومات الاتصال وقبل الأقسام الإضافية  

# =======================================
# Right extra sections (main column)
# =======================================
RIGHT_SEC_HEADING_SIZE       = HEADING_SIZE   # اتساق مع العناوين
RIGHT_SEC_TEXT_SIZE          = TEXT_SIZE      # اتساق مع الفقرات
RIGHT_SEC_TITLE_TO_RULE_GAP  = 10             # بعد العنوان وقبل الخط
RIGHT_SEC_RULE_COLOR         = RULE_COLOR   # لون الخط
RIGHT_SEC_RULE_WIDTH         = 0.8  
RIGHT_SEC_RULE_TO_TEXT_GAP   = 14            # بعد الخط وقبل النص
RIGHT_SEC_LINE_GAP           = 12   # مسافة السطر داخل الفقرات
RIGHT_SEC_SECTION_GAP        = GAP_BETWEEN_SECTIONS  # فراغ بين الأقسام
LEFT_SEC_TITLE_ALIGN = "left"  # "left" | "center" | "right"

RIGHT_SEC_PARA_GAP = 4 

# ===== Projects layout =====
PROJECT_TITLE_SIZE         = TEXT_SIZE + 1   # حجم عنوان المشروع
PROJECT_TITLE_GAP_BELOW    = 14               # فراغ تحت عنوان المشروع
PROJECT_DESC_LEADING       = 14              # ← مسافة السطر داخل وصف المشروع
PROJECT_DESC_PARA_GAP      = 2               # فراغ بسيط بين فقرات الوصف
PROJECT_LINK_TEXT_SIZE     = TEXT_SIZE - 1   # حجم خط الرابط
PROJECT_LINK_GAP_ABOVE     = -10              # فراغ فوق سطر الرابط
PROJECT_BLOCK_GAP          = 24              # فراغ بعد كل مشروع قبل التالي


# --- Weiterbildung (Education) spacing ---
EDU_TEXT_LEADING = 12      # جرّب 14–16 حسب ذوقك
EDU_PARA_GAP     = GAP_BETWEEN_PARAS

# =======================================
# LinkedIn handling (professional setup)
# =======================================
LINKEDIN_REDIRECT_URL = "https://tamer.dev/in"  # رابط وسيط مملوك لك (اختياري)
USE_LINKEDIN_REDIRECT = False                   # True لو تريد استخدام الرابط الوسيط دائمًا
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
    para_gap: int | None = None,   # ← جديد
) -> float:
    c.setFont(font, size)
    cur = y
    line_gap = leading if leading is not None else (
        LEADING_BODY_RTL if (rtl_mode and align == "right") else LEADING_BODY
    )
    gap_between_paras = GAP_BETWEEN_PARAS if para_gap is None else para_gap  # ← جديد

    for raw in lines:
        txt = rtl(raw) if (rtl_mode and align == "right") else raw
        wrapped = wrap_text(txt, font, size, max_w) if txt else [""]
        for ln in wrapped:
            if align == "right":
                c.drawRightString(x + max_w, cur, ln)
            else:
                c.drawString(x, cur, ln)
            cur -= line_gap
        cur -= gap_between_paras   # ← استخدم الفاصل الممرَّر
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
    size: int = LEFT_TEXT_SIZE,
    valign: str = "middle",
    text_dy: float = 0,
    line_gap: int | None = None,
    max_w: float | None = None,
    halign: str = "left",
    container_w: float | None = None,
    link_url: str | None = None,
) -> float:
    # الخط المستخدم لقيمة النص
    value_font = LEFT_TEXT_FONT_BOLD if LEFT_TEXT_IS_BOLD else LEFT_TEXT_FONT

    # استخدم نفس الخط للقياسات حتى يكون التمركز صحيحًا
    asc = pdfmetrics.getAscent(value_font) / 1000.0 * size
    dsc = abs(pdfmetrics.getDescent(value_font)) / 1000.0 * size

    # محاذاة أفقية (اختياري)
    text_w_nowrap = pdfmetrics.stringWidth(value, value_font, size)
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
        # fallback بسيط لو الصورة غير متوفرة
        c.setFont(value_font, size + 2)
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
    c.setFont(value_font, size)
    if max_w is None:
        c.drawString(text_x, text_y, value)
        if link_url:
            tw = pdfmetrics.stringWidth(value, value_font, size)
            c.linkURL(link_url, (text_x, text_y - dsc, text_x + tw, text_y + asc*0.2),
                      relative=0, thickness=0)
        used_h = max(icon_h, asc + dsc)
        gap = line_gap if line_gap is not None else max(LEADING_BODY, used_h + 2)
        return y - gap
    else:
        text_w = max_w - (text_x - x)
        lines = wrap_text(value, value_font, size, text_w)
        cur_y = text_y
        for i, ln in enumerate(lines):
            c.drawString(text_x, cur_y, ln)
            if link_url and i == 0:
                tw = pdfmetrics.stringWidth(ln, value_font, size)
                c.linkURL(link_url, (text_x, cur_y - dsc, text_x + tw, cur_y + asc*0.2),
                          relative=0, thickness=0)
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

def draw_left_extra_sections(
    c: canvas.Canvas,
    inner_x: float,
    inner_w: float,
    cursor: float,
    sections_left: list[dict],
) -> float:
    """يرسم الأقسام الإضافية داخل الكارد يسار باستخدام متغيرات الضبط أعلاه."""
    for sec in (sections_left or []):
        title = (sec.get("title") or "").strip()
        lines = [str(x).strip() for x in (sec.get("lines") or []) if str(x).strip()]
        if not title or not lines:
            continue

        # فراغ قبل العنوان
        cursor -= LEFT_SEC_TITLE_TOP_GAP

        # عنوان القسم
        c.setFont("Helvetica-Bold", LEFT_SEC_HEADING_SIZE)
        c.setFillColor(colors.black)
        if LEFT_SEC_TITLE_ALIGN == "center":
            c.drawCentredString(inner_x + inner_w/2, cursor, title)
        elif LEFT_SEC_TITLE_ALIGN == "right":
            c.drawRightString(inner_x + inner_w, cursor, title)
        else:  # left
            c.drawString(inner_x, cursor, title)

        # خط فاصل
        cursor -= LEFT_SEC_TITLE_BOTTOM_GAP
        c.setStrokeColor(LEFT_SEC_RULE_COLOR)
        c.setLineWidth(LEFT_SEC_RULE_WIDTH)
        c.line(inner_x, cursor, inner_x + inner_w, cursor)

        # بداية العناصر
        cursor -= LEFT_SEC_RULE_TO_LIST_GAP
        c.setFont("Helvetica", LEFT_SEC_TEXT_SIZE)
        c.setFillColor(colors.black)
        for ln in lines:
            # نقطة بولِت
            c.circle(inner_x + LEFT_SEC_BULLET_X_OFFSET,
                     cursor + 3, LEFT_SEC_BULLET_RADIUS, stroke=1, fill=1)
            # نص العنصر
            c.drawString(inner_x + LEFT_SEC_TEXT_X_OFFSET, cursor, ln)
            cursor -= LEFT_SEC_LINE_GAP

        # فراغ بعد القسم (اختياري)
        cursor -= LEFT_SEC_SECTION_GAP

    return cursor


def draw_right_extra_sections(
    c: canvas.Canvas,
    right_x: float,
    right_w: float,
    yR: float,
    sections_right: list[dict],
) -> float:
    """يرسم الأقسام الإضافية في العمود اليمين باستخدام متغيرات الضبط أعلاه."""
    for sec in (sections_right or []):
        title = (sec.get("title") or "").strip()
        lines = [str(x).strip() for x in (sec.get("lines") or []) if str(x).strip()]
        if not title or not lines:
            continue

        # عنوان
        c.setFont("Helvetica-Bold", RIGHT_SEC_HEADING_SIZE)
        c.setFillColor(colors.black)
        c.drawString(right_x, yR, title)
        yR -= RIGHT_SEC_TITLE_TO_RULE_GAP

        # خط
        c.setStrokeColor(RIGHT_SEC_RULE_COLOR)
        c.setLineWidth(RIGHT_SEC_RULE_WIDTH)
        c.line(right_x, yR, right_x + right_w, yR)
        yR -= RIGHT_SEC_RULE_TO_TEXT_GAP

        # نصوص (التفاف) بمسافة سطر مضبوطة
        c.setFont("Helvetica", RIGHT_SEC_TEXT_SIZE)
        c.setFillColor(colors.black)
        yR = draw_par(
            c=c, x=right_x, y=yR,
            lines=lines,
            font="Helvetica", size=RIGHT_SEC_TEXT_SIZE, max_w=right_w,
            align="left", rtl_mode=False,
            leading=RIGHT_SEC_LINE_GAP,   # تباعد السطر (مثلاً 12–14)
            para_gap=RIGHT_SEC_PARA_GAP,  # تباعد بين البنود (مثلاً 0–4)
        )


        # فراغ بين الأقسام
        yR -= RIGHT_SEC_SECTION_GAP

    return yR




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

    # الصورة في وسط الكارد (دائرية)
    if photo_bytes:
        try:
            img = ImageReader(BytesIO(photo_bytes))

            # قطر الدائرة (مربع الاحتواء)
            max_d = 42*mm                       # غيّرها لو حاب تكبر/تصغر
            d = min(inner_w, max_d)
            r = d / 2.0

            # مركز الدائرة: منتصف الكارد أفقياً وتحت الكرسر بمقدار نصف القطر
            cx = inner_x + inner_w/2.0
            cy = cursor - r

            # مربّع الصورة الذي سنقصّه بالدائرة
            ix = cx - r
            iy = cy - r

            # قصّ بمسار دائري ثم ارسم الصورة
            c.saveState()
            p = c.beginPath()
            p.circle(cx, cy, r)
            c.clipPath(p, stroke=0, fill=0)

            # ارسم الصورة داخل المربّع المحيط بالدائرة
            c.drawImage(img, ix, iy, width=d, height=d,
                        preserveAspectRatio=True, mask="auto")

            c.restoreState()

            # (اختياري) إطار خفيف حول الدائرة
            c.setStrokeColor(LEFT_BORDER)
            c.setLineWidth(1)
            c.circle(cx, cy, r)

            # انزل تحت الصورة بقليل
            cursor = iy - 6*mm

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

    # ... بعد آخر info_line
    info_drawn = any([location, phone, email, birthdate, github, linkedin])
    if info_drawn:
        cursor -= LEFT_AFTER_CONTACT_GAP
    # ---------------------------------------------------------------------------



    # ===== المهارات داخل الكارد (بعنوان وخط فاصل وبنود ملتفة) =====
    if skills:
        # عنوان القسم
        cursor -= LEFT_SEC_TITLE_TOP_GAP
        c.setFont("Helvetica-Bold", LEFT_SEC_HEADING_SIZE)
        c.setFillColor(HEADING_COLOR)

        if LEFT_SEC_TITLE_ALIGN == "center":
            c.drawCentredString(inner_x + inner_w/2, cursor, "Technische Fähigkeiten")
        elif LEFT_SEC_TITLE_ALIGN == "right":
            c.drawRightString(inner_x + inner_w, cursor, "Technische Fähigkeiten")
        else:  # left
            c.drawString(inner_x, cursor, "Technische Fähigkeiten")

        # خط فاصل
        cursor -= LEFT_SEC_TITLE_BOTTOM_GAP
        c.setStrokeColor(LEFT_SEC_RULE_COLOR)
        c.setLineWidth(LEFT_SEC_RULE_WIDTH)
        c.line(inner_x, cursor, inner_x + inner_w, cursor)

        # عناصر المهارات (مع التفاف داخل كل بند)
        cursor -= LEFT_SEC_RULE_TO_LIST_GAP
        c.setFont("Helvetica", LEFT_SEC_TEXT_SIZE)
        c.setFillColor(colors.black)

        max_text_w = inner_w - (LEFT_SEC_TEXT_X_OFFSET + 2)

        for sk in skills:
            wrapped = wrap_text(sk, "Helvetica", LEFT_SEC_TEXT_SIZE, max_text_w)
            for i, ln in enumerate(wrapped):
                if i == 0:  # النقطة للسطر الأول فقط
                    c.circle(inner_x + LEFT_SEC_BULLET_X_OFFSET,
                            cursor + 3, LEFT_SEC_BULLET_RADIUS, stroke=1, fill=1)
                c.drawString(inner_x + LEFT_SEC_TEXT_X_OFFSET, cursor, ln)
                cursor -= LEFT_SEC_LINE_GAP

        cursor -= LEFT_SEC_SECTION_GAP  # فراغ بعد القسم

    # ===== اللغات داخل الكارد =====
    if languages:
        cursor -= LEFT_SEC_TITLE_TOP_GAP
        c.setFont("Helvetica-Bold", LEFT_SEC_HEADING_SIZE)
        if LEFT_SEC_TITLE_ALIGN == "center":
            c.drawCentredString(inner_x + inner_w/2, cursor, "Sprachen")
        elif LEFT_SEC_TITLE_ALIGN == "right":
            c.drawRightString(inner_x + inner_w, cursor, "Sprachen")
        else:
            c.drawString(inner_x, cursor, "Sprachen")

        cursor -= LEFT_SEC_TITLE_BOTTOM_GAP
        c.setStrokeColor(LEFT_SEC_RULE_COLOR)
        c.setLineWidth(LEFT_SEC_RULE_WIDTH)
        c.line(inner_x, cursor, inner_x + inner_w, cursor)

        cursor -= LEFT_SEC_RULE_TO_LIST_GAP
        c.setFont("Helvetica", LEFT_SEC_TEXT_SIZE)
        langs = ", ".join(languages)
        # استخدم نفس مسافة الأسطر في اليسار
        cursor = draw_par(
            c=c, x=inner_x, y=cursor,
            lines=[langs], font="Helvetica", size=LEFT_SEC_TEXT_SIZE,
            max_w=inner_w, align="left", rtl_mode=False,
            leading=LEFT_SEC_LINE_GAP
        )
        cursor -= LEFT_SEC_SECTION_GAP

    # ---------------------------------------------------------------------------
# … بعد قسم اللغات مباشرة
    cursor = draw_left_extra_sections(c, inner_x, inner_w, cursor, sections_left)

    yR = y_top - GAP_AFTER_HEADING 

    # ===== العمود الأيمن =====

    yR = draw_right_extra_sections(c, right_x, right_w, yR, sections_right)

    # عنوان رئيسي
    c.setFont("Helvetica-Bold", HEADING_SIZE)
    c.setFillColor(HEADING_COLOR)
    c.drawString(right_x, yR, "Ausgewählte Projekte")
    yR -= GAP_AFTER_HEADING
    draw_rule(c, right_x, yR, right_w)
    yR -= RIGHT_SEC_RULE_TO_TEXT_GAP

    for title, desc, link in projects:
        # عنوان المشروع
        c.setFont("Helvetica-Bold", PROJECT_TITLE_SIZE)
        c.setFillColor(SUBHEAD_COLOR)
        c.drawString(right_x, yR, title or "")
        yR -= PROJECT_TITLE_GAP_BELOW

        # وصف المشروع — نضبط leading للمسافة بين السطور
        c.setFillColor(colors.black)
        # الوصف
        yR = draw_par(
            c=c, x=right_x, y=yR,
            lines=(desc or "").split("\n"),
            font=(AR_FONT if rtl_mode else "Helvetica"),
            size=TEXT_SIZE, max_w=right_w,
            align=("right" if rtl_mode else "left"),
            rtl_mode=rtl_mode,
            leading=PROJECT_DESC_LEADING,
        )

        # ↙︎ أضف مسافة قبل الرابط
        if link:
            # قلّل/زد هذه لتغيير الفجوة قبل الرابط
            yR -= PROJECT_LINK_GAP_ABOVE  # اجعلها 0 أو حتى سالبة لتقليل الفراغ

            font_name = "Helvetica-Oblique"
            c.setFont(font_name, PROJECT_LINK_TEXT_SIZE)
            c.setFillColor(HEADING_COLOR)

            link_text = f"Repo: {link}"
            c.drawString(right_x, yR, link_text)

            tw  = pdfmetrics.stringWidth(link_text, font_name, PROJECT_LINK_TEXT_SIZE)
            asc = pdfmetrics.getAscent(font_name)  / 1000.0 * PROJECT_LINK_TEXT_SIZE
            dsc = abs(pdfmetrics.getDescent(font_name)) / 1000.0 * PROJECT_LINK_TEXT_SIZE

            # جعل منطقة النقر ملاصقة للنص
            c.linkURL(link, (right_x, yR - dsc, right_x + tw, yR + asc * 0.2), relative=0, thickness=0)

            yR -= PROJECT_BLOCK_GAP
        else:
            yR -= PROJECT_BLOCK_GAP




    # --------- التعليم / التدريب (يمين) ---------
    draw_rule(c, right_x, yR, right_w)
    yR -= RIGHT_SEC_RULE_TO_TEXT_GAP

    c.setFont("Helvetica-Bold", HEADING_SIZE)
    c.setFillColor(HEADING_COLOR)
    c.drawString(right_x, yR, "Berufliche Weiterbildung")
    yR -= GAP_AFTER_HEADING
    draw_rule(c, right_x, yR, right_w)
    yR -= RIGHT_SEC_RULE_TO_TEXT_GAP   # مسافة صغيرة بعد الخط

    if education_items:
        for block in education_items:
            parts = [ln.strip() for ln in str(block).splitlines() if ln.strip()]
            if not parts:
                continue

            # --- العنوان (السطر الأول) ملوّن وغامق ---
            title_lines = wrap_text(parts[0], "Helvetica-Bold", TEXT_SIZE, right_w)
            c.setFont("Helvetica-Bold", TEXT_SIZE)
            c.setFillColor(EDU_TITLE_COLOR)   # لوّن العنوان فقط
            for tl in title_lines:
                c.drawString(right_x, yR, tl)
                yR -= RIGHT_SEC_LINE_GAP

            # ارجِع للأسود قبل بقية الأسطر
            c.setFillColor(colors.black)

            # --- بقية الأسطر نص عادي أسود ---
            rest = parts[1:]
            if rest:
                yR = draw_par(
                    c=c, x=right_x, y=yR,
                    lines=rest,
                    font="Helvetica",
                    size=RIGHT_SEC_TEXT_SIZE,
                    max_w=right_w,
                    align="left",
                    rtl_mode=False,
                    leading=EDU_TEXT_LEADING,
                    para_gap=2,
                )

            # مسافة بين العناصر
            yR -= RIGHT_SEC_SECTION_GAP






    # … بعد رسم education_items


    c.showPage()
    c.save()
    out = buffer.getvalue()
    buffer.close()
    return out
