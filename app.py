"""Provenance Guard — Flask application.

M3: POST /submit runs Signal 1 (LLM classification) and writes an audit log
entry. Stylometrics, combined scoring, transparency labels, and appeals are
added in later milestones (see planning.md).
"""

import json
import os
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request

from signals.llm_signal import classify_with_llm

app = Flask(__name__)

AUDIT_LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_log.json")


def _attribution_for(score: float) -> str:
    """Map a confidence score to an attribution bucket (see planning.md)."""
    if score >= 0.75:
        return "likely_ai"
    if score <= 0.40:
        return "likely_human"
    return "uncertain"


def _read_audit_log() -> list:
    """Return all audit log entries, or an empty list if none exist yet."""
    try:
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def write_audit_entry(entry: dict) -> None:
    """Append a structured entry to audit_log.json."""
    entries = _read_audit_log()
    entries.append(entry)
    with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


@app.route("/submit", methods=["POST"])
def submit():
    """Accept content, run Signal 1, log the result, and return a verdict.

    Expects JSON (or form) with `text` and `creator_id`.
    """
    data = request.get_json(silent=True) or request.form

    text = (data.get("text") or "").strip()
    creator_id = (data.get("creator_id") or "").strip()

    if not text:
        return jsonify({"error": "field 'text' is required and must not be empty"}), 400
    if not creator_id:
        return jsonify({"error": "field 'creator_id' is required"}), 400

    llm_score = classify_with_llm(text)
    attribution = _attribution_for(llm_score)

    content_id = str(uuid.uuid4())
    # TODO(M4): combine with stylometric signal via the 0.7/0.3 weighted formula.
    # TODO(M5): generate the real transparency label text.
    label = "Attribution label pending (M5)"

    entry = {
        "content_id": content_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "creator_id": creator_id,
        "text": text,
        "llm_score": llm_score,
        "confidence": llm_score,
        "attribution": attribution,
        "label": label,
        "status": "classified",
    }
    write_audit_entry(entry)

    return jsonify(
        {
            "content_id": content_id,
            "attribution": attribution,
            "confidence": llm_score,
            "label": label,
        }
    )


@app.route("/log", methods=["GET"])
def log():
    """Return all audit log entries."""
    return jsonify({"entries": _read_audit_log()})


if __name__ == "__main__":
    app.run(debug=True)
