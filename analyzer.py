"""
analyzer.py - the brain of the Smart Resume Analyzer.

This one file does the four jobs from the project modules:
  1. extract_text()       -> read the text inside a PDF or DOCX    (Module 1)
  2. score_resume()       -> give the resume a score out of 100    (Module 2)
  3. check_ats()          -> compare the resume with a job role    (Module 3)
  4. build_suggestions()  -> write improvement tips                (Module 4)

analyze_resume() runs all of them and returns one result dictionary.
"""

import io
import re
from collections import Counter

# ----- Job roles and the keywords employers look for (Module 3) -----
# Want another role? Just add a new line here.
ROLE_KEYWORDS = {
    "Data Analyst": ["python", "sql", "excel", "pandas", "numpy",
                     "tableau", "power bi", "data visualization", "statistics", "data cleaning"],
    "Web Developer": ["html", "css", "javascript", "react", "node.js",
                      "flask", "bootstrap", "tailwind", "git", "rest api"],
    "AI Engineer": ["python", "machine learning", "nlp", "spacy", "nltk",
                    "scikit-learn", "tensorflow", "pandas", "deep learning", "git"],
    "Cloud Engineer": ["aws", "azure", "docker", "kubernetes", "linux",
                       "terraform", "ci/cd", "python", "networking", "git"],
}

# ----- Words that usually appear as section headings (Module 2) -----
SECTION_WORDS = {
    "skills": ["skills", "technical skills", "core skills", "core competencies"],
    "education": ["education", "academic background", "academics"],
    "projects": ["projects", "project experience", "academic projects"],
    "experience": ["experience", "work experience", "internship", "internships"],
    "certifications": ["certifications", "certificates", "courses"],
    "summary": ["summary", "objective", "profile"],
}

# Very common words we ignore when counting "important words" (basic NLP)
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "have", "has", "been", "will", "using", "used", "also", "able",
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


# ===================== MODULE 1: READ THE FILE =====================
def extract_text(filename, file_bytes):
    """Return all the text inside a PDF or DOCX file."""
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        from docx import Document
        document = Document(io.BytesIO(file_bytes))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError("Only PDF and DOCX files are supported.")


# ===================== MODULE 2: SCORE THE RESUME =====================
def has_section(text, words):
    """True if a line of the resume looks like one of these section headings."""
    for line in text.lower().splitlines():
        clean = line.strip(" :-*|").strip()
        if clean in words or (len(clean) < 30 and any(clean.startswith(w) for w in words)):
            return True
    return False


def has_phone(text):
    """True if we find a phone-like number with at least 10 digits."""
    for candidate in re.findall(r"\+?\d[\d\s()-]{8,}\d", text):
        if len(re.sub(r"\D", "", candidate)) >= 10:
            return True
    return False


def score_resume(text):
    """Check 6 areas of the resume. Returns a list with the points for each area."""
    found = [name for name, words in SECTION_WORDS.items() if has_section(text, words)]
    word_count = len(text.split())
    email = bool(EMAIL_RE.search(text))
    phone = has_phone(text)

    if 300 <= word_count <= 800:
        length_points = 10
    elif 150 <= word_count <= 1000:
        length_points = 5
    else:
        length_points = 0
    section_points = 10 if len(found) >= 4 else (5 if len(found) >= 3 else 0)

    return [
        {"name": "Contact info", "max": 15,
         "points": (8 if email else 0) + (7 if phone else 0),
         "tip": "Add your email AND phone number at the top of the resume."},
        {"name": "Skills section", "max": 20,
         "points": 20 if "skills" in found else 0,
         "tip": "Add a clear 'Skills' section that lists your technical tools."},
        {"name": "Education", "max": 15,
         "points": 15 if "education" in found else 0,
         "tip": "Add an 'Education' section with your degree, college and year."},
        {"name": "Projects", "max": 20,
         "points": 20 if "projects" in found else 0,
         "tip": "Add a 'Projects' section with 2 or more projects, the tools used and the results."},
        {"name": "Experience", "max": 10,
         "points": 10 if "experience" in found else 0,
         "tip": "Add internship, freelance or volunteer work. Academic projects also count."},
        {"name": "Structure and length", "max": 20,
         "points": length_points + section_points,
         "tip": "Aim for 300 to 800 words and at least 4 clear sections."},
    ]


# ===================== MODULE 3: ATS KEYWORD CHECK =====================
def find_keywords(text, keywords):
    """Return the keywords that appear in the text as whole words."""
    lowered = text.lower()
    found = []
    for keyword in keywords:
        pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
        if re.search(pattern, lowered):
            found.append(keyword)
    return found


def check_ats(text, role):
    """Compare the resume with the keywords for one job role."""
    keywords = ROLE_KEYWORDS[role]
    found = find_keywords(text, keywords)
    missing = [k for k in keywords if k not in found]
    keyword_percent = round(len(found) / len(keywords) * 100)

    # ATS software also likes simple, clean formatting
    format_points = 0
    if len(text.strip()) > 200:
        format_points += 30
    if sum(has_section(text, words) for words in SECTION_WORDS.values()) >= 3:
        format_points += 40
    if EMAIL_RE.search(text):
        format_points += 15
    if has_phone(text):
        format_points += 15

    # Final ATS score: keywords count 70%, formatting counts 30%
    ats_score = round(0.7 * keyword_percent + 0.3 * format_points)
    return {
        "score": ats_score,
        "keyword_percent": keyword_percent,
        "found": found,
        "missing": missing,
        "format_points": format_points,
    }


def top_keywords(text, count=10):
    """Basic NLP: split the text into words, drop common words, count the rest."""
    words = re.findall(r"[a-z][a-z+#]{2,}", text.lower())
    counts = Counter(word for word in words if word not in STOPWORDS)
    return [word for word, _ in counts.most_common(count)]


# ===================== MODULE 4: SMART SUGGESTIONS =====================
def build_suggestions(text, role, breakdown, ats):
    """Create a list of tips based on what is weak or missing."""
    tips = [item["tip"] for item in breakdown if item["points"] < item["max"]]

    if not has_section(text, SECTION_WORDS["certifications"]):
        tips.append("Add certifications (for example from Coursera, NPTEL or AWS) to show you keep learning.")
    if ats["missing"]:
        skills = ", ".join(ats["missing"][:4])
        tips.append(f"For a {role} job, consider learning and adding: {skills}. Only add skills you really know.")
    if ats["format_points"] < 70:
        tips.append("Use plain text and simple headings. Avoid tables, images and multi-column designs, "
                    "because ATS software can misread them.")
    return tips[:8]


# ===================== PUT EVERYTHING TOGETHER =====================
def analyze_resume(text, role):
    """Run all the checks and return one result dictionary."""
    if role not in ROLE_KEYWORDS:
        role = "Web Developer"
    breakdown = score_resume(text)
    total = sum(item["points"] for item in breakdown)
    ats = check_ats(text, role)
    return {
        "role": role,
        "score": total,
        "breakdown": breakdown,
        "ats": ats,
        "suggestions": build_suggestions(text, role, breakdown, ats),
        "top_words": top_keywords(text),
        "word_count": len(text.split()),
  }
