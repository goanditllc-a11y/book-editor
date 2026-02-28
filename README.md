# 📚 Book Editor & Rater

A local web application for uploading, analysing, rating and editing books, comics, blogs and any other literary content. Runs entirely on your machine — no cloud API required.

---

## Features

| Feature | Details |
|---|---|
| **Multi-format upload** | PDF, EPUB, DOCX, TXT — up to 200 MB |
| **AI content detection** | Six-signal local engine (phrase patterns, sentence uniformity, vocabulary diversity, burstiness, paragraph uniformity, filler density) |
| **Auto-editing** | Replaces AI phrases, adds contractions, varies sentence structure |
| **Book rating** | Readability (Flesch, FK Grade, Gunning Fog), Originality, Quality → 1-5 star overall |
| **Library** | Browse, sort and manage all uploaded books |
| **Download** | Export edited text as a plain-text file |
| **Large-file support** | Chunked processing for books >50 K words; on-disk text storage for large files |

---

## Quick Start

### Prerequisites
- Python 3.9 or later
- pip

### 1. Clone / download the repository

```bash
git clone <repo-url>
cd book-editor
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

**Windows (double-click):**
```
run.bat
```

**Any platform:**
```bash
python app.py
```

The app will start on **http://localhost:5000** and open in your default browser automatically.

---

## File Structure

```
book-editor/
├── app.py                   # Flask application + routes
├── requirements.txt         # Python dependencies
├── book_editor.spec         # PyInstaller spec (Windows exe)
├── run.bat                  # Windows launcher
├── .gitignore
├── README.md
├── src/
│   ├── __init__.py
│   ├── database.py          # SQLite storage (sqlite3)
│   ├── file_parser.py       # PDF / EPUB / DOCX / TXT parsing
│   ├── ai_detector.py       # Local AI-content detection engine
│   ├── ai_editor.py         # AI-phrase rewriting engine
│   └── rater.py             # Multi-dimensional book rater
├── templates/
│   ├── base.html
│   ├── index.html           # Dashboard + upload
│   ├── book.html            # Book detail + analysis
│   └── library.html         # All books
└── static/
    ├── css/style.css
    └── js/app.js
```

---

## Building a Windows Executable

Requires PyInstaller:

```bash
pip install pyinstaller
pyinstaller book_editor.spec
```

The executable will be at `dist/BookEditor/BookEditor.exe`.

---

## How It Works

### AI Detection
The detector analyses text across six independent signals:

1. **Phrase Patterns** (30%) — counts known AI-generated phrases per 1,000 words.
2. **Sentence Uniformity** (20%) — AI tends to write sentences of similar length; measured via coefficient of variation.
3. **Vocabulary Diversity** (15%) — Type-Token Ratio in sliding windows; low TTR = repetitive = AI-like.
4. **Burstiness** (15%) — natural text has bursty word usage; AI spreads words evenly.
5. **Paragraph Uniformity** (10%) — AI paragraphs tend to be similar in length.
6. **Filler Word Density** (10%) — counts "very", "really", "essentially", etc.

Scores are combined into a single `ai_score` in **[0.0, 1.0]** (0 = human, 1 = AI).

### Rating
- **Readability** — Flesch Reading Ease, Flesch-Kincaid Grade, Gunning Fog → 1-5 stars
- **Originality** — inverse of `ai_score` → 1-5 stars
- **Quality** — sentence variety, average length, paragraph structure → 1-5 stars
- **Overall** — 30% readability + 40% originality + 30% quality

### Auto-Editing
Replaces 50+ known AI phrases with natural alternatives, applies contractions,
and breaks up uniform sentence openings. All changes are logged and shown in the UI.

---

## Supported File Types

| Format | Library |
|---|---|
| PDF | PyMuPDF (`fitz`) |
| DOCX | python-docx |
| EPUB | ebooklib |
| TXT | built-in (multi-encoding) |

---

## Dependencies

```
Flask==3.0.3
PyMuPDF==1.24.5
python-docx==1.1.2
ebooklib==0.18
textstat==0.7.3
nltk==3.8.1
Werkzeug==3.0.3
```

---

## License

MIT
