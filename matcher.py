
import re
import hashlib
import unicodedata
import streamlit as st
import numpy as np

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


# =========================================================
# AI MODEL
# =========================================================

@st.cache_resource
def load_ai_model():
    return SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )


# =========================================================
# SKILL DATABASE
# =========================================================

SKILL_ALIASES = {
    "Python": ["python"],
    "Java": ["java"],
    "C++": ["c++", "cpp"],
    "C": ["c language"],
    "JavaScript": ["javascript", "js"],
    "TypeScript": ["typescript"],
    "SQL": ["sql", "structured query language"],
    "MySQL": ["mysql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MongoDB": ["mongodb", "mongo db"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3"],
    "React": ["react.js", "reactjs", "react"],
    "Node.js": ["node.js", "nodejs"],
    "Express": ["express.js", "expressjs"],
    "Django": ["django"],
    "Flask": ["flask"],
    "FastAPI": ["fastapi"],
    "Streamlit": ["streamlit"],
    "Machine Learning": ["machine learning"],
    "Deep Learning": ["deep learning"],
    "Artificial Intelligence": ["artificial intelligence", "ai"],
    "NLP": ["natural language processing", "nlp"],
    "Generative AI": ["generative ai", "genai", "gen ai"],
    "LLM": ["large language model", "llm", "llms"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch"],
    "Scikit-learn": ["scikit-learn", "sklearn"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Matplotlib": ["matplotlib"],
    "Seaborn": ["seaborn"],
    "Power BI": ["power bi"],
    "Tableau": ["tableau"],
    "Excel": ["microsoft excel", "excel"],
    "Data Analysis": ["data analysis", "data analytics"],
    "Data Science": ["data science"],
    "Data Visualization": ["data visualization"],
    "Statistics": ["statistics", "statistical analysis"],
    "Deep Neural Networks": ["neural networks", "deep neural networks"],
    "Computer Vision": ["computer vision"],
    "OpenCV": ["opencv"],
    "Git": ["git", "github"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes"],
    "AWS": ["amazon web services", "aws"],
    "Azure": ["microsoft azure", "azure"],
    "Google Cloud": ["google cloud", "gcp"],
    "Linux": ["linux"],
    "Agile": ["agile"],
    "REST API": ["rest api", "restful api"],
    "Data Structures": ["data structures", "dsa"],
    "Algorithms": ["algorithms"],
    "OOP": ["object oriented programming", "oop"],
    "Problem Solving": ["problem solving"],
}


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(text):
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Preserve line breaks for section detection.
    lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in text.split("\n")
    ]

    return "\n".join(line for line in lines if line).strip()


def normalize_text(text):
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9+#.\n ]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def normalize_heading(text):
    text = normalize_text(text)
    text = re.sub(r"^[\W\d]+", "", text)
    text = re.sub(r"[:\-]+$", "", text)

    return text.strip()


# =========================================================
# PDF TEXT EXTRACTION
# =========================================================

def extract_pdf_text(uploaded_file):
    try:
        uploaded_file.seek(0)

        reader = PdfReader(uploaded_file)

        if reader.is_encrypted:
            try:
                result = reader.decrypt("")
                if result == 0:
                    return ""
            except Exception:
                return ""

        pages_text = []

        for page in reader.pages:
            page_text = page.extract_text() or ""

            if page_text.strip():
                pages_text.append(page_text)

        uploaded_file.seek(0)

        return clean_text("\n".join(pages_text))

    except Exception:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        return ""


# =========================================================
# SKILL EXTRACTION
# =========================================================

def contains_keyword(text, keyword):
    normalized_text = normalize_text(text)
    normalized_keyword = normalize_text(keyword)

    if not normalized_keyword:
        return False

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(normalized_keyword)
        + r"(?![a-z0-9])"
    )

    return bool(re.search(pattern, normalized_text))


def extract_skills(text):
    found_skills = []

    normalized_text = normalize_text(text)

    for skill, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            if contains_keyword(normalized_text, alias):
                found_skills.append(skill)
                break

    return sorted(set(found_skills))


# =========================================================
# RESUME ID
# =========================================================

def create_resume_id(text):
    normalized = normalize_text(text)

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()[:16]


# =========================================================
# SECTION DETECTION
# =========================================================

PROJECT_HEADINGS = {
    "projects",
    "personal projects",
    "academic projects",
    "key projects",
    "project experience",
    "projects undertaken",
    "academic project",
    "major projects"
}

EXPERIENCE_HEADINGS = {
    "experience",
    "work experience",
    "professional experience",
    "employment history",
    "internship",
    "internships",
    "work history",
    "professional background"
}

OTHER_HEADINGS = {
    "education",
    "skills",
    "technical skills",
    "certifications",
    "certificates",
    "achievements",
    "awards",
    "languages",
    "interests",
    "summary",
    "profile",
    "objective",
    "contact",
    "personal details",
    "declaration",
    "references",
    "technical expertise",
    "career objective"
}


def detect_sections(text):
    lines = [
        line.strip()
        for line in str(text).splitlines()
        if line.strip()
    ]

    sections = {
        "projects": [],
        "experience": []
    }

    current_section = None

    for line in lines:
        heading = normalize_heading(line)

        if heading in PROJECT_HEADINGS:
            current_section = "projects"
            continue

        if heading in EXPERIENCE_HEADINGS:
            current_section = "experience"
            continue

        if heading in OTHER_HEADINGS:
            current_section = None
            continue

        # Detect headings with simple trailing content.
        heading_match = re.match(
            r"^(projects|work experience|professional experience|"
            r"internship|education|technical skills)\s*[:\-]\s*(.*)$",
            heading
        )

        if heading_match:
            matched_heading = heading_match.group(1)
            remaining_text = heading_match.group(2)

            if matched_heading == "projects":
                current_section = "projects"
            elif matched_heading in {
                "work experience",
                "professional experience",
                "internship"
            }:
                current_section = "experience"
            else:
                current_section = None

            if current_section and remaining_text:
                sections[current_section].append(remaining_text)

            continue

        if current_section:
            sections[current_section].append(line)

    return {
        "projects": clean_text(" ".join(sections["projects"])),
        "experience": clean_text(" ".join(sections["experience"]))
    }


# =========================================================
# SEMANTIC SIMILARITY
# =========================================================

def get_embedding(text, model):
    text = clean_text(text)

    if not text:
        return None

    # Limit input length to control processing time.
    text = text[:12000]

    embedding = model.encode(
        text,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    return embedding


def calculate_semantic_score(text1, text2, model):
    if not text1 or not text2:
        return 0.0

    try:
        embedding1 = get_embedding(text1, model)
        embedding2 = get_embedding(text2, model)

        if embedding1 is None or embedding2 is None:
            return 0.0

        similarity = float(np.dot(embedding1, embedding2))

        score = max(0.0, similarity) * 100

        return round(min(score, 100), 2)

    except Exception:
        return 0.0


# =========================================================
# SKILL MATCHING
# =========================================================

def calculate_skill_score(job_skills, resume_skills):
    if not job_skills:
        return 0.0, [], []

    matched = sorted(
        set(job_skills).intersection(set(resume_skills))
    )

    missing = sorted(
        set(job_skills).difference(set(resume_skills))
    )

    score = (len(matched) / len(job_skills)) * 100

    return round(score, 2), matched, missing


# =========================================================
# FINAL MATCH SCORE
# =========================================================

def calculate_final_score(
    semantic_score,
    skill_score,
    project_score,
    experience_score,
    job_skills_exist,
    project_detected,
    experience_detected
):
    components = [(semantic_score, 65)]

    if job_skills_exist:
        components.append((skill_score, 20))

    if project_detected:
        components.append((project_score, 7.5))

    if experience_detected:
        components.append((experience_score, 7.5))

    total_weight = sum(weight for _, weight in components)

    if total_weight <= 0:
        return 0.0

    final_score = sum(
        score * weight
        for score, weight in components
    ) / total_weight

    return round(max(0.0, min(final_score, 100.0)), 2)


# =========================================================
# MAIN RESUME MATCHER
# =========================================================

def match_resumes(job_description, uploaded_files):

    job_description = clean_text(job_description)

    if not job_description or not uploaded_files:
        return []

    model = load_ai_model()

    job_skills = extract_skills(job_description)

    results = []
    seen_resume_ids = set()

    duplicate_count = 0
    unreadable_count = 0

    duplicate_files = []
    unreadable_files = []

    total_files = len(uploaded_files)

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        job_embedding = get_embedding(job_description, model)

        for index, uploaded_file in enumerate(uploaded_files):

            filename = getattr(
                uploaded_file,
                "name",
                f"Resume_{index + 1}.pdf"
            )

            status_text.text(
                f"Analysing resume {index + 1} of {total_files}..."
            )

            resume_text = extract_pdf_text(uploaded_file)

            # Skip unreadable or nearly empty PDFs.
            if len(resume_text.strip()) < 30:
                unreadable_count += 1
                unreadable_files.append(filename)

                progress_bar.progress(
                    (index + 1) / total_files
                )
                continue

            resume_id = create_resume_id(resume_text)

            # Skip exact duplicate resume content.
            if resume_id in seen_resume_ids:
                duplicate_count += 1
                duplicate_files.append(filename)

                progress_bar.progress(
                    (index + 1) / total_files
                )
                continue

            seen_resume_ids.add(resume_id)

            candidate_name = filename.rsplit(".", 1)[0]

            resume_skills = extract_skills(resume_text)

            sections = detect_sections(resume_text)

            projects_text = sections["projects"]
            experience_text = sections["experience"]

            project_detected = len(projects_text) > 20
            experience_detected = len(experience_text) > 20

            resume_embedding = get_embedding(
                resume_text,
                model
            )

            if (
                job_embedding is not None
                and resume_embedding is not None
            ):
                similarity = float(
                    np.dot(job_embedding, resume_embedding)
                )

                semantic_score = round(
                    max(0.0, similarity) * 100,
                    2
                )
            else:
                semantic_score = 0.0

            skill_score, matched_skills, missing_skills = (
                calculate_skill_score(
                    job_skills,
                    resume_skills
                )
            )

            if project_detected:
                project_score = calculate_semantic_score(
                    job_description,
                    projects_text,
                    model
                )
            else:
                project_score = 0.0

            if experience_detected:
                experience_score = calculate_semantic_score(
                    job_description,
                    experience_text,
                    model
                )
            else:
                experience_score = 0.0

            match_score = calculate_final_score(
                semantic_score=semantic_score,
                skill_score=skill_score,
                project_score=project_score,
                experience_score=experience_score,
                job_skills_exist=bool(job_skills),
                project_detected=project_detected,
                experience_detected=experience_detected
            )

            score_reasons = []

            if matched_skills:
                score_reasons.append(
                    "Matched skills: " +
                    ", ".join(matched_skills)
                )

            if missing_skills:
                score_reasons.append(
                    "Missing skills: " +
                    ", ".join(missing_skills)
                )

            score_reasons.append(
                "Project section detected"
                if project_detected
                else "Project section not detected"
            )

            score_reasons.append(
                "Experience section detected"
                if experience_detected
                else "Experience section not detected"
            )

            result = {
                "candidate": candidate_name,
                "filename": filename,
                "resume_id": resume_id,

                "match_score": match_score,
                "semantic_score": semantic_score,
                "skill_score": skill_score,
                "project_score": project_score,
                "experience_score": experience_score,

                "project_detected": project_detected,
                "experience_detected": experience_detected,

                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "extracted_skills": resume_skills,

                "extracted_text": resume_text,
                "projects_text": projects_text,
                "experience_text": experience_text,

                "total_skills": len(job_skills),
                "matched_count": len(matched_skills),
                "missing_count": len(missing_skills),

                "score_reasons": score_reasons,
                "job_skills": job_skills,

                "duplicate_count": 0,
                "unreadable_count": 0,

                "duplicate_files": [],
                "unreadable_files": []
            }

            results.append(result)

            progress_bar.progress(
                (index + 1) / total_files
            )

        results.sort(
            key=lambda item: item["match_score"],
            reverse=True
        )

        # Attach batch-level processing information.
        for result in results:
            result["duplicate_count"] = duplicate_count
            result["unreadable_count"] = unreadable_count
            result["duplicate_files"] = duplicate_files
            result["unreadable_files"] = unreadable_files

        status_text.success(
            f"Analysis complete. {len(results)} readable unique "
            f"resumes processed."
        )

        return results

    except Exception:
        status_text.error(
            "Resume analysis failed. Please check the uploaded PDFs "
            "and try again."
        )
        raise
