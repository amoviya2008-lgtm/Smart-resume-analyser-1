"""
database.py - saves each analysis in a small SQLite database file.
SQLite comes built into Python, so there is nothing extra to install.
"""

import json
import sqlite3
from datetime import datetime

DB_FILE = "resume_analyzer.db"


def _run(sql, params=()):
    """Open the database, run one SQL command, save the change, and close it."""
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row  # lets us use names like row["filename"]
    try:
        cursor = connection.execute(sql, params)
        connection.commit()
        return cursor.fetchone(), cursor.lastrowid
    finally:
        connection.close()


def init_db():
    """Create the table the first time the app runs."""
    _run("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            role TEXT,
            score INTEGER,
            ats_score INTEGER,
            resume_text TEXT,
            result_json TEXT,
            created_at TEXT
        )
    """)


def save_analysis(filename, resume_text, result):
    """Save one analysis and return its id number."""
    _, new_id = _run(
        "INSERT INTO analyses (filename, role, score, ats_score, resume_text, result_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (filename, result["role"], result["score"], result["ats"]["score"],
         resume_text, json.dumps(result), datetime.now().strftime("%d %b %Y, %I:%M %p")),
    )
    return new_id


def get_analysis(analysis_id):
    """Get one saved analysis by its id. Returns None if it does not exist."""
    row, _ = _run("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
    if row is None:
        return None
    record = dict(row)
    record["result"] = json.loads(record["result_json"])
    return record
