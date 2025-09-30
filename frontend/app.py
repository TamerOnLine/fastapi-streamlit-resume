# frontend/app.py
from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import requests
import streamlit as st

# ─────────────────────────────
# إعداد عام
# ─────────────────────────────
st.set_page_config(page_title="Resume PDF Builder", page_icon="🧾", layout="centered")
st.title("🧾 Resume PDF Builder (FastAPI + Streamlit)")
st.caption("كل الحقول اختيارية. ارفع JSON (Browse files) → Load uploaded لتعبئة الحقول، أو عدِّل واحفظ بـ Save.")

# ─────────────────────────────
# مسارات
# ─────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[1]
PROFILES_DIR = BASE_DIR / "profiles"
OUTPUTS_DIR = BASE_DIR / "outputs"
PROFILES_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# ─────────────────────────────
# حالة الجلسة للـ PDF
# ─────────────────────────────
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "pdf_filename" not in st.session_state:
    st.session_state.pdf_filename = "resume.pdf"

# ─────────────────────────────
# مفاتيح الحقول (ثابتة)
# ─────────────────────────────
K = {
    "name": "f_name",
    "location": "f_location",
    "phone": "f_phone",
    "email": "f_email",
    "birthdate": "f_birthdate",
    "github": "f_github",
    "linkedin": "f_linkedin",
    "skills": "f_skills",
    "languages": "f_languages",
    "projects_text": "f_projects_text",
    "education_text": "f_education_text",
    "sections_left_text": "f_sections_left_text",
    "sections_right_text": "f_sections_right_text",
    "rtl_mode": "f_rtl_mode",
    "api_base": "f_api_base",
}

# ─────────────────────────────
# دوال حفظ/تحميل صغيرة
# ─────────────────────────────
def persist_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def payload_from_form() -> Dict[str, Any]:
    return {
        "name": st.session_state.get(K["name"], ""),
        "location": st.session_state.get(K["location"], ""),
        "phone": st.session_state.get(K["phone"], ""),
        "email": st.session_state.get(K["email"], ""),
        "github": st.session_state.get(K["github"], ""),
        "linkedin": st.session_state.get(K["linkedin"], ""),
        "birthdate": st.session_state.get(K["birthdate"], ""),
        "skills": [s.strip() for s in st.session_state.get(K["skills"], "").split(",") if s.strip()],
        "languages": [s.strip() for s in st.session_state.get(K["languages"], "").split(",") if s.strip()],
        "projects_text": st.session_state.get(K["projects_text"], ""),
        "education_text": st.session_state.get(K["education_text"], ""),
        "sections_left_text": st.session_state.get(K["sections_left_text"], ""),
        "sections_right_text": st.session_state.get(K["sections_right_text"], ""),
        "rtl_mode": bool(st.session_state.get(K["rtl_mode"], False)),
    }

def apply_payload_to_form(p: Dict[str, Any]) -> None:
    st.session_state[K["name"]] = p.get("name", "")
    st.session_state[K["location"]] = p.get("location", "")
    st.session_state[K["phone"]] = p.get("phone", "")
    st.session_state[K["email"]] = p.get("email", "")
    st.session_state[K["birthdate"]] = p.get("birthdate", "")
    st.session_state[K["github"]] = p.get("github", "")
    st.session_state[K["linkedin"]] = p.get("linkedin", "")
    st.session_state[K["skills"]] = (
        ", ".join(p.get("skills", [])) if isinstance(p.get("skills"), list) else (p.get("skills", "") or "")
    )
    st.session_state[K["languages"]] = (
        ", ".join(p.get("languages", [])) if isinstance(p.get("languages"), list) else (p.get("languages", "") or "")
    )
    st.session_state[K["projects_text"]] = p.get("projects_text", "")
    st.session_state[K["education_text"]] = p.get("education_text", "")
    st.session_state[K["sections_left_text"]] = p.get("sections_left_text", "")
    st.session_state[K["sections_right_text"]] = p.get("sections_right_text", "")
    st.session_state[K["rtl_mode"]] = bool(p.get("rtl_mode", False))

# ─────────────────────────────
# الشريط الجانبي (Save / Load)
# ─────────────────────────────
st.sidebar.header("💾 Save / Load (Minimal)")
preset_name = st.sidebar.text_input("Preset name", value="", placeholder="my-profile")
uploaded = st.sidebar.file_uploader(" ", type=["json"], label_visibility="collapsed")
col_load, col_save = st.sidebar.columns([1, 1])

if col_load.button("Load uploaded", use_container_width=True):
    if uploaded is None:
        st.sidebar.error("ارفع ملف JSON أولاً.")
    else:
        try:
            payload = json.loads(uploaded.getvalue().decode("utf-8"))
            apply_payload_to_form(payload)
            st.sidebar.success("Loaded from uploaded JSON.")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Invalid JSON: {e}")

if col_save.button("Save", use_container_width=True):
    if not preset_name.strip():
        st.sidebar.error("اكتب اسمًا للحفظ.")
    else:
        try:
            data = payload_from_form()
            path = PROFILES_DIR / f"{preset_name.strip()}.json"
            persist_json_atomic(path, data)
            st.sidebar.success(f"Saved → {path.name}")
        except Exception as e:
            st.sidebar.error(f"Save failed: {e}")

# ─────────────────────────────
# الحقول (كلها اختيارية)
# ─────────────────────────────
colA, colB = st.columns(2)
with colA:
    st.text_input("Name", key=K["name"])
    st.text_input("Location", key=K["location"])
    st.text_input("Phone", key=K["phone"])
    st.text_input("Email", key=K["email"])
    st.text_input("Birthdate", key=K["birthdate"])
with colB:
    st.text_input("GitHub", key=K["github"])
    st.text_input("LinkedIn", key=K["linkedin"])
    st.text_input("Skills (comma separated)", key=K["skills"])
    st.text_input("Languages (comma separated)", key=K["languages"])
    st.checkbox("Enable RTL/Arabic rendering", value=False, key=K["rtl_mode"])

st.subheader("Projects")
st.caption("Block = title, description, (optional) link on its own line. Separate blocks by a blank line.")
st.text_area("Projects blocks", height=160, key=K["projects_text"])

st.subheader("Education / Training")
st.caption("One item per line.")
st.text_area("Education items", key=K["education_text"])

st.subheader("Extra Sections (Left / Right)")
st.caption("Use: [Title] then lines starting with - . Separate sections by a blank line.")
st.text_area("Sections (Left)", height=120, key=K["sections_left_text"])
st.text_area("Sections (Right)", height=120, key=K["sections_right_text"])

# صورة + عنوان الـ API
photo = st.file_uploader("Profile Photo (optional)", type=["png", "jpg", "jpeg"])
api_base = st.text_input("API Base URL", "http://127.0.0.1:8000", key=K["api_base"])

# ─────────────────────────────
# أزرار الإجراءات في الشريط الجانبي
# ─────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Actions")

generate = st.sidebar.button("Generate PDF", type="primary", use_container_width=True)

if generate:
    # جهّز البيانات
    data = {
        "name": st.session_state.get(K["name"], ""),
        "location": st.session_state.get(K["location"], ""),
        "phone": st.session_state.get(K["phone"], ""),
        "email": st.session_state.get(K["email"], ""),
        "github": st.session_state.get(K["github"], ""),
        "linkedin": st.session_state.get(K["linkedin"], ""),
        "birthdate": st.session_state.get(K["birthdate"], ""),

        # ⬇️ غيّر المفتاحين هنا
        "skills_text": st.session_state.get(K["skills"], ""),
        "languages_text": st.session_state.get(K["languages"], ""),

        "projects_text": st.session_state.get(K["projects_text"], ""),
        "education_text": st.session_state.get(K["education_text"], ""),
        "sections_left_text": st.session_state.get(K["sections_left_text"], ""),
        "sections_right_text": st.session_state.get(K["sections_right_text"], ""),
        "rtl_mode": str(bool(st.session_state.get(K["rtl_mode"], False))).lower(),
    }

    files = {"photo": (photo.name, photo.getvalue())} if photo is not None else None

    try:
        url = f"{st.session_state.get(K['api_base'],'http://127.0.0.1:8000').rstrip('/')}/generate-form"
        resp = requests.post(url, data=data, files=files, timeout=60)
        resp.raise_for_status()
        pdf_bytes = resp.content

        # خزّن في الجلسة لزر التحميل والمعاينة
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.pdf_filename = "resume.pdf"

        # خزّن نسخة بالقرص
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = OUTPUTS_DIR / f"resume_{ts}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        st.sidebar.success(f"تم توليد PDF: {pdf_path.name}")
    except requests.RequestException as e:
        st.sidebar.error(f"Request failed: {e}")
    except Exception as e:
        st.sidebar.error(f"Unexpected error: {e}")

# زر التحميل في الشريط الجانبي
if st.session_state.pdf_bytes:
    st.sidebar.download_button(
        "Download resume.pdf",
        data=st.session_state.pdf_bytes,
        file_name=st.session_state.pdf_filename,
        mime="application/pdf",
        use_container_width=True,
    )

# ─────────────────────────────
# معاينة PDF داخل الصفحة (إن وُجد)
# ─────────────────────────────
if st.session_state.pdf_bytes:
    b64 = base64.b64encode(st.session_state.pdf_bytes).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="700px" '
        f'style="border:1px solid #333;border-radius:8px;"></iframe>',
        unsafe_allow_html=True,
    )
