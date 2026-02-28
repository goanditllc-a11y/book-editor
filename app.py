"""
Book Editor — Main Flask Application
"""

import os
import re
import io

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_file, jsonify, abort
)
from werkzeug.utils import secure_filename

import config
import models
import ai_detector
import editor
import rater

# ---------------------------------------------------------------------------
# Parsers (imported lazily to avoid hard crashes when packages are missing)
# ---------------------------------------------------------------------------

def _parse_pdf(path):
    try:
        import PyPDF2
        text_parts = []
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return '\n'.join(text_parts)
    except Exception as e:
        raise ValueError(f"Could not parse PDF: {e}")


def _parse_epub(path):
    try:
        import ebooklib
        from ebooklib import epub
        from html.parser import HTMLParser

        class _StripTags(HTMLParser):
            def __init__(self):
                super().__init__()
                self._parts = []
            def handle_data(self, data):
                self._parts.append(data)
            def get_text(self):
                return ' '.join(self._parts)

        book = epub.read_epub(path)
        text_parts = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            parser = _StripTags()
            parser.feed(item.get_content().decode('utf-8', errors='ignore'))
            text_parts.append(parser.get_text())
        return '\n'.join(text_parts)
    except Exception as e:
        raise ValueError(f"Could not parse EPUB: {e}")


def _parse_docx(path):
    try:
        from docx import Document
        doc = Document(path)
        return '\n'.join(p.text for p in doc.paragraphs)
    except Exception as e:
        raise ValueError(f"Could not parse DOCX: {e}")


def _parse_txt(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        raise ValueError(f"Could not read TXT file: {e}")


PARSERS = {
    'pdf': _parse_pdf,
    'epub': _parse_epub,
    'docx': _parse_docx,
    'txt': _parse_txt,
}

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)
models.init_db()


def _allowed_file(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS
    )


def _chunk_text(text, size=config.CHUNK_SIZE):
    """Split text into chunks of `size` characters, respecting word boundaries."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        if end < len(text):
            # Try to break at a sentence boundary
            boundary = text.rfind('. ', start, end)
            if boundary == -1:
                boundary = text.rfind(' ', start, end)
            if boundary != -1:
                end = boundary + 1
        chunks.append(text[start:end])
        start = end
    return chunks


def _derive_title(filename):
    """Derive a human-readable title from a filename."""
    name = filename.rsplit('.', 1)[0]
    name = re.sub(r'[_\-]+', ' ', name)
    return name.title()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    books = models.get_all_books()
    books_with_ratings = []
    for book in books:
        rating = models.get_rating(book['id'])
        books_with_ratings.append({'book': book, 'rating': rating})
    return render_template('index.html', books=books_with_ratings)


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('index'))

    f = request.files['file']
    if not f or f.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('index'))

    if not _allowed_file(f.filename):
        flash(
            f'Unsupported file type. Please upload PDF, EPUB, TXT, or DOCX.',
            'danger'
        )
        return redirect(url_for('index'))

    filename = secure_filename(f.filename)
    # Ensure unique filename
    base, ext = os.path.splitext(filename)
    counter = 1
    save_path = os.path.join(config.UPLOAD_FOLDER, filename)
    while os.path.exists(save_path):
        filename = f"{base}_{counter}{ext}"
        save_path = os.path.join(config.UPLOAD_FOLDER, filename)
        counter += 1

    f.save(save_path)

    file_type = ext.lstrip('.').lower()
    title = request.form.get('title', '').strip() or _derive_title(filename)

    # Parse text
    parser = PARSERS.get(file_type)
    if parser is None:
        os.remove(save_path)
        flash('Unsupported file type.', 'danger')
        return redirect(url_for('index'))

    try:
        text = parser(save_path)
    except ValueError as e:
        os.remove(save_path)
        flash(str(e), 'danger')
        return redirect(url_for('index'))

    if not text or not text.strip():
        os.remove(save_path)
        flash('The file appears to be empty or could not be parsed.', 'danger')
        return redirect(url_for('index'))

    # Create DB record
    book_id = models.create_book(title, filename, save_path, file_type)

    # Process in chunks
    chunks = _chunk_text(text)
    models.update_book(book_id, total_chunks=len(chunks))

    # AI detection
    ai_results = ai_detector.analyse_document(chunks)

    # Editing
    edited_chunks = editor.edit_document(chunks, ai_results)

    # Save edited output
    edited_filename = f"edited_{book_id}_{filename.rsplit('.', 1)[0]}.txt"
    edited_path = os.path.join(config.OUTPUT_FOLDER, edited_filename)
    with open(edited_path, 'w', encoding='utf-8') as out:
        out.write('\n\n'.join(edited_chunks))

    # Store chunks in DB
    chunk_results = ai_results.get('chunk_results', [])
    for i, (orig, edited_text) in enumerate(zip(chunks, edited_chunks)):
        cr = chunk_results[i] if i < len(chunk_results) else {}
        models.create_chunk(
            book_id=book_id,
            chunk_index=i,
            original_text=orig,
            edited_text=edited_text,
            ai_score=cr.get('ai_score', 0.0),
            is_ai_flagged=cr.get('is_ai_flagged', False),
        )

    # Update processed_chunks and edited_path
    models.update_book(
        book_id,
        processed_chunks=len(chunks),
        edited_path=edited_path,
    )

    # Rate the book (use full text)
    full_edited = '\n\n'.join(edited_chunks)
    ratings = rater.rate_book(text)
    models.create_rating(
        book_id=book_id,
        readability=ratings['readability'],
        originality=ratings['originality'],
        quality=ratings['quality'],
        overall=ratings['overall'],
        ai_pct=ai_results['overall_ai_percentage'],
    )

    flash(f'"{title}" uploaded and processed successfully!', 'success')
    return redirect(url_for('book_detail', book_id=book_id))


@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = models.get_book(book_id)
    if book is None:
        abort(404)
    rating = models.get_rating(book_id)
    chunks = models.get_chunks(book_id)
    flagged_chunks = [c for c in chunks if c['is_ai_flagged']]
    return render_template(
        'book_detail.html',
        book=book,
        rating=rating,
        chunks=chunks,
        flagged_chunks=flagged_chunks,
    )


@app.route('/book/<int:book_id>/download')
def download(book_id):
    book = models.get_book(book_id)
    if book is None:
        abort(404)
    edited_path = book['edited_path']
    if not edited_path or not os.path.exists(edited_path):
        flash('Edited file not found.', 'danger')
        return redirect(url_for('book_detail', book_id=book_id))
    return send_file(
        edited_path,
        as_attachment=True,
        download_name=f"edited_{book['title']}.txt",
    )


@app.route('/book/<int:book_id>/delete', methods=['POST'])
def delete_book(book_id):
    book = models.get_book(book_id)
    if book is None:
        abort(404)
    # Clean up files
    for path_col in ('original_path', 'edited_path'):
        path = book[path_col]
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
    models.delete_book(book_id)
    flash('Book deleted.', 'info')
    return redirect(url_for('index'))


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 100 MB.', 'danger')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
