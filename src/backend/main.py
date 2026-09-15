import asyncio
import io
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

import fitz
import pytesseract
from PIL import Image
from docx import Document
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None



import base64
import time
import tempfile
import zipfile
import subprocess
import html as html_lib
from PIL import Image, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    Image as ReportLabImage,
    KeepTogether,
    Table,
    TableStyle,
)
from reportlab.lib.utils import ImageReader

load_dotenv()

from auth import get_current_user, get_db

app = FastAPI(title="ResumeAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



# =========================================================
# PERSISTENT RESUME HISTORY
# =========================================================
def init_resume_history_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS resume_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        score INTEGER NOT NULL,
        analysis_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        resume_text TEXT DEFAULT '',
        job_id TEXT DEFAULT ''
    )""")
    cols = {r[1] for r in conn.execute('PRAGMA table_info(resume_analyses)').fetchall()}
    if 'resume_text' not in cols:
        conn.execute("ALTER TABLE resume_analyses ADD COLUMN resume_text TEXT DEFAULT ''")
    if 'job_id' not in cols:
        conn.execute("ALTER TABLE resume_analyses ADD COLUMN job_id TEXT DEFAULT ''")
    conn.commit()
    conn.close()

init_resume_history_db()

# =========================================================
# GEMINI
# =========================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

gemini_client = None

if GEMINI_API_KEY and genai is not None:
    gemini_client = genai.Client(
        api_key=GEMINI_API_KEY
    )


# =========================================================
# JOB STORAGE
# =========================================================

ai_jobs: dict[str, dict[str, Any]] = {}
chat_jobs: dict[str, dict[str, Any]] = {}


# =========================================================
# MODELS
# =========================================================

class ChatRequest(BaseModel):
    job_id: str
    message: str = Field(min_length=1, max_length=4000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    page_context: str = Field(default='resume', max_length=80)


class FeedbackSchema(BaseModel):
    overall_advice: str
    high_priority_issues: list[str]
    medium_priority_issues: list[str]
    strengths: list[str]
    actionable_suggestions: list[str]


# =========================================================
# TEXT EXTRACTION
# =========================================================

def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text,
    )
    return text.strip()


def extract_from_pdf(data: bytes) -> str:
    """Fast, high-recall PDF extraction.

    Native PDF text is always preferred. OCR is used only for sparse/scanned
    PDFs and is capped to the first two pages to avoid making normal analysis
    unnecessarily slow.
    """
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        native_pages = []
        for page in doc:
            try:
                value = page.get_text("text").strip()
                if value:
                    native_pages.append(value)
            except Exception as exc:
                print("PDF native text error:", repr(exc))
        native = clean_text("\n\n".join(native_pages))
        if len(native) >= 900:
            return native

        ocr_pages = []
        for index, page in enumerate(doc):
            if index >= min(len(doc), 4):
                break
            try:
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                gray = ImageOps.autocontrast(ImageOps.grayscale(image))
                value = pytesseract.image_to_string(gray, config="--psm 6")
                if not value.strip():
                    value = pytesseract.image_to_string(gray, config="--psm 11")
                if value.strip():
                    ocr_pages.append(value)
            except Exception as exc:
                print("PDF OCR page error:", repr(exc))
        ocr = clean_text("\n\n".join(ocr_pages))
        return clean_text(native + ("\n\n" + ocr if ocr else ""))
    finally:
        doc.close()


def extract_from_docx(data: bytes) -> str:

    document = Document(
        io.BytesIO(data)
    )

    parts = []

    for paragraph in document.paragraphs:

        if paragraph.text.strip():
            parts.append(
                paragraph.text
            )

    for table in document.tables:

        for row in table.rows:

            cells = [
                cell.text.strip()
                for cell in row.cells
                if cell.text.strip()
            ]

            if cells:
                parts.append(
                    " | ".join(cells)
                )

    return clean_text(
        "\n".join(parts)
    )



def extract_from_rtf(data: bytes) -> str:
    try:
        from striprtf.striprtf import rtf_to_text
        return clean_text(rtf_to_text(data.decode("utf-8", errors="ignore")))
    except Exception:
        raw = data.decode("utf-8", errors="ignore")
        raw = re.sub(r"\\'[0-9a-fA-F]{2}", " ", raw)
        raw = re.sub(r"\\[a-zA-Z]+-?\\d* ?", " ", raw)
        raw = re.sub(r"[{}]", " ", raw)
        return clean_text(raw)


def extract_from_odt(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml = archive.read("content.xml").decode("utf-8", errors="ignore")
        xml = re.sub(r"</text:p>|</text:h>|</table:table-cell>|</text:list-item>", "\n", xml)
        xml = re.sub(r"<[^>]+>", " ", xml)
        return clean_text(html_lib.unescape(xml))
    except Exception as exc:
        raise ValueError("The ODT file could not be read. Please export it as PDF or DOCX and try again.") from exc


def extract_from_doc(data: bytes) -> str:
    # .doc is a legacy binary format. Prefer LibreOffice/antiword when present.
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "resume.doc")
        with open(src, "wb") as fh:
            fh.write(data)
        for command in (["antiword", src], ["catdoc", src]):
            try:
                proc = subprocess.run(command, capture_output=True, text=True, timeout=12)
                if proc.returncode == 0 and proc.stdout.strip():
                    return clean_text(proc.stdout)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        outdir = os.path.join(td, "out")
        os.makedirs(outdir, exist_ok=True)
        try:
            proc = subprocess.run(
                ["libreoffice", "--headless", "--convert-to", "txt:Text", "--outdir", outdir, src],
                capture_output=True, text=True, timeout=20,
            )
            txt = os.path.join(outdir, "resume.txt")
            if proc.returncode == 0 and os.path.exists(txt):
                return clean_text(Path(txt).read_text(errors="ignore"))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    raise ValueError("Legacy DOC files need a document converter on the server. Please save the resume as PDF or DOCX and upload it again.")


def extract_from_image(data: bytes) -> str:
    """High-recall OCR for JPG/PNG resumes without excessive duplicate passes."""
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image).convert("RGB")
    max_dim = max(image.size)
    scale = 2 if max_dim < 2800 else 1
    if scale > 1:
        image = image.resize((image.width * scale, image.height * scale))

    gray = ImageOps.autocontrast(ImageOps.grayscale(image))
    texts = []
    for config in ("--psm 6", "--psm 11"):
        try:
            value = pytesseract.image_to_string(gray, config=config)
            if value.strip():
                texts.append(value)
        except Exception as exc:
            print("Image OCR error:", repr(exc))

    merged = clean_text("\n".join(texts))
    email_found = bool(re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", merged, re.I))
    phone_found = has_phone_number(merged)
    if not (email_found and phone_found):
        # Contact details are often placed in a compact header/sidebar.
        try:
            top = gray.crop((0, 0, gray.width, max(1, int(gray.height * 0.42))))
            value = pytesseract.image_to_string(top, config="--psm 11")
            if value.strip():
                texts.append(value)
        except Exception as exc:
            print("Contact OCR error:", repr(exc))

    seen = set(); lines = []
    for block in texts:
        for line in block.splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            key = line.lower()
            if line and key not in seen:
                seen.add(key); lines.append(line)
    return clean_text("\n".join(lines))


async def extract_resume_text(
    filename: str,
    data: bytes,
) -> str:

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension == ".pdf":

        return await asyncio.to_thread(
            extract_from_pdf,
            data,
        )

    if extension == ".docx":

        return await asyncio.to_thread(
            extract_from_docx,
            data,
        )

    if extension == ".doc":
        return await asyncio.to_thread(extract_from_doc, data)

    if extension == ".rtf":
        return await asyncio.to_thread(extract_from_rtf, data)

    if extension == ".odt":
        return await asyncio.to_thread(extract_from_odt, data)

    if extension in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }:

        return await asyncio.to_thread(
            extract_from_image,
            data,
        )

    if extension == '.txt':
        return clean_text(data.decode('utf-8', errors='ignore'))

    raise ValueError(
        "Unsupported file format. ResumeAI supports PDF, DOC, DOCX, RTF, ODT, TXT, JPG, JPEG, PNG and WEBP."
    )


# =========================================================
# CONTACT EXTRACTION HELPERS
# =========================================================

def normalize_contact_text(text: str) -> str:
    value = (text or '').replace('\u00a0', ' ')
    # Normalize common OCR punctuation without destroying number separators.
    value = value.replace('−', '-').replace('–', '-').replace('—', '-')
    return value


def has_phone_number(text: str) -> bool:
    value = normalize_contact_text(text)
    patterns = [
        r'(?<!\d)(?:\+?91[\s().-]*)?[6-9](?:[\s().-]*\d){9}(?!\d)',
        r'(?<!\d)[6-9]\d{4}[\s.-]\d{5}(?!\d)',
        r'(?i)(?:phone|mobile|mob|contact|contact\s*no|contact\s*number|tel)\s*[:#-]?\s*(?:\+?91[\s.-]*)?[6-9][0-9OIl\s().-]{8,18}',
    ]
    if any(re.search(pattern, value) for pattern in patterns):
        return True

    # OCR can turn digits into O/I/l and can insert spaces in a phone number.
    # Only accept a loose 10-digit candidate when it appears on a contact-like
    # line, which avoids treating dates/IDs elsewhere in a resume as phones.
    for line in value.splitlines():
        if re.search(r'(?i)\b(phone|mobile|mob|contact|contact\s*no|contact\s*number|tel)\b', line):
            candidate = re.sub(r'(?i)[OIl]', lambda m: {'O':'0','I':'1','l':'1'}[m.group(0)], line)
            digits = re.sub(r'\D', '', candidate)
            if len(digits) >= 10:
                tail = digits[-10:]
                if tail[0] in '6789':
                    return True
    return False


def looks_like_resume(text: str, filename: str = "") -> bool:
    """Conservative resume classifier designed to reduce false negatives.

    It accepts normal student/fresher/professional resumes even when a PDF has
    weak extraction, while explicitly rejecting common non-resume documents.
    """
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    if len(cleaned) < 35:
        return False

    lower = cleaned.lower()
    filename_lower = (filename or "").lower()

    obvious_non_resume = [
        "marksheet", "mark sheet", "statement of marks", "transcript",
        "transcript of records", "grade card", "report card", "fee receipt",
        "fee structure", "invoice", "tax invoice", "bill", "admit card",
        "hall ticket", "bank statement", "medical report", "purchase order",
        "challan", "time table", "timetable", "attendance sheet", "fee payment receipt",
    ]
    if any(term in filename_lower for term in obvious_non_resume):
        return False
    if any(term in lower for term in obvious_non_resume):
        return False

    email = bool(re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", cleaned, re.I))
    phone = has_phone_number(cleaned)
    linkedin = "linkedin.com" in lower or "linkedin " in lower
    github = "github.com" in lower or "github " in lower

    section_patterns = {
        "education": r"\b(education|academic background|qualifications?|b\.?tech|bachelor|master|university|college)\b",
        "skills": r"\b(skills?|technical skills?|technologies|tech stack|core competencies)\b",
        "experience": r"\b(experience|work experience|professional experience|employment|work history)\b",
        "projects": r"\b(projects?|personal projects?|academic projects?)\b",
        "internship": r"\b(internships?|intern experience)\b",
        "certifications": r"\b(certifications?|certificates?|courses?)\b",
        "achievements": r"\b(achievements?|awards?|honors?)\b",
        "summary": r"\b(summary|professional summary|profile|objective|career objective|about me)\b",
        "contact": r"\b(contact|email|phone|mobile)\b",
    }
    hits = {name for name, pattern in section_patterns.items() if re.search(pattern, lower)}
    section_hits = len(hits)

    skills = detect_skills(cleaned)
    action_verbs = detect_action_verbs(cleaned)

    professional_terms = [
        "developer", "engineer", "analyst", "designer", "consultant", "intern",
        "student", "software", "technology", "programming", "python", "java",
        "javascript", "react", "sql", "api", "database", "management", "research",
    ]
    professional_hits = sum(1 for term in professional_terms if re.search(rf"\b{re.escape(term)}\b", lower))

    explicit_resume_name = any(term in filename_lower for term in ("resume", "cv", "curriculum", "biodata", "bio-data"))
    explicit_resume_wording = bool(re.search(r"\b(resume|curriculum vitae|curriculum-vitae|cv)\b", lower))

    # A structured resume is accepted even if contact extraction is imperfect.
    if section_hits >= 3 and len(cleaned) >= 120:
        return True

    if section_hits >= 4:
        return True

    # Typical student/fresher resume: identity/contact + education/skills/projects.
    if section_hits >= 3 and (email or phone or linkedin or github or len(skills) >= 2):
        return True

    # Typical professional resume with 2 clear sections and professional evidence.
    if section_hits >= 2 and (email or phone or linkedin or github) and (len(skills) >= 1 or action_verbs or professional_hits >= 2):
        return True

    # Some exported/scanned resumes have almost no heading extraction. Strong
    # contact + career evidence is enough, provided the document is not a known
    # non-resume document.
    if (email or phone) and (len(skills) >= 2 or action_verbs or professional_hits >= 3) and len(cleaned) >= 70:
        return True

    # Filename is supporting evidence, not the only reason to accept arbitrary text.
    if explicit_resume_name and len(cleaned) >= 35:
        return True

    if explicit_resume_wording and (section_hits >= 1 or email or phone or len(skills) >= 1):
        return True

    return False


# =========================================================
# SECTION DETECTION
# =========================================================

SECTION_PATTERNS = {
    "contact": [
        "contact",
        "email",
        "phone",
        "mobile",
        "linkedin",
        "github",
    ],
    "summary": [
        "summary",
        "professional summary",
        "profile",
        "objective",
        "about me",
    ],
    "education": [
        "education",
        "academic",
        "b.tech",
        "btech",
        "bachelor",
        "degree",
        "university",
        "college",
    ],
    "skills": [
        "skills",
        "technical skills",
        "core skills",
        "technologies",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment",
    ],
    "internship": [
        "internship",
        "internships",
        "intern",
    ],
    "projects": [
        "projects",
        "project",
        "academic projects",
    ],
    "certifications": [
        "certifications",
        "certification",
        "certificates",
    ],
    "achievements": [
        "achievements",
        "achievement",
        "awards",
        "honors",
    ],
}


SKILLS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "c",
    "c++",
    "c#",
    "html",
    "css",
    "react",
    "react.js",
    "node.js",
    "express",
    "fastapi",
    "flask",
    "django",
    "sql",
    "mysql",
    "postgresql",
    "mongodb",
    "git",
    "github",
    "docker",
    "aws",
    "azure",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "data analysis",
    "pandas",
    "numpy",
    "matplotlib",
    "tensorflow",
    "pytorch",
    "power bi",
    "excel",
    "figma",
    "rest api",
    "api",
]


ACTION_VERBS = [
    "developed",
    "built",
    "created",
    "designed",
    "implemented",
    "optimized",
    "improved",
    "automated",
    "managed",
    "led",
    "analyzed",
    "deployed",
    "engineered",
    "integrated",
    "tested",
    "delivered",
    "configured",
    "maintained",
    "develop",
    "build",
    "create",
    "design",
    "implement",
    "optimize",
    "improve",
    "automate",
    "manage",
    "lead",
    "analyze",
    "deploy",
    "solve",
    "solved",
    "launched",
    "migrated",
    "refactored",
]


GENERIC_PHRASES = [
    "hardworking",
    "hard working",
    "quick learner",
    "team player",
    "passionate individual",
    "self motivated",
    "self-motivated",
    "good communication skills",
    "excellent communication skills",
    "seeking a challenging position",
    "looking for a challenging opportunity",
    "to work in a reputed organization",
    "where i can utilize my skills",
    "where i can grow",
    "highly motivated",
    "dedicated individual",
    "responsible individual",
]


WEAK_BULLET_PHRASES = [
    "responsible for",
    "worked on",
    "helped with",
    "helped in",
    "involved in",
    "did",
    "made",
    "was responsible",
]


def detect_sections(
    text: str,
) -> list[str]:

    lower = text.lower()

    detected = []

    for section, keywords in SECTION_PATTERNS.items():

        if any(
            re.search(
                rf"\b{re.escape(keyword)}\b",
                lower,
            )
            for keyword in keywords
        ):
            detected.append(section)

    return detected


def detect_skills(
    text: str,
) -> list[str]:

    lower = text.lower()

    found = []

    for skill in SKILLS:

        pattern = re.escape(
            skill.lower()
        )

        if re.search(
            rf"(?<![a-z0-9]){pattern}(?![a-z0-9])",
            lower,
        ):
            found.append(skill)

    return list(
        dict.fromkeys(found)
    )


def detect_metrics(
    text: str,
) -> list[str]:

    patterns = [
        r"\b\d+(?:\.\d+)?%",
        r"\b\d+\+",
        r"\b\d+\s+(?:users|clients|customers|students|members|projects|employees|records|requests)\b",
        r"\b\d+\s+(?:days|months|years|weeks)\b",
        r"\b\d+(?:\.\d+)?\s*(?:k|m|million|billion)\b",
        r"\b(?:increased|decreased|reduced|improved|saved|grew|cut)\b.{0,50}?\b\d+(?:\.\d+)?%?",
    ]

    results = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.I,
        )

        results.extend(matches)

    return list(
        dict.fromkeys(results)
    )[:30]


def detect_action_verbs(
    text: str,
) -> list[str]:

    lower = text.lower()

    found = []

    for verb in ACTION_VERBS:

        if re.search(
            rf"\b{re.escape(verb)}\b",
            lower,
        ):
            found.append(verb)

    return list(
        dict.fromkeys(found)
    )


def detect_generic_phrases(
    text: str,
) -> list[str]:

    lower = text.lower()

    found = []

    for phrase in GENERIC_PHRASES:

        if phrase in lower:
            found.append(phrase)

    return found


def detect_weak_bullets(
    text: str,
) -> list[str]:

    lower = text.lower()

    found = []

    for phrase in WEAK_BULLET_PHRASES:

        if phrase in lower:
            found.append(phrase)

    return found


def extract_bullets(
    text: str,
) -> list[str]:

    bullets = []

    for line in text.splitlines():

        cleaned = line.strip()

        if not cleaned:
            continue

        if re.match(
            r"^[•●▪◦‣*-]\s+",
            cleaned,
        ):
            bullets.append(cleaned)

        elif re.match(
            r"^\d+[.)]\s+",
            cleaned,
        ):
            bullets.append(cleaned)

    return bullets


def count_meaningful_lines(
    text: str,
) -> int:

    return len(
        [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]
    )


def count_email_addresses(
    text: str,
) -> int:

    return len(
        re.findall(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            text,
            re.I,
        )
    )


# =========================================================
# QUALITY ANALYSIS
# =========================================================

def analyze_summary_quality(
    text: str,
    sections: list[str],
) -> tuple[int, list[str], list[str]]:

    if "summary" not in sections:

        return (
            0,
            [],
            [
                "Add a focused professional summary for the target role."
            ],
        )

    summary_match = re.search(
        r"(?:professional summary|summary|profile|objective|about me)"
        r"(.*?)(?=\n\s*(?:education|skills|technical skills|experience|work experience|projects|internship|certifications|achievements)\b|$)",
        text,
        re.I | re.S,
    )

    summary = (
        summary_match.group(1).strip()
        if summary_match
        else ""
    )

    words = re.findall(
        r"\b\w+\b",
        summary,
    )

    score = 0
    strengths = []
    suggestions = []

    if len(words) >= 25:
        score += 3

    elif len(words) >= 12:
        score += 2

    else:
        suggestions.append(
            "Expand the summary with a concise description of your role, technical focus and career direction."
        )

    role_terms = [
        "developer",
        "engineer",
        "designer",
        "analyst",
        "student",
        "intern",
        "manager",
        "specialist",
        "scientist",
        "consultant",
    ]

    if any(
        term in summary.lower()
        for term in role_terms
    ):
        score += 2

    summary_skills = detect_skills(
        summary
    )

    if summary_skills:
        score += 2

    if any(
        phrase in summary.lower()
        for phrase in GENERIC_PHRASES
    ):
        score -= 2

        suggestions.append(
            "Replace generic self-descriptions with specific evidence, skills and career focus."
        )

    if re.search(
        r"\b(experience|experienced|built|developed|implemented|created)\b",
        summary,
        re.I,
    ):
        score += 2

    if re.search(
        r"\b(?:python|java|javascript|react|sql|fastapi|machine learning|data analysis|aws|docker)\b",
        summary,
        re.I,
    ):
        score += 1

    score = max(
        0,
        min(score, 10),
    )

    if score >= 8:

        strengths.append(
            "The professional summary is specific and relevant."
        )

    elif score >= 5:

        suggestions.append(
            "Make the summary more specific to the target role and technical strengths."
        )

    else:

        suggestions.append(
            "The summary is too weak or generic to communicate a clear professional value proposition."
        )

    return (
        score,
        strengths,
        suggestions,
    )


def analyze_contact_quality(
    text: str,
) -> tuple[int, list[str], list[str]]:

    lower = text.lower()

    email_found = count_email_addresses(
        text
    ) > 0

    phone_found = has_phone_number(text)

    linkedin_found = (
        "linkedin.com" in lower
    )

    github_found = (
        "github.com" in lower
    )

    score = 0
    strengths = []
    suggestions = []

    if email_found:

        score += 4

        strengths.append(
            "A professional email address is present."
        )

    else:

        suggestions.append(
            "Add a professional email address."
        )

    if phone_found:

        score += 3

        strengths.append(
            "A reachable phone number is present."
        )

    else:

        suggestions.append(
            "Add a reachable phone number."
        )

    if linkedin_found:

        score += 2

        strengths.append(
            "A LinkedIn profile is included."
        )

    else:

        suggestions.append(
            "Add a LinkedIn profile URL if available."
        )

    if github_found:

        score += 1

        strengths.append(
            "A GitHub profile is included."
        )

    return (
        score,
        strengths,
        suggestions,
    )


def analyze_skills_quality(
    text: str,
    skills: list[str],
) -> tuple[int, list[str], list[str]]:

    sections = detect_sections(text)

    if "skills" not in sections:

        return (
            0,
            [],
            [
                "Add a dedicated Skills section containing relevant skills."
            ],
        )

    score = 3
    strengths = []
    suggestions = []

    if len(skills) >= 8:
        score += 4

    elif len(skills) >= 5:
        score += 3

    elif len(skills) >= 3:
        score += 2

    elif len(skills) >= 1:
        score += 1

    else:

        suggestions.append(
            "The Skills section does not contain enough recognizable technical skills."
        )

    evidence_skills = 0

    lower = text.lower()

    for skill in skills:

        occurrences = len(
            re.findall(
                rf"(?<![a-z0-9]){re.escape(skill.lower())}(?![a-z0-9])",
                lower,
            )
        )

        if occurrences >= 2:
            evidence_skills += 1

    if evidence_skills >= 4:

        score += 2

        strengths.append(
            "Several listed skills are supported by other resume content."
        )

    elif skills and evidence_skills == 0:

        suggestions.append(
            "Provide evidence for listed skills through projects, experience or achievements instead of relying only on a keyword list."
        )

    if len(skills) >= 5:

        strengths.append(
            f"{len(skills)} technical skills were detected."
        )

    return (
        max(0, min(score, 10)),
        strengths,
        suggestions,
    )


def analyze_project_quality(
    text: str,
    skills: list[str],
    metrics: list[str],
    action_verbs: list[str],
) -> tuple[int, list[str], list[str]]:

    sections = detect_sections(text)

    if "projects" not in sections:

        return (
            0,
            [],
            [
                "Add relevant projects with technologies, responsibilities and outcomes."
            ],
        )

    lower = text.lower()

    score = 4
    strengths = []
    suggestions = []

    project_keywords = [
        "developed",
        "built",
        "created",
        "implemented",
        "designed",
        "application",
        "website",
        "system",
        "platform",
        "api",
        "model",
        "dashboard",
    ]

    project_evidence = sum(
        1
        for word in project_keywords
        if word in lower
    )

    if project_evidence >= 5:
        score += 3

    elif project_evidence >= 3:
        score += 2

    elif project_evidence >= 1:
        score += 1

    if len(skills) >= 3:
        score += 1

    if action_verbs:
        score += 1

    if metrics:
        score += 1

    if score >= 8:

        strengths.append(
            "Projects contain meaningful technical implementation evidence."
        )

    if not action_verbs:

        suggestions.append(
            "Use strong action verbs to explain what you personally built or implemented."
        )

    if not metrics:

        suggestions.append(
            "Where truthful, add measurable project outcomes such as performance, users, scale, time saved or accuracy."
        )

    if len(skills) < 3:

        suggestions.append(
            "Mention the technologies actually used in each project."
        )

    return (
        max(0, min(score, 15)),
        strengths,
        suggestions,
    )


def analyze_experience_quality(
    text: str,
    action_verbs: list[str],
    metrics: list[str],
) -> tuple[int, list[str], list[str]]:

    sections = detect_sections(text)

    has_experience = (
        "experience" in sections
        or "internship" in sections
    )

    if not has_experience:

        return (
            0,
            [],
            [],
        )

    score = 5
    strengths = []
    suggestions = []

    bullets = extract_bullets(text)

    if len(bullets) >= 5:
        score += 3

    elif len(bullets) >= 3:
        score += 2

    elif len(bullets) >= 1:
        score += 1

    else:

        suggestions.append(
            "Describe experience using concise achievement-oriented bullet points."
        )

    if action_verbs:
        score += 2

    if metrics:
        score += 3

    weak_bullets = detect_weak_bullets(text)

    if weak_bullets:

        score -= 2

        suggestions.append(
            "Replace passive phrases such as 'worked on' or 'responsible for' with specific actions and outcomes."
        )

    if metrics:

        strengths.append(
            "Experience includes measurable evidence."
        )

    if action_verbs:

        strengths.append(
            "Action-oriented language is used in the resume."
        )

    return (
        max(0, min(score, 15)),
        strengths,
        suggestions,
    )


def analyze_impact_quality(
    text: str,
    metrics: list[str],
    action_verbs: list[str],
) -> tuple[int, list[str], list[str]]:

    score = 0
    strengths = []
    suggestions = []

    bullets = extract_bullets(text)

    if metrics:

        score += 5

        strengths.append(
            "The resume contains measurable results or scale indicators."
        )

    if action_verbs:
        score += 2

    if bullets:

        strong_bullets = 0

        for bullet in bullets:

            words = re.findall(
                r"\b\w+\b",
                bullet,
            )

            if len(words) >= 8:
                strong_bullets += 1

        if strong_bullets >= 4:
            score += 2

        elif strong_bullets >= 2:
            score += 1

    generic = detect_generic_phrases(
        text
    )

    if generic:

        score -= min(
            2,
            len(generic),
        )

        suggestions.append(
            "Replace generic claims with concrete evidence and outcomes."
        )

    if not metrics:

        suggestions.append(
            "Add truthful numbers or measurable outcomes to demonstrate impact."
        )

    return (
        max(0, min(score, 10)),
        strengths,
        suggestions,
    )


def analyze_ats_quality(
    text: str,
    sections: list[str],
    word_count: int,
) -> tuple[int, list[str], list[str]]:

    score = 0
    strengths = []
    suggestions = []

    if len(sections) >= 5:
        score += 3

    elif len(sections) >= 3:
        score += 2

    elif len(sections) >= 1:
        score += 1

    if 300 <= word_count <= 900:

        score += 3

        strengths.append(
            "Resume content length is within a generally practical range."
        )

    elif 180 <= word_count < 300:

        score += 2

        suggestions.append(
            "The resume is short; add relevant evidence rather than filler."
        )

    elif word_count > 1100:

        score += 1

        suggestions.append(
            "The resume is long; remove repetitive or low-value content."
        )

    else:

        suggestions.append(
            "The resume contains very little professional content."
        )

    formatting_noise = len(
        re.findall(
            r"[|]{3,}|[_]{3,}|[.]{5,}|[-]{5,}",
            text,
        )
    )

    if formatting_noise == 0:

        score += 2

    else:

        suggestions.append(
            "Reduce excessive decorative separators or formatting noise for cleaner ATS parsing."
        )

    if count_email_addresses(text) <= 1:

        score += 1

    else:

        suggestions.append(
            "Keep one primary professional email address."
        )

    generic = detect_generic_phrases(
        text
    )

    if not generic:

        score += 1

    else:

        suggestions.append(
            "Remove generic resume phrases and replace them with role-specific evidence."
        )

    return (
        max(0, min(score, 10)),
        strengths,
        suggestions,
    )


# =========================================================
# STRICT SCORE ENGINE
# =========================================================

def analyze_resume_text(
    text: str,
) -> dict[str, Any]:

    sections = detect_sections(text)
    skills = detect_skills(text)
    metrics = detect_metrics(text)
    action_verbs = detect_action_verbs(text)

    word_count = len(
        re.findall(
            r"\b\w+\b",
            text,
        )
    )

    meaningful_lines = count_meaningful_lines(
        text
    )

    (
        contact_score,
        contact_strengths,
        contact_suggestions,
    ) = analyze_contact_quality(text)

    (
        summary_score,
        summary_strengths,
        summary_suggestions,
    ) = analyze_summary_quality(
        text,
        sections,
    )

    education_score = (
        8
        if "education" in sections
        else 0
    )

    education_strengths = []
    education_suggestions = []

    if education_score:

        education_strengths.append(
            "Education information is present."
        )

    else:

        education_suggestions.append(
            "Add an Education section with degree, institution and relevant details."
        )

    (
        skills_score,
        skills_strengths,
        skills_suggestions,
    ) = analyze_skills_quality(
        text,
        skills,
    )

    (
        project_score,
        project_strengths,
        project_suggestions,
    ) = analyze_project_quality(
        text,
        skills,
        metrics,
        action_verbs,
    )

    (
        experience_score,
        experience_strengths,
        experience_suggestions,
    ) = analyze_experience_quality(
        text,
        action_verbs,
        metrics,
    )

    (
        impact_score,
        impact_strengths,
        impact_suggestions,
    ) = analyze_impact_quality(
        text,
        metrics,
        action_verbs,
    )

    (
        ats_score,
        ats_strengths,
        ats_suggestions,
    ) = analyze_ats_quality(
        text,
        sections,
        word_count,
    )

    certification_bonus = (
        2
        if "certifications" in sections
        else 0
    )

    achievement_bonus = (
        2
        if "achievements" in sections
        else 0
    )

    if "experience" in sections:

        experience_presence_bonus = 3

    elif "internship" in sections:

        experience_presence_bonus = 2

    else:

        experience_presence_bonus = 0

    score = (
        contact_score
        + summary_score
        + education_score
        + skills_score
        + project_score
        + experience_score
        + impact_score
        + ats_score
        + certification_bonus
        + achievement_bonus
        + experience_presence_bonus
    )

    score = max(
        0,
        min(score, 100),
    )

    has_core_content = (
        "skills" in sections
        and (
            "projects" in sections
            or "experience" in sections
            or "internship" in sections
        )
    )

    weak_content_signals = 0

    if word_count < 220:
        weak_content_signals += 1

    if not metrics:
        weak_content_signals += 1

    if not action_verbs:
        weak_content_signals += 1

    if detect_generic_phrases(text):
        weak_content_signals += 1

    if len(skills) < 3:
        weak_content_signals += 1

    if not has_core_content:
        weak_content_signals += 2

    if meaningful_lines < 12:
        weak_content_signals += 2

    if weak_content_signals >= 5:

        score = min(
            score,
            49,
        )

    elif weak_content_signals == 4:

        score = min(
            score,
            59,
        )

    elif weak_content_signals == 3:

        score = min(
            score,
            69,
        )

    elif weak_content_signals == 2:

        score = min(
            score,
            79,
        )

    missing_core = 0

    if "summary" not in sections:
        missing_core += 1

    if "education" not in sections:
        missing_core += 1

    if "skills" not in sections:
        missing_core += 1

    if (
        "projects" not in sections
        and "experience" not in sections
        and "internship" not in sections
    ):
        missing_core += 2

    if missing_core >= 4:
        score = min(score, 49)

    elif missing_core == 3:
        score = min(score, 59)

    elif missing_core == 2:
        score = min(score, 69)

    if word_count < 150:
        score = min(score, 39)

    elif word_count < 220:
        score = min(score, 54)

    bullets = extract_bullets(text)

    if (
        (
            "projects" in sections
            or "experience" in sections
        )
        and len(bullets) == 0
    ):
        score = min(
            score,
            59,
        )

    score = int(
        max(
            0,
            min(
                round(score),
                100,
            ),
        )
    )

    # -----------------------------------------------------
    # VERDICT
    # -----------------------------------------------------

    if score >= 90:

        verdict = "Excellent Resume"
        verdict_emoji = "🔥"

        verdict_message = (
            "Your resume is highly competitive and demonstrates strong evidence, clarity and professional impact."
        )

    elif score >= 80:

        verdict = "Strong Resume"
        verdict_emoji = "😎"

        verdict_message = (
            "Your resume has a strong foundation, with a few areas that can still be improved."
        )

    elif score >= 70:

        verdict = "Good Resume"
        verdict_emoji = "🙂"

        verdict_message = (
            "Your resume has good foundations, but several improvements could make it more competitive."
        )

    elif score >= 60:

        verdict = "Needs Improvement"
        verdict_emoji = "😐"

        verdict_message = (
            "Your resume has useful content, but important areas need improvement before applying."
        )

    elif score >= 40:

        verdict = "Weak Resume"
        verdict_emoji = "😕"

        verdict_message = (
            "Your resume needs significant improvement in content quality, evidence and presentation."
        )

    else:

        verdict = "Major Improvement Needed"
        verdict_emoji = "😟"

        verdict_message = (
            "Your resume currently lacks enough strong professional evidence and needs substantial improvement."
        )

    # -----------------------------------------------------
    # STRENGTHS
    # -----------------------------------------------------

    strengths = (
        contact_strengths
        + summary_strengths
        + education_strengths
        + skills_strengths
        + project_strengths
        + experience_strengths
        + impact_strengths
        + ats_strengths
    )

    strengths = list(
        dict.fromkeys(strengths)
    )

    # -----------------------------------------------------
    # SUGGESTIONS
    # -----------------------------------------------------

    suggestions = (
        contact_suggestions
        + summary_suggestions
        + education_suggestions
        + skills_suggestions
        + project_suggestions
        + experience_suggestions
        + impact_suggestions
        + ats_suggestions
    )

    suggestions = list(
        dict.fromkeys(suggestions)
    )

    # -----------------------------------------------------
    # WHY SCORE
    # -----------------------------------------------------

    why_score = []

    if contact_score >= 8:

        why_score.append(
            "Contact information is mostly complete."
        )

    elif contact_score < 5:

        why_score.append(
            "Contact information is incomplete."
        )

    if summary_score >= 8:

        why_score.append(
            "The professional summary is focused and relevant."
        )

    elif summary_score < 5:

        why_score.append(
            "The professional summary is weak or too generic."
        )

    if skills_score >= 8:

        why_score.append(
            "The Skills section contains a useful set of technical skills."
        )

    elif skills_score < 5:

        why_score.append(
            "The Skills section needs stronger or more relevant evidence."
        )

    if project_score >= 10:

        why_score.append(
            "Projects provide meaningful technical evidence."
        )

    elif (
        "projects" in sections
        and project_score < 7
    ):

        why_score.append(
            "Project descriptions need stronger implementation and outcome details."
        )

    if experience_score >= 10:

        why_score.append(
            "Experience demonstrates useful professional evidence."
        )

    elif (
        "experience" in sections
        or "internship" in sections
    ):

        why_score.append(
            "Experience descriptions need stronger achievement-focused bullets."
        )

    if metrics:

        why_score.append(
            "The resume uses measurable evidence."
        )

    else:

        why_score.append(
            "The resume has limited measurable evidence."
        )

    if detect_generic_phrases(text):

        why_score.append(
            "Some generic resume language reduces the content quality."
        )

    if not action_verbs:

        why_score.append(
            "Bullet points need stronger action-oriented language."
        )

    if word_count < 220:

        why_score.append(
            "The resume contains relatively little professional evidence."
        )

    breakdown = {
        "contact": contact_score,
        "summary": summary_score,
        "education": education_score,
        "skills": skills_score,
        "projects": project_score,
        "experience": (
            experience_score
            + experience_presence_bonus
        ),
        "impact": impact_score,
        "ats": ats_score,
        "certifications": certification_bonus,
        "achievements": achievement_bonus,
        "metrics": min(
            len(metrics),
            10,
        ),
        "action_verbs": min(
            len(action_verbs),
            10,
        ),
        "links": (
            int(
                "linkedin.com"
                in text.lower()
            )
            + int(
                "github.com"
                in text.lower()
            )
        ),
        "internship": (
            5
            if "internship" in sections
            else 0
        ),
    }

    return {
        "success": True,
        "score": score,
        "overall": verdict,
        "verdict": verdict,
        "verdict_emoji": verdict_emoji,
        "verdict_message": verdict_message,
        "why_score": why_score[:8],
        "breakdown": breakdown,
        "detected_sections": sections,
        "sections": sections,
        "skills_detected": skills,
        "skills": skills,
        "strengths": strengths[:12],
        "suggestions": suggestions[:12],
        "action_plan": suggestions[:6],
        "metrics_found": metrics,
        "action_verbs_found": action_verbs,
        "generic_phrases_found": detect_generic_phrases(text),
        "weak_bullet_phrases": detect_weak_bullets(text),
        "word_count": word_count,
        "bullet_count": len(bullets),
        "meaningful_lines": meaningful_lines,
    }


# =========================================================
# GEMINI HELPERS
# =========================================================

def is_transient_gemini_error(
    exc: Exception,
) -> bool:

    message = str(exc).lower()

    transient_terms = [
        "503",
        "500",
        "429",
        "unavailable",
        "service unavailable",
        "temporarily unavailable",
        "internal server error",
        "resource exhausted",
        "deadline exceeded",
        "timeout",
    ]

    return any(
        term in message
        for term in transient_terms
    )


def gemini_generate(
    prompt: str,
    *,
    response_schema=None,
    temperature: float = 0.2,
):

    if gemini_client is None or types is None:
        raise RuntimeError(
            "Gemini API key is not configured or the google-genai package is unavailable."
        )

    # Try current model first, then fallback.
    models = [
        os.getenv("RESUMEAI_GEMINI_MODEL", "gemini-3.8-flash"),
        "gemini-3.7-flash",
        "gemini-3.5-flash-lite",
    ]

    last_error = None

    for model_index, model_name in enumerate(
        models
    ):

        for attempt in range(3):

            try:

                config_kwargs = {
                    "temperature": temperature,
                }

                if response_schema is not None:

                    config_kwargs.update(
                        {
                            "response_mime_type": "application/json",
                            "response_schema": response_schema,
                        }
                    )

                response = (
                    gemini_client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            **config_kwargs
                        ),
                    )
                )

                return response

            except Exception as exc:

                last_error = exc

                print(
                    f"Gemini error using {model_name}, "
                    f"attempt {attempt + 1}:",
                    repr(exc),
                )

                if not is_transient_gemini_error(
                    exc
                ):
                    break

                if attempt < 2:

                    wait_time = min(
                        2 ** attempt,
                        6,
                    )

                    time.sleep(
                        wait_time
                    )

        print(
            f"Gemini model {model_name} exhausted."
        )

        if model_index < len(models) - 1:
            continue

    raise RuntimeError(
        str(last_error)
        if last_error
        else "Gemini request failed."
    )


# =========================================================
# GEMINI AI ADVISOR
# =========================================================

def generate_ai_feedback(
    resume_text: str,
) -> dict[str, Any]:

    if not gemini_client:

        return {
            "success": False,
            "message": (
                "Gemini API key is not configured."
            ),
        }

    prompt = f"""
You are ResumeAI's expert AI Resume Advisor.

Analyze ONLY the resume text provided below.

Give honest, evidence-based feedback.

STRICT RULES:
- Never invent facts.
- Never assume skills.
- Never invent employers.
- Never invent education.
- Never invent certifications.
- Never invent achievements.
- Never invent numbers.
- Never claim the resume contains something that is not visible.
- If something is missing, explicitly identify it as missing.
- Recommendations may suggest what the candidate should add.
- Do not give fake praise.
- Do not call a weak resume excellent.
- Be specific and practical.
- Prioritize the most important problems.
- Evaluate clarity, ATS readability, projects, experience,
  measurable impact, summary quality, technical evidence
  and overall job-readiness.
- Do not calculate or invent a resume score.
- The rule-based analyzer calculates the score separately.

RESUME:
----------------
{resume_text}
----------------

Before writing feedback, review the complete extracted resume from beginning to end.
Cross-check contact details, section presence, skills, education, experience, projects,
certifications and achievements against the actual text. If OCR appears noisy, do not
turn an unclear token into a confident claim; say it is unclear instead.
"""

    try:

        response = gemini_generate(
            prompt,
            response_schema=FeedbackSchema,
            temperature=0.2,
        )

        data = json.loads(
            response.text
        )

        return {
            "success": True,
            "overall_advice": data.get(
                "overall_advice",
                "",
            ),
            "high_priority_issues": data.get(
                "high_priority_issues",
                [],
            ),
            "medium_priority_issues": data.get(
                "medium_priority_issues",
                [],
            ),
            "strengths": data.get(
                "strengths",
                [],
            ),
            "actionable_suggestions": data.get(
                "actionable_suggestions",
                [],
            ),
        }

    except Exception as exc:

        print(
            "Gemini feedback error:",
            repr(exc),
        )

        return {
            "success": False,
            "message": str(exc),
        }


def run_ai_feedback_job(
    job_id: str,
    resume_text: str,
):

    if job_id not in ai_jobs:
        return

    ai_jobs[job_id]["status"] = (
        "processing"
    )

    try:

        feedback = generate_ai_feedback(
            resume_text
        )

        if not feedback.get("success"):

            ai_jobs[job_id]["status"] = (
                "failed"
            )

            ai_jobs[job_id]["message"] = (
                feedback.get(
                    "message",
                    "AI feedback failed.",
                )
            )

            return

        ai_jobs[job_id]["status"] = (
            "completed"
        )

        ai_jobs[job_id]["ai_feedback"] = (
            feedback
        )

    except Exception as exc:

        ai_jobs[job_id]["status"] = (
            "failed"
        )

        ai_jobs[job_id]["message"] = str(
            exc
        )


# =========================================================
# AI CHAT
# =========================================================

def _chat_history_text(history: list[dict[str, str]]) -> str:
    cleaned = []
    for item in history[-12:]:
        role = str(item.get('role') or '').strip().lower()
        text = str(item.get('text') or '').strip()
        if role in {'user', 'assistant'} and text:
            cleaned.append(f"{role.upper()}: {text[:2500]}")
    return "\n".join(cleaned)


def generate_chat_answer(
    resume_text: str,
    message: str,
    history: list[dict[str, str]] | None = None,
    page_context: str = 'resume',
) -> str:
    if not gemini_client:
        raise RuntimeError("Gemini API key is not configured.")

    history_text = _chat_history_text(history or []) or "No previous chat messages."
    prompt = f"""
You are ResumeAI's persistent AI Career Assistant.

You are helping the user across the ResumeAI website. The current page/context is: {page_context}.
The resume below is the source of truth for resume-related facts.

IMPORTANT:
- Remember and use the previous chat turns below. Answer follow-up questions in context.
- The user may ask in English, Hindi, or Hinglish. Reply naturally in the same language/style.
- Use the resume for facts about the candidate. Never invent skills, projects, employers, education,
  certifications, achievements, numbers, job titles, responsibilities or experience.
- If the resume does not contain the requested fact, say that it is not present/unclear.
- You may give recommendations, but label them as recommendations rather than facts.
- If the question is about ResumeAI features (Jobs, Mocks, Dashboard, Settings), explain how the feature
  should work and use available resume context when relevant. Do not claim an action was completed unless it was.
- Give a direct answer first, then useful detail. Do not repeat the user's question.

PREVIOUS CHAT:
----------------
{history_text}
----------------

RESUME:
----------------
{resume_text[:50000]}
----------------

CURRENT USER MESSAGE:
{message}
"""
    response = gemini_generate(prompt, temperature=0.25)
    answer = response.text.strip() if response.text else ''
    if not answer:
        raise RuntimeError('Gemini returned an empty response.')
    return answer


def run_chatbot_job(
    chat_job_id: str,
    resume_text: str,
    message: str,
    history: list[dict[str, str]] | None = None,
    page_context: str = 'resume',
):
    if chat_job_id not in chat_jobs:
        return
    chat_jobs[chat_job_id]['status'] = 'processing'
    try:
        answer = generate_chat_answer(resume_text, message, history, page_context)
        chat_jobs[chat_job_id]['status'] = 'completed'
        chat_jobs[chat_job_id]['chat_answer'] = answer
    except Exception as exc:
        print('Chat error:', repr(exc))
        chat_jobs[chat_job_id]['status'] = 'failed'
        chat_jobs[chat_job_id]['message'] = str(exc)
# AI PROFESSIONAL RESUME ENHANCER
# =========================================================

def generate_professional_resume_text(
    resume_text: str,
) -> str:

    if not gemini_client:

        raise RuntimeError(
            "Gemini API key is not configured."
        )

    prompt = f"""
You are ResumeAI's professional resume editor.

Rewrite the ORIGINAL RESUME into a polished,
professional, ATS-friendly resume.

VERY IMPORTANT:

Use ONLY facts contained in the original resume.

NEVER invent:
- companies
- job titles
- skills
- technologies
- projects
- certifications
- achievements
- numbers
- percentages
- dates
- responsibilities
- employers
- education
- experience

You ARE allowed to:
- fix grammar
- improve sentence structure
- remove unnecessary repetition
- make wording professional
- convert weak bullet wording into stronger wording
  when the underlying fact remains unchanged
- organize information into professional sections
- improve readability
- make bullets concise
- preserve all genuine facts

If a result or number is not present, DO NOT create one.

Preserve genuine email, phone, LinkedIn and GitHub details.

Use these standard section headings whenever
the information exists:

PROFESSIONAL SUMMARY
SKILLS
EXPERIENCE
INTERNSHIP
PROJECTS
EDUCATION
CERTIFICATIONS
ACHIEVEMENTS

Do not add a fake section merely because it sounds professional.

Every important factual item from the original resume
must remain somewhere in the enhanced resume.

Return ONLY the resume text.

ORIGINAL RESUME
==================================================
{resume_text[:30000]}
==================================================
"""

    response = gemini_generate(
        prompt,
        temperature=0.2,
    )

    enhanced = (
        response.text.strip()
        if response.text
        else ""
    )

    if not enhanced:

        raise RuntimeError(
            "Gemini returned an empty enhanced resume."
        )

    return enhanced


# =========================================================
# PDF TEXT HELPERS
# =========================================================

PDF_SECTION_NAMES = {
    "professional summary",
    "summary",
    "profile",
    "objective",
    "skills",
    "technical skills",
    "core skills",
    "experience",
    "work experience",
    "professional experience",
    "employment",
    "internship",
    "internships",
    "projects",
    "academic projects",
    "education",
    "certifications",
    "certification",
    "certificates",
    "achievements",
    "awards",
    "honors",
}


def is_pdf_section_heading(
    line: str,
) -> bool:

    stripped = line.strip()

    if not stripped:
        return False

    cleaned = re.sub(
        r"[^a-zA-Z ]",
        "",
        stripped,
    ).strip().lower()

    if cleaned in PDF_SECTION_NAMES:
        return True

    # ALL-CAPS short section headings
    letters_only = re.sub(
        r"[^A-Za-z]",
        "",
        stripped,
    )

    if (
        letters_only
        and stripped.upper() == stripped
        and len(stripped.split()) <= 5
        and len(stripped) <= 45
    ):
        return True

    return False


def clean_resume_for_pdf(
    text: str,
) -> str:

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    # Remove common Markdown formatting generated by AI.
    text = re.sub(
        r"\*\*(.*?)\*\*",
        r"\1",
        text,
    )

    text = re.sub(
        r"__(.*?)__",
        r"\1",
        text,
    )

    lines = []

    for raw_line in text.split("\n"):

        line = re.sub(
            r"[ \t]+",
            " ",
            raw_line,
        ).strip()

        # Remove heading markdown.
        line = re.sub(
            r"^#{1,6}\s*",
            "",
            line,
        )

        if not line:

            if (
                lines
                and lines[-1] != ""
            ):
                lines.append("")

            continue

        lines.append(line)

    while (
        lines
        and lines[-1] == ""
    ):
        lines.pop()

    return "\n".join(lines)


def split_resume_lines(
    text: str,
) -> list[str]:

    cleaned = clean_resume_for_pdf(
        text
    )

    return cleaned.split("\n")


def escape_pdf_text(
    text: str,
) -> str:

    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def is_bullet_line(
    line: str,
) -> bool:

    return bool(
        re.match(
            r"^(?:[•●▪◦‣*-]|\d+[.)])\s+",
            line.strip(),
        )
    )


def remove_bullet_marker(
    line: str,
) -> str:

    return re.sub(
        r"^(?:[•●▪◦‣*-]|\d+[.)])\s+",
        "",
        line.strip(),
    )


# =========================================================
# PHOTO PROCESSING
# =========================================================

def prepare_profile_photo(
    photo_data: bytes,
) -> io.BytesIO:

    image = Image.open(
        io.BytesIO(photo_data)
    )

    image = ImageOps.exif_transpose(
        image
    )

    image = image.convert("RGB")

    max_dimension = 1200

    if max(image.size) > max_dimension:

        ratio = (
            max_dimension
            / max(image.size)
        )

        new_size = (
            max(
                1,
                int(
                    image.width * ratio
                ),
            ),
            max(
                1,
                int(
                    image.height * ratio
                ),
            ),
        )

        image = image.resize(
            new_size,
            Image.LANCZOS,
        )

    output = io.BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=94,
    )

    output.seek(0)

    return output


# =========================================================
# EXTRACT PHOTO FROM PDF
# =========================================================

def extract_profile_photo_from_pdf(
    data: bytes,
) -> bytes | None:

    try:

        doc = fitz.open(
            stream=data,
            filetype="pdf",
        )

        candidates = []

        for page_number, page in enumerate(
            doc
        ):

            images = page.get_images(
                full=True
            )

            for image_info in images:

                xref = image_info[0]

                try:

                    extracted = (
                        doc.extract_image(
                            xref
                        )
                    )

                    image_bytes = (
                        extracted.get(
                            "image"
                        )
                    )

                    if not image_bytes:
                        continue

                    image = Image.open(
                        io.BytesIO(
                            image_bytes
                        )
                    )

                    width, height = (
                        image.size
                    )

                    if (
                        width < 100
                        or height < 100
                    ):
                        continue

                    aspect = (
                        width / height
                    )

                    # Ignore banners.
                    if (
                        aspect < 0.45
                        or aspect > 1.8
                    ):
                        continue

                    area = width * height

                    score = 0

                    if (
                        0.55
                        <= aspect
                        <= 1.35
                    ):
                        score += 5

                    if page_number == 0:
                        score += 3

                    if area >= 40000:
                        score += 2

                    candidates.append(
                        (
                            score,
                            page_number,
                            image_bytes,
                        )
                    )

                except Exception:
                    continue

        doc.close()

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (
                item[0],
                -item[1],
            ),
            reverse=True,
        )

        return candidates[0][2]

    except Exception as exc:

        print(
            "PDF photo extraction error:",
            repr(exc),
        )

        return None


# =========================================================
# EXTRACT PHOTO FROM DOCX
# =========================================================

def extract_profile_photo_from_docx(
    data: bytes,
) -> bytes | None:

    try:

        document = Document(
            io.BytesIO(data)
        )

        candidates = []

        # Inline images first.
        for shape in document.inline_shapes:

            try:

                blip = (
                    shape
                    ._inline
                    .graphic
                    .graphicData
                    .pic
                    .blipFill
                    .blip
                )

                relationship_id = (
                    blip.embed
                )

                related_part = (
                    document.part
                    .related_parts
                    .get(
                        relationship_id
                    )
                )

                if not related_part:
                    continue

                image_bytes = (
                    related_part.blob
                )

                image = Image.open(
                    io.BytesIO(
                        image_bytes
                    )
                )

                width, height = (
                    image.size
                )

                if (
                    width < 100
                    or height < 100
                ):
                    continue

                aspect = (
                    width / height
                )

                if (
                    aspect < 0.45
                    or aspect > 1.8
                ):
                    continue

                area = width * height

                score = 5

                if (
                    0.55
                    <= aspect
                    <= 1.35
                ):
                    score += 4

                if area >= 40000:
                    score += 2

                candidates.append(
                    (
                        score,
                        image_bytes,
                    )
                )

            except Exception:
                continue

        # Fallback to all image relationships.
        if not candidates:

            for relationship in (
                document.part.rels.values()
            ):

                try:

                    if (
                        "image"
                        not in relationship.reltype.lower()
                    ):
                        continue

                    related_part = (
                        relationship.target_part
                    )

                    image_bytes = (
                        related_part.blob
                    )

                    image = Image.open(
                        io.BytesIO(
                            image_bytes
                        )
                    )

                    width, height = (
                        image.size
                    )

                    if (
                        width < 100
                        or height < 100
                    ):
                        continue

                    aspect = (
                        width / height
                    )

                    if (
                        aspect < 0.45
                        or aspect > 1.8
                    ):
                        continue

                    score = 5

                    if (
                        0.55
                        <= aspect
                        <= 1.35
                    ):
                        score += 4

                    candidates.append(
                        (
                            score,
                            image_bytes,
                        )
                    )

                except Exception:
                    continue

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return candidates[0][1]

    except Exception as exc:

        print(
            "DOCX photo extraction error:",
            repr(exc),
        )

        return None


# =========================================================
# EXTRACT ORIGINAL PROFILE PHOTO
# =========================================================

def extract_embedded_profile_photo(
    filename: str,
    data: bytes,
) -> bytes | None:

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension == ".pdf":

        return extract_profile_photo_from_pdf(
            data
        )

    if extension == ".docx":

        return extract_profile_photo_from_docx(
            data
        )

    # JPG/PNG resume itself is not treated
    # as profile photo.
    return None


# =========================================================
# VALIDATE USER PHOTO
# =========================================================

def validate_uploaded_photo(
    photo_data: bytes,
) -> bytes | None:

    if not photo_data:
        return None

    if len(photo_data) > (
        8 * 1024 * 1024
    ):
        return None

    try:

        image = Image.open(
            io.BytesIO(photo_data)
        )

        image.verify()

        image = Image.open(
            io.BytesIO(photo_data)
        )

        if (
            image.width < 80
            or image.height < 80
        ):
            return None

        return photo_data

    except Exception:

        return None


# =========================================================
# PHOTO DATA URL FOR WEB PREVIEW
# =========================================================

def photo_to_data_url(photo_data: bytes | None) -> str:
    if not photo_data:
        return ""
    try:
        image = Image.open(io.BytesIO(photo_data)).convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception:
        return ""


# =========================================================
# PROFESSIONAL PDF BUILDER
# =========================================================

def build_professional_pdf(
    resume_text: str,
    photo_data: bytes | None = None,
) -> bytes:

    output = io.BytesIO()

    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=0.58 * inch,
        leftMargin=0.58 * inch,
        topMargin=0.48 * inch,
        bottomMargin=0.50 * inch,
        title="ResumeAI Professional Resume",
        author="ResumeAI",
    )

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        "ResumeName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=24,
        textColor=colors.HexColor(
            "#172033"
        ),
        alignment=TA_LEFT,
        spaceAfter=5,
    )

    contact_style = ParagraphStyle(
        "ResumeContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor(
            "#5F6B7A"
        ),
        alignment=TA_LEFT,
        spaceAfter=8,
    )

    section_style = ParagraphStyle(
        "ResumeSection",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor(
            "#173B72"
        ),
        spaceBefore=9,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=13,
        textColor=colors.HexColor(
            "#26324A"
        ),
        spaceAfter=3,
    )

    bullet_style = ParagraphStyle(
        "ResumeBullet",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-7,
        spaceAfter=3,
    )

    story = []

    lines = split_resume_lines(
        resume_text
    )

    non_empty = [
        line
        for line in lines
        if line.strip()
    ]

    name = (
        non_empty[0]
        if non_empty
        else "Professional Resume"
    )

    contact_line = ""

    if len(non_empty) > 1:

        possible_contact = non_empty[1]

        if (
            "@"
            in possible_contact
            or re.search(
                r"\d{10}",
                possible_contact,
            )
            or "linkedin"
            in possible_contact.lower()
            or "github"
            in possible_contact.lower()
            or "|"
            in possible_contact
        ):

            contact_line = (
                possible_contact
            )

    # -----------------------------------------------------
    # HEADER
    # -----------------------------------------------------

    header_left = [
        Paragraph(
            escape_pdf_text(name),
            name_style,
        )
    ]

    if contact_line:

        header_left.append(
            Paragraph(
                escape_pdf_text(
                    contact_line
                ),
                contact_style,
            )
        )

    # Fixed photo area.
    if photo_data:

        try:

            photo_stream = (
                prepare_profile_photo(
                    photo_data
                )
            )

            photo = ReportLabImage(
                photo_stream,
                width=0.92 * inch,
                height=0.92 * inch,
                kind="proportional",
            )

            photo_cell = photo

        except Exception as exc:

            print(
                "Photo rendering error:",
                repr(exc),
            )

            photo_cell = Spacer(
                0.92 * inch,
                0.92 * inch,
            )

    else:

        # Completely blank reserved area.
        photo_cell = Spacer(
            0.92 * inch,
            0.92 * inch,
        )

    header_table = Table(
        [
            [
                header_left,
                photo_cell,
            ]
        ],
        colWidths=[
            6.35 * inch,
            0.95 * inch,
        ],
        rowHeights=[
            0.95 * inch,
        ],
    )

    header_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (1, 0),
                    "RIGHT",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    story.append(
        header_table
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor(
                "#315BDC"
            ),
            spaceBefore=2,
            spaceAfter=7,
        )
    )

    # -----------------------------------------------------
    # BODY
    # -----------------------------------------------------

    skip_contact = bool(
        contact_line
    )

    for index, line in enumerate(
        lines
    ):

        stripped = line.strip()

        if not stripped:

            story.append(
                Spacer(
                    1,
                    2,
                )
            )

            continue

        # Name already rendered.
        if index == 0:
            continue

        # Contact already rendered.
        if (
            skip_contact
            and index == 1
        ):
            continue

        if is_pdf_section_heading(
            stripped
        ):

            heading = stripped.upper()

            story.append(
                Paragraph(
                    escape_pdf_text(
                        heading
                    ),
                    section_style,
                )
            )

            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.55,
                    color=colors.HexColor(
                        "#D5DDEA"
                    ),
                    spaceBefore=0,
                    spaceAfter=4,
                )
            )

            continue

        if is_bullet_line(
            stripped
        ):

            bullet_text = (
                remove_bullet_marker(
                    stripped
                )
            )

            story.append(
                Paragraph(
                    "• "
                    + escape_pdf_text(
                        bullet_text
                    ),
                    bullet_style,
                )
            )

            continue

        # Role / project / institution
        # lines are visually emphasized.
        if (
            " | " in stripped
            or " — " in stripped
            or " - " in stripped
        ):

            story.append(
                Paragraph(
                    "<b>"
                    + escape_pdf_text(
                        stripped
                    )
                    + "</b>",
                    body_style,
                )
            )

        else:

            story.append(
                Paragraph(
                    escape_pdf_text(
                        stripped
                    ),
                    body_style,
                )
            )

    # -----------------------------------------------------
    # FOOTER
    # -----------------------------------------------------

    def draw_footer(
        canvas,
        doc,
    ):

        canvas.saveState()

        canvas.setFont(
            "Helvetica",
            7,
        )

        canvas.setFillColor(
            colors.HexColor(
                "#8A94A6"
            )
        )

        canvas.drawCentredString(
            A4[0] / 2,
            0.27 * inch,
            "ResumeAI • Professional Resume",
        )

        canvas.restoreState()

    document.build(
        story,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
    )

    output.seek(0)

    return output.read()


def _template_resume_parts(resume_text: str):
    lines = [line.strip() for line in split_resume_lines(resume_text) if line.strip()]
    name = lines[0] if lines else "Professional Resume"
    contact = ""
    start = 1
    if len(lines) > 1 and (
        "@" in lines[1]
        or re.search(r"\d{7,}", lines[1])
        or "linkedin" in lines[1].lower()
        or "github" in lines[1].lower()
        or "|" in lines[1]
    ):
        contact = lines[1]
        start = 2

    sections = []
    current = None
    for line in lines[start:]:
        if is_pdf_section_heading(line):
            current = {"title": line, "items": []}
            sections.append(current)
        elif current is not None:
            current["items"].append(line)
        else:
            if not sections:
                current = {"title": "Professional Summary", "items": []}
                sections.append(current)
            sections[0]["items"].append(line)
    return name, contact, sections


def _template_paragraphs(section, heading_style, body_style, bullet_style):
    flow = [Paragraph(escape_pdf_text(section["title"].upper()), heading_style)]
    for item in section["items"]:
        if is_bullet_line(item):
            flow.append(Paragraph("• " + escape_pdf_text(remove_bullet_marker(item)), bullet_style))
        else:
            flow.append(Paragraph(escape_pdf_text(item), body_style))
    return flow


def build_template_pdf(
    resume_text: str,
    photo_data: bytes | None,
    template: str,
) -> bytes:
    name, contact, sections = _template_resume_parts(resume_text)
    output = io.BytesIO()

    document = SimpleDocTemplate(
        output, pagesize=A4,
        rightMargin=0.45 * inch, leftMargin=0.45 * inch,
        topMargin=0.42 * inch, bottomMargin=0.45 * inch,
        title=f"ResumeAI {template.title()} Resume", author="ResumeAI"
    )
    styles = getSampleStyleSheet()

    if template == "executive":
        return _build_executive_pdf(document, output, name, contact, sections, photo_data, styles)
    if template == "modern":
        return _build_modern_pdf(document, output, name, contact, sections, photo_data, styles)
    return _build_minimal_pdf(document, output, name, contact, sections, photo_data, styles)


def _photo_flowable(photo_data, size=0.78):
    if not photo_data:
        return Spacer(size * inch, size * inch)
    try:
        stream = prepare_profile_photo(photo_data)
        return ReportLabImage(stream, width=size * inch, height=size * inch, kind="proportional")
    except Exception:
        return Spacer(size * inch, size * inch)


def _build_executive_pdf(document, output, name, contact, sections, photo_data, styles):
    navy = colors.HexColor("#173B72")
    light = colors.HexColor("#EAF2F8")
    white = colors.white
    name_style = ParagraphStyle("ExecName", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=23, leading=25, textColor=white)
    contact_style = ParagraphStyle("ExecContact", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#E5EEF8"))
    side_head = ParagraphStyle("ExecSideHead", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=navy, spaceBefore=5, spaceAfter=4)
    head = ParagraphStyle("ExecHead", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10.5, leading=12, textColor=navy, spaceBefore=6, spaceAfter=4)
    body = ParagraphStyle("ExecBody", parent=styles["Normal"], fontName="Helvetica", fontSize=8.6, leading=11.5, textColor=colors.HexColor("#2D3748"), spaceAfter=3)
    bullet = ParagraphStyle("ExecBullet", parent=body, leftIndent=10, firstLineIndent=-6)

    left_names = {"skills", "technical skills", "languages", "certifications", "achievements", "awards", "interests"}
    left_sections = [s for s in sections if s["title"].lower().rstrip(":") in left_names]
    right_sections = [s for s in sections if s not in left_sections]

    header_left = [Paragraph(escape_pdf_text(name.upper()), name_style)]
    if contact:
        header_left.append(Paragraph(escape_pdf_text(contact), contact_style))
    header_cell = [header_left, _photo_flowable(photo_data, 0.78)]
    header = Table([header_cell], colWidths=[6.45 * inch, 0.8 * inch], rowHeights=[0.88 * inch])
    header.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), navy), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING",(0,0),(0,0),14), ("RIGHTPADDING",(-1,0),(-1,0),12), ("TOPPADDING",(0,0),(-1,-1),8), ("BOTTOMPADDING",(0,0),(-1,-1),8)]))

    story=[header, Spacer(1, 0.10*inch)]
    left_flow=[]
    for sec in left_sections:
        left_flow.extend(_template_paragraphs(sec, side_head, body, bullet))
        left_flow.append(Spacer(1, 0.04*inch))
    right_flow=[]
    for sec in right_sections:
        right_flow.extend(_template_paragraphs(sec, head, body, bullet))
        right_flow.append(Spacer(1, 0.03*inch))
    if not left_flow:
        left_flow=[Paragraph("SKILLS", side_head), Paragraph("See the sections on the right for the full resume content.", body)]

    body_table=Table([[left_flow, right_flow]], colWidths=[1.85*inch, 5.4*inch], repeatRows=0)
    body_table.setStyle(TableStyle([("BACKGROUND",(0,0),(0,0),light),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(0,0),12),("RIGHTPADDING",(0,0),(0,0),10),("LEFTPADDING",(1,0),(1,0),15),("RIGHTPADDING",(1,0),(1,0),8),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    story.append(body_table)

    def footer(canvas, doc):
        canvas.saveState(); canvas.setFont("Helvetica",7); canvas.setFillColor(colors.HexColor("#7A8797")); canvas.drawCentredString(A4[0]/2,0.22*inch,"ResumeAI • Executive Two-Column"); canvas.restoreState()
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    output.seek(0); return output.read()


def _build_modern_pdf(document, output, name, contact, sections, photo_data, styles):
    purple=colors.HexColor("#5B35D5"); pale=colors.HexColor("#F1EEFF")
    name_style=ParagraphStyle("ModName",parent=styles["Normal"],fontName="Helvetica-Bold",fontSize=21,leading=23,textColor=colors.HexColor("#182038"))
    contact_style=ParagraphStyle("ModContact",parent=styles["Normal"],fontName="Helvetica",fontSize=8,leading=10,textColor=colors.HexColor("#667085"))
    head=ParagraphStyle("ModHead",parent=styles["Normal"],fontName="Helvetica-Bold",fontSize=10,leading=12,textColor=purple,spaceBefore=5,spaceAfter=4)
    body=ParagraphStyle("ModBody",parent=styles["Normal"],fontName="Helvetica",fontSize=8.7,leading=11.7,textColor=colors.HexColor("#26324A"),spaceAfter=3)
    bullet=ParagraphStyle("ModBullet",parent=body,leftIndent=10,firstLineIndent=-6)
    left_names={"skills","technical skills","languages","certifications","achievements","awards","interests"}
    left=[s for s in sections if s["title"].lower().rstrip(":") in left_names]; right=[s for s in sections if s not in left]
    left_flow=[Paragraph(escape_pdf_text(name.upper()), ParagraphStyle("SideName",parent=styles["Normal"],fontName="Helvetica-Bold",fontSize=14,textColor=colors.white,leading=16))]
    if contact: left_flow.append(Paragraph(escape_pdf_text(contact), ParagraphStyle("SideContact",parent=styles["Normal"],fontName="Helvetica",fontSize=7.2,textColor=colors.HexColor("#EDE9FF"),leading=9)))
    left_flow.append(Spacer(1,0.12*inch))
    for sec in left:
        left_flow.extend(_template_paragraphs(sec, ParagraphStyle("SideHead2",parent=head,textColor=colors.white,spaceBefore=6), ParagraphStyle("SideBody2",parent=body,textColor=colors.HexColor("#E8E5F7")), ParagraphStyle("SideBullet2",parent=bullet,textColor=colors.HexColor("#E8E5F7"))))
    if not left:
        left_flow.append(Paragraph("SKILLS", ParagraphStyle("SideHead3",parent=head,textColor=colors.white)))
    right_flow=[]
    for sec in right:
        right_flow.extend(_template_paragraphs(sec,head,body,bullet)); right_flow.append(Spacer(1,0.03*inch))
    header_table=Table([[left_flow,right_flow]],colWidths=[2.15*inch,5.1*inch])
    header_table.setStyle(TableStyle([("BACKGROUND",(0,0),(0,0),purple),("BACKGROUND",(1,0),(1,0),colors.white),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(0,0),14),("RIGHTPADDING",(0,0),(0,0),12),("LEFTPADDING",(1,0),(1,0),18),("RIGHTPADDING",(1,0),(1,0),8),("TOPPADDING",(0,0),(-1,-1),14),("BOTTOMPADDING",(0,0),(-1,-1),12)]))
    story=[header_table]
    def footer(canvas,doc):
        canvas.saveState(); canvas.setFont("Helvetica",7); canvas.setFillColor(colors.HexColor("#8B94A6")); canvas.drawCentredString(A4[0]/2,0.22*inch,"ResumeAI • Modern Sidebar"); canvas.restoreState()
    document.build(story,onFirstPage=footer,onLaterPages=footer); output.seek(0); return output.read()


def _build_minimal_pdf(document, output, name, contact, sections, photo_data, styles):
    black=colors.HexColor("#111827"); gray=colors.HexColor("#667085")
    name_style=ParagraphStyle("MinName",parent=styles["Normal"],fontName="Helvetica-Bold",fontSize=24,leading=26,textColor=black,spaceAfter=4)
    contact_style=ParagraphStyle("MinContact",parent=styles["Normal"],fontName="Helvetica",fontSize=8,leading=10,textColor=gray,spaceAfter=8)
    head=ParagraphStyle("MinHead",parent=styles["Normal"],fontName="Helvetica-Bold",fontSize=10,leading=12,textColor=black,spaceBefore=10,spaceAfter=4)
    body=ParagraphStyle("MinBody",parent=styles["Normal"],fontName="Helvetica",fontSize=8.8,leading=12,textColor=colors.HexColor("#374151"),spaceAfter=3)
    bullet=ParagraphStyle("MinBullet",parent=body,leftIndent=11,firstLineIndent=-7)
    header=[]
    if photo_data:
        photo=_photo_flowable(photo_data,0.72); header=Table([[[Paragraph(escape_pdf_text(name),name_style),Paragraph(escape_pdf_text(contact),contact_style)],photo]],colWidths=[6.35*inch,0.72*inch])
        header.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("ALIGN",(1,0),(1,0),"RIGHT"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]))
    else:
        header=[Paragraph(escape_pdf_text(name),name_style)]
        if contact: header.append(Paragraph(escape_pdf_text(contact),contact_style))
    story=[header,HRFlowable(width="100%",thickness=0.8,color=black,spaceBefore=1,spaceAfter=4)]
    for sec in sections:
        story.extend(_template_paragraphs(sec,head,body,bullet)); story.append(Spacer(1,0.02*inch))
    def footer(canvas,doc):
        canvas.saveState(); canvas.setFont("Helvetica",7); canvas.setFillColor(gray); canvas.drawCentredString(A4[0]/2,0.22*inch,"ResumeAI • Minimal ATS"); canvas.restoreState()
    document.build(story,onFirstPage=footer,onLaterPages=footer); output.seek(0); return output.read()


def build_final_resume_pdf(
    resume_text: str,
    photo_data: bytes | None = None,
    template: str = "professional",
) -> bytes:
    template = (template or "professional").lower().strip()
    if template == "professional":
        return build_professional_pdf(resume_text, photo_data)
    if template in {"executive", "modern", "minimal"}:
        return build_template_pdf(resume_text, photo_data, template)
    return build_professional_pdf(resume_text, photo_data)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "success": True,
        "message": (
            "AI Resume Analyzer Backend is running!"
        ),
    }
    # =========================================================
# ANALYZE
# =========================================================

@app.post("/analyze")
async def analyze_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):

    filename = file.filename or ""

    allowed = {
        ".pdf",
        ".doc",
        ".docx",
        ".rtf",
        ".odt",
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".txt",
    }

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension not in allowed:

        return {
            "success": False,
            "message": (
                "PDF, DOC, DOCX, RTF, ODT, JPG, JPEG, PNG, WEBP and TXT resume files are supported."
            ),
        }

    try:

        data = await file.read()

        if not data:

            return {
                "success": False,
                "message": (
                    "The uploaded file is empty."
                ),
            }

        text = await extract_resume_text(
            filename,
            data,
        )

        if len(text.strip()) < 35:

            return {
                "success": False,
                "message": (
                    "Could not extract enough text. Please upload a clear resume."
                ),
            }

        if not looks_like_resume(
            text,
            filename,
        ):

            return {
                "success": False,
                "message": (
                    "This file does not appear to be a resume. Please upload a valid resume in PDF, DOC, DOCX, RTF, ODT, JPG, JPEG, PNG, WEBP or TXT format."
                ),
            }

        analysis = analyze_resume_text(
            text
        )

        job_id = str(uuid.uuid4())

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO resume_analyses(user_id, filename, score, analysis_json, created_at, resume_text, job_id) VALUES(?,?,?,?,?,?,?)",
                (
                    user['id'],
                    filename,
                    int(analysis.get('score', 0)),
                    json.dumps(analysis, ensure_ascii=False),
                    __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                    text,
                    job_id,
                ),
            )
            try:
                conn.execute('INSERT INTO notification_events(user_id,title,body,kind,created_at) VALUES(?,?,?,?,?)', (user['id'], 'Resume analyzed', f"{filename} was analyzed with a score of {int(analysis.get('score', 0))}/100.", 'resume', __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()))
            except Exception:
                pass
            conn.commit()
        finally:
            conn.close()

        ai_jobs[job_id] = {
            "status": "queued",
            "ai_feedback": None,
            "message": None,
            "resume_text": text,
            "filename": filename,
        }

        background_tasks.add_task(
            run_ai_feedback_job,
            job_id,
            text,
        )

        return {
            **analysis,

            "filename": filename,

            "ai_feedback": None,
            "ai_feedback_status": (
                "processing"
            ),

            "ai_feedback_job_id": job_id,
            "resume_job_id": job_id,
            "job_id": job_id,
        }

    except ValueError as exc:

        return {
            "success": False,
            "message": str(exc),
        }

    except Exception as exc:

        print(
            "Analyze error:",
            repr(exc),
        )

        return {
            "success": False,
            "message": (
                "We could not process this resume. Please try another clear PDF, DOC, DOCX, RTF, ODT, JPG, JPEG, PNG, WEBP or TXT resume."
            ),
        }


# =========================================================
# AI FEEDBACK STATUS
# =========================================================

@app.get(
    "/ai-feedback/{job_id}"
)
def get_ai_feedback(
    job_id: str,
):

    job = ai_jobs.get(
        job_id
    )

    if not job:

        return {
            "success": False,
            "status": "failed",
            "message": (
                "AI feedback job not found."
            ),
        }

    return {
        "success": True,
        "status": job.get(
            "status"
        ),
        "ai_feedback": job.get(
            "ai_feedback"
        ),
        "message": job.get(
            "message"
        ),
    }


# =========================================================
# START CHAT
# =========================================================

@app.post("/chat")
async def start_chat(request: ChatRequest, user=Depends(get_current_user)):
    resume_job_id = request.job_id.strip()
    job = ai_jobs.get(resume_job_id) or {}
    resume_text = job.get('resume_text') or ''

    # Survive page refreshes/backend restarts by reading the persisted resume.
    if not resume_text:
        conn = get_db()
        row = conn.execute(
            'SELECT resume_text FROM resume_analyses WHERE job_id=? AND user_id=? ORDER BY id DESC LIMIT 1',
            (resume_job_id, user['id']),
        ).fetchone()
        conn.close()
        resume_text = row['resume_text'] if row else ''

    if not resume_text:
        return {'success': False, 'message': 'Resume analysis not found. Please analyze the resume again.'}

    message = request.message.strip()
    if not message:
        return {'success': False, 'message': 'Please enter a question.'}

    chat_job_id = str(uuid.uuid4())
    chat_jobs[chat_job_id] = {'status': 'queued', 'chat_answer': None, 'message': None}
    asyncio.create_task(asyncio.to_thread(
        run_chatbot_job,
        chat_job_id,
        resume_text,
        message,
        request.history,
        request.page_context,
    ))
    return {'success': True, 'chat_job_id': chat_job_id, 'status': 'queued'}
# CHAT STATUS
# =========================================================

@app.get(
    "/chat/{chat_job_id}"
)
def get_chat(
    chat_job_id: str,
):

    job = chat_jobs.get(
        chat_job_id
    )

    if not job:

        return {
            "success": False,
            "status": "failed",
            "message": (
                "Chat job not found."
            ),
        }

    answer = job.get(
        "chat_answer"
    )

    return {
        "success": True,
        "status": job.get(
            "status"
        ),
        "answer": answer,
        "chat_answer": answer,
        "message": job.get(
            "message"
        ),
    }


# =========================================================
# CHECK ORIGINAL RESUME PHOTO
# =========================================================

@app.post(
    "/enhance-photo-status"
)
async def enhance_photo_status(
    job_id: str = Form(...),
    resume_file: UploadFile = File(...),
):

    job = ai_jobs.get(
        job_id
    )

    if not job:

        return {
            "success": False,
            "message": (
                "Resume analysis not found. Please analyze the resume again."
            ),
        }

    try:

        filename = (
            resume_file.filename
            or ""
        )

        data = await resume_file.read()

        if not data:

            return {
                "success": False,
                "message": (
                    "Resume file is empty."
                ),
            }

        photo_data = (
            await asyncio.to_thread(
                extract_embedded_profile_photo,
                filename,
                data,
            )
        )

        return {
            "success": True,
            "photo_detected": bool(
                photo_data
            ),
        }

    except Exception as exc:

        print(
            "Photo status error:",
            repr(exc),
        )

        return {
            "success": False,
            "message": (
                "Could not check the original resume photo."
            ),
        }


# =========================================================
# ENHANCE RESUME
# =========================================================

@app.post("/enhance")
async def enhance_resume(
    job_id: str = Form(...),
    resume_file: UploadFile | None = File(None),
    photo: UploadFile | None = File(None),
):

    job = ai_jobs.get(
        job_id
    )

    if not job:

        return {
            "success": False,
            "message": (
                "Resume analysis not found. Please analyze the resume again."
            ),
        }

    original_text = job.get(
        "resume_text"
    )

    if not original_text:

        return {
            "success": False,
            "message": (
                "Resume text is unavailable. Please analyze the resume again."
            ),
        }

    try:

        # -------------------------------------------------
        # ORIGINAL SCORE
        # -------------------------------------------------

        original_analysis = (
            analyze_resume_text(
                original_text
            )
        )

        original_score = int(
            original_analysis.get(
                "score",
                0,
            )
        )

        # -------------------------------------------------
        # AI ENHANCEMENT
        # -------------------------------------------------

        enhanced_text = (
            await asyncio.to_thread(
                generate_professional_resume_text,
                original_text,
            )
        )

        # -------------------------------------------------
        # ENHANCED SCORE
        # -------------------------------------------------

        enhanced_analysis = (
            analyze_resume_text(
                enhanced_text
            )
        )

        enhanced_score = int(
            enhanced_analysis.get(
                "score",
                0,
            )
        )

        # Never return an AI version
        # that scores lower.
        if (
            enhanced_score
            < original_score
        ):

            print(
                "Enhanced resume score dropped:",
                original_score,
                "->",
                enhanced_score,
            )

            enhanced_text = (
                original_text
            )

            enhanced_score = (
                original_score
            )

        # Keep the enhanced text available for instant template switching.
        ai_jobs.setdefault(job_id, {})["enhanced_text"] = enhanced_text

        # -------------------------------------------------
        # PHOTO
        # -------------------------------------------------

        photo_data = None
        photo_source = "none"

        # Priority 1:
        # original embedded photo.
        if resume_file:

            original_filename = (
                resume_file.filename
                or ""
            )

            original_file_data = (
                await resume_file.read()
            )

            if original_file_data:

                original_photo = (
                    await asyncio.to_thread(
                        extract_embedded_profile_photo,
                        original_filename,
                        original_file_data,
                    )
                )

                if original_photo:

                    photo_data = (
                        original_photo
                    )

                    photo_source = (
                        "original_resume"
                    )

        # Priority 2:
        # user-selected photo.
        if (
            not photo_data
            and photo
        ):

            photo_filename = (
                photo.filename
                or ""
            )

            photo_extension = (
                os.path.splitext(
                    photo_filename
                )[1].lower()
            )

            allowed_photo_extensions = {
                ".jpg",
                ".jpeg",
                ".png",
            }

            if (
                photo_extension
                in allowed_photo_extensions
            ):

                uploaded_photo_data = (
                    await photo.read()
                )

                validated_photo = (
                    validate_uploaded_photo(
                        uploaded_photo_data
                    )
                )

                if validated_photo:

                    photo_data = (
                        validated_photo
                    )

                    photo_source = (
                        "user_uploaded"
                    )

        ai_jobs.setdefault(job_id, {})["photo_data"] = photo_data

        # -------------------------------------------------
        # BUILD PDF
        # -------------------------------------------------

        pdf_bytes = (
            await asyncio.to_thread(
                build_final_resume_pdf,
                enhanced_text,
                photo_data,
                "professional",
            )
        )

        pdf_base64 = (
            base64.b64encode(
                pdf_bytes
            ).decode("ascii")
        )

        return {
            "success": True,

            "enhanced_resume": (
                enhanced_text
            ),

            "original_score": (
                original_score
            ),

            "enhanced_score": (
                enhanced_score
            ),

            "pdf_base64": (
                pdf_base64
            ),

            "filename": (
                "ResumeAI-Professional-Resume.pdf"
            ),

            "photo_included": bool(
                photo_data
            ),

            "photo_source": (
                photo_source
            ),

            "photo_data_url": photo_to_data_url(photo_data),
        }

    except Exception as exc:

        print(
            "Professional enhance error:",
            repr(exc),
        )

        return {
            "success": False,
            "message": (
                "Professional resume generation failed. Please try again."
            ),
        }


# =========================================================
# ENHANCE RESUME TEMPLATE SWITCHER
# =========================================================

@app.post("/enhance-template")
async def enhance_resume_template(
    job_id: str = Form(...),
    template: str = Form("professional"),
    enhanced_text: str = Form(""),
):
    allowed_templates = {"professional", "executive", "modern", "minimal"}
    template = (template or "professional").strip().lower()
    if template not in allowed_templates:
        return {"success": False, "message": "Unknown resume template."}

    job = ai_jobs.get(job_id) or {}
    text = (enhanced_text or job.get("enhanced_text") or "").strip()
    if not text:
        return {"success": False, "message": "Enhanced resume is not available. Please enhance the resume again."}

    photo_data = job.get("photo_data")

    try:
        pdf_bytes = await asyncio.to_thread(
            build_final_resume_pdf,
            text,
            photo_data,
            template,
        )
        return {
            "success": True,
            "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
            "filename": f"ResumeAI-{template}-Resume.pdf",
            "template": template,
        }
    except Exception as exc:
        print("Template generation error:", repr(exc))
        return {"success": False, "message": "Could not generate the selected resume style."}


# =========================================================
# OPTIONAL COMPATIBILITY FUNCTION
# =========================================================

def generate_enhanced_resume(
    resume_text: str,
) -> str:

    return generate_professional_resume_text(
        resume_text
    )


# =========================================================
# END
# =========================================================

# =========================================================
# REAL WORKSPACE FEATURES
# =========================================================
from auth import auth_router
from features import features_router

app.include_router(auth_router)
app.include_router(features_router)
