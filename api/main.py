# api/main.py
from __future__ import annotations
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import Optional, List, Dict, Any
from api.pdf_utils import build_resume_pdf

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- أدوات بسيطة لتحويل النصوص ---

def parse_csv_or_lines(txt: str) -> list[str]:
    """تفصل نصًا إلى عناصر إمّا بالفواصل أو كل سطر عنصر"""
    if not txt:
        return []
    parts = []
    for line in txt.replace(",", "\n").splitlines():
        s = line.strip()
        if s:
            parts.append(s)
    return parts

def normalize_language_level(label: str) -> str:
    """تحويل CEFR (A1..C2) إلى صياغة محايدة بالعربية/الألمانية"""
    s = label.strip()
    mapping = {
        "a1": "Grundkenntnisse",
        "a2": "Grundkenntnisse",
        "b1": "Gute Kenntnisse",
        "b2": "Gute Kenntnisse",
        "c1": "Sehr gute Kenntnisse",
        "c2": "Verhandlungssicher",
    }
    import re
    m = re.search(r"(?i)^(.+?)\s*[-–:]\s*([abc][12])\b", s)
    if m:
        lang = m.group(1).strip()
        lvl  = m.group(2).lower()
        return f"{lang} – {mapping.get(lvl, m.group(2))}"
    return s



def parse_sections(text: str):
    """
    شكل النص:
      [Title]
      - line 1
      - line 2

      [Next]
      - another line
    """
    sections, cur = [], {"title": "", "lines": []}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            # اغلاق القسم الحالي إذا كان صالحاً
            if cur["title"] and cur["lines"]:
                sections.append(cur)
            cur = {"title": "", "lines": []}
            continue

        if line.startswith("[") and line.endswith("]"):
            # اغلاق السابق
            if cur["title"] and cur["lines"]:
                sections.append(cur)
            cur = {"title": line.strip("[]").strip(), "lines": []}
        elif line.startswith("-"):
            cur["lines"].append(line[1:].strip())

    if cur["title"] and cur["lines"]:
        sections.append(cur)

    return sections

def parse_simple_list(txt: str) -> List[str]:
    """كل سطر عنصر. تسقط الأسطر الفارغة."""
    out: List[str] = []
    for line in (txt or "").splitlines():
        s = line.strip()
        if s:
            out.append(s)
    return out

def parse_projects_blocks(txt: str) -> List[tuple[str, str, Optional[str]]]:
    """
    بلوك المشروع = [العنوان] ثم أسطر الوصف، وإذا كان في سطر منفصل يبدأ بـ http أو https نعدّه link.
    يفصل بين البلوكات سطر فارغ.
    """
    blocks: List[tuple[str, str, Optional[str]]] = []
    cur_title, cur_desc, cur_link = "", [], None
    def flush():
        nonlocal cur_title, cur_desc, cur_link
        if cur_title or cur_desc or cur_link:
            blocks.append((cur_title.strip(), "\n".join(cur_desc).strip(), cur_link))
        cur_title, cur_desc, cur_link = "", [], None

    for raw in (txt or "").splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if not cur_title:
            cur_title = line
        elif line.startswith("http://") or line.startswith("https://"):
            cur_link = line
        else:
            cur_desc.append(line)
    flush()
    return blocks

def parse_sections_text(txt: str):
    sections = []
    title, lines = None, []

    def flush():
        nonlocal title, lines
        if title and lines:
            sections.append({"title": title, "lines": lines[:]})
        title, lines = None, []

    for raw in (txt or "").splitlines():
        s = raw.strip()
        if not s:
            flush(); continue
        if s.startswith("[") and s.endswith("]"):
            flush()
            title = s[1:-1].strip()
        elif s[:1] in "-•–":  # يدعم -, •, –
            lines.append(s[1:].strip())
        else:
            # استمرار للسطر السابق
            if lines:
                lines[-1] += " " + s
            else:
                title = title or s
    flush()
    return sections


def parse_extra_sections(text: str):
    """
    صيغة الإدخال:
      [Title]
      - line 1
      - line 2

      [Another]
      - item
    """
    secs = []
    cur_title = None
    cur_lines = []
    for raw in (text or "").splitlines():
        ln = raw.strip()
        if not ln:
            continue
        if ln.startswith("[") and ln.endswith("]"):
            if cur_title and cur_lines:
                secs.append({"title": cur_title, "lines": cur_lines})
            cur_title = ln[1:-1].strip()
            cur_lines = []
        elif ln.startswith("-"):
            cur_lines.append(ln.lstrip("-").strip())
        else:
            cur_lines.append(ln)
    if cur_title and cur_lines:
        secs.append({"title": cur_title, "lines": cur_lines})
    return secs

def parse_csv_or_lines(txt: str) -> list[str]:
    if not txt:
        return []
    parts = []
    for line in txt.replace(",", "\n").splitlines():
        s = line.strip()
        if s:
            parts.append(s)
    return parts

def parse_education_blocks(txt: str) -> list[str]:
    """قسّم إلى بلوكات؛ يفصل بينها سطر فارغ. يُحافظ على الأسطر داخل كل بلوك."""
    blocks, cur = [], []
    for raw in (txt or "").splitlines():
        ln = raw.rstrip()
        if not ln.strip():
            if cur:
                blocks.append("\n".join(cur))
                cur = []
        else:
            cur.append(ln)
    if cur:
        blocks.append("\n".join(cur))
    return blocks




# --- الـ endpoint ---

@app.post("/generate-form")
async def generate_form(
    # معلومات أساسية
    name: str = Form(""),
    location: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    github: str = Form(""),
    linkedin: str = Form(""),
    birthdate: str = Form(""),

    # نصوص حرّة من الواجهة
    projects_text: str = Form(""),
    education_text: str = Form(""),
    sections_left_text: str = Form(""),
    sections_right_text: str = Form(""),

    # جديد: مهارات ولغات (فاصلة أو كل عنصر بسطر)
    skills_text: str = Form(""),
    languages_text: str = Form(""),

    # خيارات
    rtl_mode: str = Form("false"),

    # صورة شخصية (اختياري)
    photo: Optional[UploadFile] = File(None),
):
    # حمّل الصورة (إن وجدت)
    photo_bytes: Optional[bytes] = await photo.read() if photo is not None else None

    # حوّل النصوص إلى هياكل
    skills         = parse_csv_or_lines(skills_text)               # ["Python", "FastAPI", ...]
    languages_raw  = parse_csv_or_lines(languages_text)
    languages      = [normalize_language_level(x) for x in languages_raw]

    projects       = parse_projects_blocks(projects_text)          # [(title, desc, link?), ...]
    education_items = parse_education_blocks(education_text)
    sections_left  = parse_sections_text(sections_left_text)       # [{"title":..,"lines":[..]}, ...]
    sections_right = parse_sections_text(sections_right_text)      # [{"title":..,"lines":[..]}, ...]

    # توليد الـ PDF
    pdf = build_resume_pdf(
        name=name,
        location=location,
        phone=phone,
        email=email,
        github=github,
        linkedin=linkedin,
        birthdate=birthdate,
        skills=skills,
        languages=languages,
        projects=projects,
        education_items=education_items,
        photo_bytes=photo_bytes,
        rtl_mode=(rtl_mode.strip().lower() == "true"),
        sections_left=sections_left,
        sections_right=sections_right,
    )

    return Response(content=pdf, media_type="application/pdf")
