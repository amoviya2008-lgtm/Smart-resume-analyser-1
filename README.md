# Smart Resume Analyzer with AI-Based Feedback

An AI-powered web app that scores a student's resume out of 100, checks ATS keywords for a chosen job role, lists missing skills, and gives improvement suggestions on a dashboard.

Live app: https://smart-resume-analyser-1-hzyc.onrender.com

## Files
- app.py: web pages and routes (Flask)
- analyzer.py: scoring, ATS keyword check, suggestions
- database.py: saves results (SQLite)
- requirements.txt: libraries to install
- Procfile: start command for deployment
- sample_resume.txt: sample resume for testing

## Run on a computer
1. Install Python 3.10 or newer.
2. Run: pip install -r requirements.txt
3. Run: python app.py
4. Open http://127.0.0.1:5000

## How it works
1. The user uploads a PDF or DOCX resume.
2. The text is extracted from the file.
3. The resume is scored out of 100 (contact, skills, education, projects, experience, structure).
4. Role keywords are matched (70% of the ATS score) and formatting is checked (30%).
5. Suggestions are generated and shown on the dashboard.

## Deployment (Render)
- Build command: pip install -r requirements.txt
- Start command: gunicorn --bind 0.0.0.0:$PORT app:app

## Limitations
Works only with text-based PDF and DOCX files. Matching is rule-based.
