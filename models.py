import sqlite3
from datetime import datetime
import config


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_path TEXT NOT NULL,
            edited_path TEXT,
            upload_date TEXT NOT NULL,
            file_type TEXT NOT NULL,
            total_chunks INTEGER DEFAULT 0,
            processed_chunks INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            readability_score REAL DEFAULT 0,
            originality_score REAL DEFAULT 0,
            quality_score REAL DEFAULT 0,
            overall_score REAL DEFAULT 0,
            ai_content_percentage REAL DEFAULT 0,
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            original_text TEXT,
            edited_text TEXT,
            ai_score REAL DEFAULT 0,
            is_ai_flagged INTEGER DEFAULT 0,
            FOREIGN KEY (book_id) REFERENCES books(id)
        );
    """)

    conn.commit()
    conn.close()


def create_book(title, filename, original_path, file_type):
    """Insert a new book record and return its id."""
    conn = get_db()
    cur = conn.cursor()
    upload_date = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO books (title, filename, original_path, upload_date, file_type) "
        "VALUES (?, ?, ?, ?, ?)",
        (title, filename, original_path, upload_date, file_type)
    )
    book_id = cur.lastrowid
    conn.commit()
    conn.close()
    return book_id


def get_book(book_id):
    """Fetch a single book by id."""
    conn = get_db()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return book


def get_all_books():
    """Fetch all books ordered by upload date descending."""
    conn = get_db()
    books = conn.execute(
        "SELECT * FROM books ORDER BY upload_date DESC"
    ).fetchall()
    conn.close()
    return books


ALLOWED_BOOK_COLUMNS = {
    'title', 'filename', 'original_path', 'edited_path',
    'upload_date', 'file_type', 'total_chunks', 'processed_chunks',
}


def update_book(book_id, **kwargs):
    """Update columns of a book record."""
    invalid = set(kwargs) - ALLOWED_BOOK_COLUMNS
    if invalid:
        raise ValueError(f"Invalid column(s): {invalid}")
    conn = get_db()
    fields = ', '.join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [book_id]
    conn.execute(f"UPDATE books SET {fields} WHERE id = ?", values)
    conn.commit()
    conn.close()


def create_rating(book_id, readability, originality, quality, overall, ai_pct):
    """Insert or replace a rating for a book."""
    conn = get_db()
    conn.execute(
        "INSERT INTO ratings (book_id, readability_score, originality_score, "
        "quality_score, overall_score, ai_content_percentage) VALUES (?, ?, ?, ?, ?, ?)",
        (book_id, readability, originality, quality, overall, ai_pct)
    )
    conn.commit()
    conn.close()


def get_rating(book_id):
    """Fetch the rating for a book."""
    conn = get_db()
    rating = conn.execute(
        "SELECT * FROM ratings WHERE book_id = ?", (book_id,)
    ).fetchone()
    conn.close()
    return rating


def create_chunk(book_id, chunk_index, original_text, edited_text, ai_score, is_ai_flagged):
    """Insert a chunk record."""
    conn = get_db()
    conn.execute(
        "INSERT INTO chunks (book_id, chunk_index, original_text, edited_text, "
        "ai_score, is_ai_flagged) VALUES (?, ?, ?, ?, ?, ?)",
        (book_id, chunk_index, original_text, edited_text, ai_score, int(is_ai_flagged))
    )
    conn.commit()
    conn.close()


def get_chunks(book_id):
    """Fetch all chunks for a book ordered by index."""
    conn = get_db()
    chunks = conn.execute(
        "SELECT * FROM chunks WHERE book_id = ? ORDER BY chunk_index",
        (book_id,)
    ).fetchall()
    conn.close()
    return chunks


def delete_book(book_id):
    """Delete a book and all its associated data."""
    conn = get_db()
    conn.execute("DELETE FROM chunks WHERE book_id = ?", (book_id,))
    conn.execute("DELETE FROM ratings WHERE book_id = ?", (book_id,))
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
