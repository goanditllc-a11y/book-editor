"""
src/database.py
SQLite database operations using Python's built-in sqlite3 module.
Handles storage of books and their analysis results.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "book_editor.db")
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    file_type TEXT,
    original_text TEXT,
    edited_text TEXT,
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    word_count INTEGER,
    ai_score REAL,
    readability_score REAL,
    originality_score REAL,
    overall_rating REAL,
    is_edited BOOLEAN DEFAULT 0,
    file_size INTEGER,
    text_stored_on_disk BOOLEAN DEFAULT 0,
    analysis_json TEXT
);
"""


def get_connection():
    """Return a sqlite3 connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't already exist."""
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Text storage helpers
# ---------------------------------------------------------------------------

def _text_file_path(book_id: int, kind: str) -> str:
    """Return path for on-disk text file (kind = 'original' or 'edited')."""
    return os.path.join(UPLOADS_DIR, f"{book_id}_{kind}.txt")


def _store_text(book_id: int, text: str, kind: str) -> bool:
    """
    Store text on disk if it is large (>500 KB).
    Returns True when text was saved to disk, False when stored in-DB.
    """
    if len(text.encode("utf-8", errors="replace")) > 500 * 1024:
        path = _text_file_path(book_id, kind)
        with open(path, "w", encoding="utf-8", errors="replace") as fh:
            fh.write(text)
        return True
    return False


def _load_text(book_id: int, db_text: str | None, kind: str) -> str:
    """
    Load text: from disk if the on-disk file exists, otherwise from db_text.
    """
    path = _text_file_path(book_id, kind)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            pass
    return db_text or ""


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def insert_book(
    title: str,
    author: str,
    file_type: str,
    original_text: str,
    word_count: int,
    file_size: int,
    ai_score: float = 0.0,
    readability_score: float = 0.0,
    originality_score: float = 0.0,
    overall_rating: float = 0.0,
    analysis_json: str = "",
) -> int:
    """Insert a new book and return its id."""
    conn = get_connection()
    try:
        # Insert with placeholder text so we get the id first
        cursor = conn.execute(
            """
            INSERT INTO books
                (title, author, file_type, word_count, file_size,
                 ai_score, readability_score, originality_score,
                 overall_rating, analysis_json, upload_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                author,
                file_type,
                word_count,
                file_size,
                ai_score,
                readability_score,
                originality_score,
                overall_rating,
                analysis_json,
                datetime.utcnow().isoformat(sep=" ", timespec="seconds"),
            ),
        )
        book_id = cursor.lastrowid

        # Decide where to store the text
        on_disk = _store_text(book_id, original_text, "original")
        if on_disk:
            conn.execute(
                "UPDATE books SET text_stored_on_disk=1 WHERE id=?", (book_id,)
            )
        else:
            conn.execute(
                "UPDATE books SET original_text=? WHERE id=?",
                (original_text, book_id),
            )

        conn.commit()
        return book_id
    finally:
        conn.close()


def get_book(book_id: int) -> dict | None:
    """Return a book as a plain dict, with texts loaded from disk if needed."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if row is None:
            return None
        book = dict(row)
        book["original_text"] = _load_text(
            book_id, book.get("original_text"), "original"
        )
        book["edited_text"] = _load_text(book_id, book.get("edited_text"), "edited")
        return book
    finally:
        conn.close()


def get_all_books(page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
    """Return (books, total_count) for the given page (1-indexed)."""
    offset = (page - 1) * per_page
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        rows = conn.execute(
            """
            SELECT id, title, author, file_type, word_count, ai_score,
                   overall_rating, upload_date, is_edited, file_size
            FROM books
            ORDER BY upload_date DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        ).fetchall()
        return [dict(r) for r in rows], total
    finally:
        conn.close()


def get_recent_books(limit: int = 5) -> list[dict]:
    """Return the most recently uploaded books (no text fields)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, title, author, file_type, word_count, ai_score,
                   overall_rating, upload_date, is_edited
            FROM books ORDER BY upload_date DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_stats() -> dict:
    """Return aggregate statistics."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_books,
                COALESCE(AVG(ai_score), 0) AS avg_ai_score,
                COALESCE(AVG(overall_rating), 0) AS avg_rating
            FROM books
            """
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def update_book_edit(book_id: int, edited_text: str, new_ai_score: float) -> None:
    """Persist edited text and updated AI score."""
    conn = get_connection()
    try:
        on_disk = _store_text(book_id, edited_text, "edited")
        if not on_disk:
            conn.execute(
                "UPDATE books SET edited_text=? WHERE id=?", (edited_text, book_id)
            )
        conn.execute(
            """
            UPDATE books
            SET is_edited=1,
                ai_score=?,
                originality_score=?
            WHERE id=?
            """,
            (new_ai_score, 1.0 - new_ai_score, book_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_book_analysis(
    book_id: int,
    ai_score: float,
    readability_score: float,
    originality_score: float,
    overall_rating: float,
    analysis_json: str,
) -> None:
    """Update analysis fields after processing."""
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE books
            SET ai_score=?, readability_score=?, originality_score=?,
                overall_rating=?, analysis_json=?
            WHERE id=?
            """,
            (
                ai_score,
                readability_score,
                originality_score,
                overall_rating,
                analysis_json,
                book_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_book(book_id: int) -> None:
    """Delete a book and its associated on-disk text files."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM books WHERE id=?", (book_id,))
        conn.commit()
    finally:
        conn.close()

    for kind in ("original", "edited"):
        path = _text_file_path(book_id, kind)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
