from __future__ import annotations
from typing import List, Tuple, Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware

from .pdf_utils import build_resume_pdf

app = FastAPI(title="Resume PDF API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ——— أدوات تحويل النصوص القادمة من الواجهة ———
def parse_comma_list(s: str | None) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]

def parse_projects_text(text: str | None) -> List[Tuple[str, str, Optional[str]]]:
    """
    Blocks separated by a blank line:
      line1: title
      line2: description (may continue multi-line)
      line3: optional link
    """
    if not text:
        return []
    blocks = [b.strip() for b in text.strip().split("\n\n") if b.strip()]
    out: List[Tuple[str, str, Optional[str]]] = []
    for b in blocks:
        lines = [l for l in b.splitlines() if l.strip()]
        if not lines:
            continue
        title = lines[0]
        link = lines[-1] if lines and lines[-1].startswith(("http://", "https://")) else None
        desc_lines = lines[1:-1] if link else lines[1:]
        out.append((title, "\n".join(desc_lines), link))
    return out

def parse_sections_text(text: str | None) -> List[Dict[str, Any]]:
    """
    Example:
      [Kontakt]
      - Berlin
      - you@example.com

      [Interessen]
      - KI
      - Open Source
    """
    if not text:
        return []
    out: List[Dict[str, Any]] = []
    cur_title: Optional[str] = None
    cur_lines: List[str] = []
    def flush():
        nonlocal cur_title, cur_lines
        if cur_title and cur_lines:
            out.append({"title": cur_title, "lines": cur_lines[:]})
        cur_title, cur_lines = None, []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush(); continue
        if line.startswith("[") and line.endswith("]"):
            flush(); cur_title = line[1:-1].strip()
        elif line.startswith("-"):
            cur_lines.append(line[1:].strip())
        else:
            # free text fallback
            if cur_title is None:
                cur_title = line
            else:
                cur_lines.append(line)
    flush()
    return out

@app.post("/generate-form")
async def generate_form(
    name: str = Form(""),
    location: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    github: str = Form(""),
    linkedin: str = Form(""),
    birthdate: str = Form(""),
    skills: str = Form(""),
    languages: str = Form(""),
    projects_text: str = Form(""),
    education_text: str = Form(""),
    sections_left_text: str = Form(""),
    sections_right_text: str = Form(""),
    rtl_mode: str = Form("false"),
    photo: UploadFile | None = File(default=None),
):
    # كل الحقول اختيارية
    projects = parse_projects_text(projects_text)
    sections_left = parse_sections_text(sections_left_text)
    sections_right = parse_sections_text(sections_right_text)
    photo_bytes = await photo.read() if photo else None
    pdf = build_resume_pdf(
        name=name, location=location, phone=phone, email=email,
        github=github, linkedin=linkedin, birthdate=birthdate,
        skills=parse_comma_list(skills), languages=parse_comma_list(languages),
        projects=projects, education_items=[l for l in education_text.splitlines() if l.strip()],
        photo_bytes=photo_bytes, rtl_mode=(rtl_mode.lower() == "true"),
        sections_left=sections_left, sections_right=sections_right,
    )
    return Response(pdf, media_type="application/pdf")
