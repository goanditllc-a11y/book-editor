"""
app.py
Main Flask application for the Book Editor & Rater.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import webbrowser
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Resolve project root so imports work whether run directly or via PyInstaller
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from src import database as db
from src.file_parser import parse_file
from src.ai_detector import detect as ai_detect
from src.ai_editor import edit as ai_edit
from src.rater import rate as rate_text

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "book-editor-secret-key-change-me")

UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "epub", "docx", "txt"}
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 MB
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    recent = db.get_recent_books(5)
    stats = db.get_stats()
    return render_template("index.html", recent=recent, stats=stats)


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("index"))

    file = request.files["file"]
    if not file or file.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash(
            "Unsupported file type. Please upload PDF, EPUB, DOCX, or TXT.",
            "danger",
        )
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    tmp_path = UPLOAD_FOLDER / filename

    # Save to temp location for parsing
    file.save(str(tmp_path))
    file_size = tmp_path.stat().st_size

    try:
        parsed = parse_file(str(tmp_path), filename)
    except Exception as exc:  # noqa: BLE001
        flash(f"File parsing failed: {exc}", "danger")
        tmp_path.unlink(missing_ok=True)
        return redirect(url_for("index"))
    finally:
        # Remove temp file once parsed
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    if parsed.get("error"):
        flash(f"Parse error: {parsed['error']}", "danger")
        return redirect(url_for("index"))

    text = parsed["text"]
    if not text.strip():
        flash("The file appears to be empty or could not be read.", "warning")
        return redirect(url_for("index"))

    # Override title/author from form if provided
    title = request.form.get("title", "").strip() or parsed["title"]
    author = request.form.get("author", "").strip() or parsed["author"]
    file_type = filename.rsplit(".", 1)[1].upper()

    # AI detection
    try:
        detection = ai_detect(text)
    except Exception as exc:  # noqa: BLE001
        detection = {
            "ai_score": 0.0,
            "ai_percentage": 0,
            "confidence": "low",
            "components": {},
            "flagged_phrases": [],
            "ai_sentences": [],
        }
        flash(f"AI detection warning: {exc}", "warning")

    ai_score = detection["ai_score"]

    # Rating
    try:
        rating = rate_text(text, ai_score)
    except Exception as exc:  # noqa: BLE001
        rating = {
            "readability_stars": 2.5,
            "originality_stars": 2.5,
            "quality_stars": 2.5,
            "overall_rating": 2.5,
            "readability_metrics": {},
            "summary": "",
        }
        flash(f"Rating warning: {exc}", "warning")

    analysis_json = json.dumps(
        {
            "detection": detection,
            "rating": rating,
        },
        default=str,
    )

    book_id = db.insert_book(
        title=title or filename,
        author=author,
        file_type=file_type,
        original_text=text,
        word_count=parsed["word_count"],
        file_size=file_size,
        ai_score=ai_score,
        readability_score=rating["readability_stars"],
        originality_score=rating["originality_stars"],
        overall_rating=rating["overall_rating"],
        analysis_json=analysis_json,
    )

    flash(f'"{title or filename}" uploaded and analysed successfully!', "success")
    return redirect(url_for("book_detail", book_id=book_id))


@app.route("/library")
def library():
    page = max(1, request.args.get("page", 1, type=int))
    books, total = db.get_all_books(page=page, per_page=20)
    total_pages = max(1, (total + 19) // 20)
    return render_template(
        "library.html", books=books, page=page, total_pages=total_pages, total=total
    )


@app.route("/book/<int:book_id>")
def book_detail(book_id: int):
    book = db.get_book(book_id)
    if book is None:
        flash("Book not found.", "danger")
        return redirect(url_for("library"))

    analysis = {}
    if book.get("analysis_json"):
        try:
            analysis = json.loads(book["analysis_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    preview_text = (book.get("edited_text") or book.get("original_text") or "")[:2000]
    return render_template(
        "book.html",
        book=book,
        analysis=analysis,
        preview_text=preview_text,
    )


@app.route("/book/<int:book_id>/edit", methods=["POST"])
def edit_book(book_id: int):
    book = db.get_book(book_id)
    if book is None:
        flash("Book not found.", "danger")
        return redirect(url_for("library"))

    text = book.get("original_text") or ""
    if not text.strip():
        flash("No text content to edit.", "warning")
        return redirect(url_for("book_detail", book_id=book_id))

    ai_score = book.get("ai_score") or 0.5

    try:
        result = ai_edit(text, ai_score=ai_score)
    except Exception as exc:  # noqa: BLE001
        flash(f"Editing failed: {exc}", "danger")
        return redirect(url_for("book_detail", book_id=book_id))

    edited_text = result["edited_text"]
    new_ai_score = result["new_ai_score"]

    db.update_book_edit(book_id, edited_text, new_ai_score)

    # Re-run rating with new ai_score
    try:
        new_rating = rate_text(edited_text, new_ai_score)
        existing = {}
        if book.get("analysis_json"):
            existing = json.loads(book["analysis_json"])

        existing["edit_result"] = {
            "changes_made": result["changes_made"],
            "changes_list": result["changes_list"],
            "old_ai_score": ai_score,
            "new_ai_score": new_ai_score,
        }
        if "rating" in existing:
            existing["rating"].update(new_rating)

        db.update_book_analysis(
            book_id,
            new_ai_score,
            new_rating["readability_stars"],
            new_rating["originality_stars"],
            new_rating["overall_rating"],
            json.dumps(existing, default=str),
        )
    except Exception:  # noqa: BLE001
        pass

    flash(
        f"Auto-edit complete! {result['changes_made']} changes made. "
        f"AI score reduced from {round(ai_score*100)}% to {round(new_ai_score*100)}%.",
        "success",
    )
    return redirect(url_for("book_detail", book_id=book_id))


@app.route("/book/<int:book_id>/download")
def download_book(book_id: int):
    book = db.get_book(book_id)
    if book is None:
        flash("Book not found.", "danger")
        return redirect(url_for("library"))

    text = book.get("edited_text") or book.get("original_text") or ""
    if not text:
        flash("No content available to download.", "warning")
        return redirect(url_for("book_detail", book_id=book_id))

    # Write to a temp file and send it
    safe_title = secure_filename(book["title"] or f"book_{book_id}")
    suffix = "_edited" if book.get("is_edited") else "_original"
    out_filename = f"{safe_title}{suffix}.txt"
    out_path = UPLOAD_FOLDER / f"_download_{book_id}.txt"

    try:
        with open(out_path, "w", encoding="utf-8", errors="replace") as fh:
            fh.write(text)
        return send_file(
            str(out_path),
            as_attachment=True,
            download_name=out_filename,
            mimetype="text/plain",
        )
    except Exception as exc:  # noqa: BLE001
        flash(f"Download failed: {exc}", "danger")
        return redirect(url_for("book_detail", book_id=book_id))


@app.route("/book/<int:book_id>/delete", methods=["POST"])
def delete_book(book_id: int):
    book = db.get_book(book_id)
    if book is None:
        flash("Book not found.", "danger")
        return redirect(url_for("library"))

    title = book.get("title", "Unknown")
    db.delete_book(book_id)
    flash(f'"{title}" deleted.', "success")
    return redirect(url_for("library"))


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(413)
def too_large(_e):
    flash("File too large. Maximum size is 200 MB.", "danger")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _open_browser():
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    db.init_db()
    # Auto-open browser after a short delay
    threading.Timer(1.5, _open_browser).start()
    app.run(host="0.0.0.0", port=5000, debug=False)
