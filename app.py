"""
app.py - the web server. It shows the pages and connects them to analyzer.py.

Run it with:  python app.py
Then open:    http://127.0.0.1:5000

The web pages (HTML) and the colors (CSS) are all inside this one file,
so there are no folders to upload. Easy to do from a phone!
"""

import os
from flask import Flask, render_template_string, request, redirect, url_for, flash
from analyzer import extract_text, analyze_resume, ROLE_KEYWORDS
from database import init_db, save_analysis, get_analysis

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret")  # needed for error messages
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB maximum file size

init_db()  # create the database table if it does not exist yet


# ---------- COLORS AND LAYOUT (CSS) ----------
STYLE = """
body { margin: 0; font-family: Arial, Helvetica, sans-serif; background: linear-gradient(135deg, #eef2ff, #f5f3ff); color: #1f2937; min-height: 100vh; }
main { max-width: 900px; margin: 40px auto; padding: 0 16px; }
.card, .score-box { background: #fff; border-radius: 14px; padding: 24px; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08); margin-bottom: 20px; }
h1 { margin-top: 0; color: #4c1d95; }
.subtitle { color: #6b7280; }
label { display: block; font-weight: bold; margin: 18px 0 6px; }
input[type=file], select { width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; }
button { margin-top: 24px; width: 100%; padding: 14px; font-size: 16px; background: #7c3aed; color: #fff; border: none; border-radius: 8px; cursor: pointer; }
.alert { background: #fee2e2; color: #991b1b; padding: 12px; border-radius: 8px; margin-bottom: 16px; }
.scores { display: flex; gap: 16px; flex-wrap: wrap; }
.score-box { flex: 1; min-width: 160px; text-align: center; margin-bottom: 0; }
.big { font-size: 48px; font-weight: bold; color: #7c3aed; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.chip { padding: 6px 12px; border-radius: 999px; font-size: 14px; }
.good { background: #dcfce7; color: #166534; }
.bad { background: #fee2e2; color: #991b1b; }
.neutral { background: #e0e7ff; color: #3730a3; }
a { color: #6d28d9; }
"""

# ---------- PAGE 1: UPLOAD FORM (HTML) ----------
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Smart Resume Analyzer</title>
  <style>{{ style|safe }}</style>
</head>
<body>
<main>
  <div class="card">
    <h1>Smart Resume Analyzer</h1>
    <p class="subtitle">Upload your resume (PDF or DOCX) and get a score, an ATS check and smart tips.</p>

    {% with messages = get_flashed_messages() %}
      {% for message in messages %}
        <div class="alert">{{ message }}</div>
      {% endfor %}
    {% endwith %}

    <form action="{{ url_for('analyze') }}" method="post" enctype="multipart/form-data">
      <label for="resume">1. Choose your resume</label>
      <input type="file" id="resume" name="resume" accept=".pdf,.docx" required>

      <label for="role">2. Choose your target job role</label>
      <select id="role" name="role">
        {% for role in roles %}
          <option value="{{ role }}">{{ role }}</option>
        {% endfor %}
      </select>

      <button type="submit">Analyze my resume</button>
    </form>
  </div>
</main>
</body>
</html>
"""

# ---------- PAGE 2: RESULTS DASHBOARD (HTML) ----------
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Results - Smart Resume Analyzer</title>
  <style>{{ style|safe }}</style>
  <!-- Chart.js draws the bar chart (loaded from the internet) -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
</head>
<body>
<main>
  <p><a href="{{ url_for('index') }}">&larr; Analyze another resume</a></p>

  {% set r = record.result %}
  <h1>Results for {{ record.filename }}</h1>
  <p>Target role: <strong>{{ r.role }}</strong> &middot; Analyzed on {{ record.created_at }}</p>

  <!-- Big score boxes -->
  <section class="scores">
    <div class="score-box">
      <div class="big">{{ r.score }}</div>
      <div>Resume score (out of 100)</div>
    </div>
    <div class="score-box">
      <div class="big">{{ r.ats.score }}</div>
      <div>ATS compatibility (out of 100)</div>
    </div>
    <div class="score-box">
      <div class="big">{{ r.ats.keyword_percent }}%</div>
      <div>Role keywords matched</div>
    </div>
  </section>

  <section class="card">
    <h2>Score breakdown</h2>
    <canvas id="breakdownChart"></canvas>
  </section>

  <section class="card">
    <h2>Skills for {{ r.role }}</h2>
    <h3>You have</h3>
    <div class="chips">
      {% for skill in r.ats.found %}<span class="chip good">{{ skill }}</span>
      {% else %}<p>None of the key skills were found.</p>{% endfor %}
    </div>
    <h3>Missing</h3>
    <div class="chips">
      {% for skill in r.ats.missing %}<span class="chip bad">{{ skill }}</span>
      {% else %}<p>You have all the key skills. Great job!</p>{% endfor %}
    </div>
  </section>

  <section class="card">
    <h2>Improvement suggestions</h2>
    <ul>
      {% for tip in r.suggestions %}<li>{{ tip }}</li>
      {% else %}<li>Your resume looks strong. Keep it updated!</li>{% endfor %}
    </ul>
  </section>

  <section class="card">
    <h2>Most common words in your resume</h2>
    <div class="chips">
      {% for word in r.top_words %}<span class="chip neutral">{{ word }}</span>{% endfor %}
    </div>
  </section>
</main>

<script>
  new Chart(document.getElementById('breakdownChart'), {
    type: 'bar',
    data: {
      labels: [{% for item in r.breakdown %}{{ item.name|tojson }}{% if not loop.last %}, {% endif %}{% endfor %}],
      datasets: [{
        label: 'Points earned',
        data: [{% for item in r.breakdown %}{{ item.points }}{% if not loop.last %}, {% endif %}{% endfor %}],
        backgroundColor: '#7c3aed'
      }]
    },
    options: { scales: { y: { beginAtZero: true, max: 20 } } }
  });
</script>
</body>
</html>
"""


# ---------- ROUTES (what happens when a page is opened) ----------
@app.route("/")
def index():
    return render_template_string(INDEX_HTML, style=STYLE, roles=list(ROLE_KEYWORDS.keys()))


@app.route("/analyze", methods=["POST"])
def analyze():
    uploaded = request.files.get("resume")
    role = request.form.get("role", "Web Developer")

    # Step 1: check that a valid file was uploaded
    if uploaded is None or uploaded.filename == "":
        flash("Please choose a file first.")
        return redirect(url_for("index"))
    if not uploaded.filename.lower().endswith((".pdf", ".docx")):
        flash("Only PDF or DOCX files are allowed.")
        return redirect(url_for("index"))

    # Step 2: read the text from the file
    try:
        text = extract_text(uploaded.filename, uploaded.read())
    except Exception:
        flash("Sorry, we could not read that file. Try saving it again as a PDF or DOCX.")
        return redirect(url_for("index"))
    if len(text.strip()) < 50:
        flash("We found almost no text in that file. Scanned images are not supported yet.")
        return redirect(url_for("index"))

    # Step 3: analyze the resume and save the result
    result = analyze_resume(text, role)
    analysis_id = save_analysis(uploaded.filename, text, result)
    return redirect(url_for("dashboard", analysis_id=analysis_id))


@app.route("/dashboard/<int:analysis_id>")
def dashboard(analysis_id):
    record = get_analysis(analysis_id)
    if record is None:
        flash("That analysis was not found.")
        return redirect(url_for("index"))
    return render_template_string(DASHBOARD_HTML, style=STYLE, record=record)


if __name__ == "__main__":
    app.run(debug=True)
