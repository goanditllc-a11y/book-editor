# Book Editor

A complete, self-contained Flask web application that lets you upload literary content (books, comics, blog posts, etc.), analyse it for AI-generated text, automatically rewrite flagged passages to sound more natural, rate the work on multiple quality dimensions, and download the edited output — all **entirely offline**.

---

## Features

| Feature | Details |
|---|---|
| 📤 File Upload | PDF, EPUB, TXT, DOCX (up to 100 MB) |
| 🤖 AI Detection | Heuristic/statistical engine — no API required |
| ✍️ Auto-Editing | Rewrites AI-flagged passages to sound more human |
| ⭐ Rating | Readability, Originality, Quality scored 0-100 |
| 📥 Download | Edited text available as `.txt` |
| 🗃️ History | All uploads stored in a local SQLite database |

---

## Prerequisites

- Python 3.9 or higher
- pip

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/goanditllc-a11y/book-editor.git
cd book-editor

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the App

```bash
python app.py
```

Then open your browser at **http://localhost:5000**.

The app creates the following directories automatically on first run:

```
uploads/   — stores uploaded original files
output/    — stores edited .txt output files
```

---

## How It Works

### Upload

1. Choose a file (PDF, EPUB, TXT, or DOCX) and optionally give it a title.
2. Click **Upload & Analyse**.
3. The app parses the text, splits it into ~5000-character chunks, runs AI detection on each chunk, rewrites flagged chunks, rates the full work, and stores everything in a local SQLite database.

### AI Detection

The `ai_detector.py` module uses five heuristic signals:

| Signal | Weight | Description |
|---|---|---|
| Perplexity proxy | 15% | Word-frequency entropy — repetitive vocabulary → higher AI score |
| Burstiness | 25% | Sentence-length variation — uniform lengths → AI |
| Phrase density | 30% | Common AI stock phrases per 1000 words |
| Vocabulary richness | 15% | Type-token ratio — low diversity → AI |
| Repetition | 15% | Repeated trigrams → AI |

Chunks scoring ≥ 55% are flagged as likely AI-generated.

### Editing

The `editor.py` module rewrites flagged chunks using:

- Replacing ~30 common AI phrases with natural alternatives
- Introducing contractions (50% probability per match)
- Splitting very long sentences or merging consecutive short ones
- Varying repeated transition words

### Rating

The `rater.py` module scores the full text on:

| Dimension | Method |
|---|---|
| Readability | Flesch Reading Ease (via `textstat`) |
| Originality | Type-token ratio minus cliché density |
| Quality | Sentence-length analysis + paragraph structure |
| Overall | Weighted average (35% / 35% / 30%) |

---

## Project Structure

```
book-editor/
├── app.py                  # Main Flask application
├── ai_detector.py          # AI content detection module
├── editor.py               # AI content rewriter/editor
├── rater.py                # Book rating engine
├── models.py               # SQLite database helpers
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── book_editor.spec        # PyInstaller spec file
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── book_detail.html
│   └── 404.html
├── static/
│   └── style.css
├── uploads/                # (gitignored) uploaded files
├── output/                 # (gitignored) edited outputs
└── README.md
```

---

## Packaging as a Windows Executable

You can produce a standalone `.exe` using [PyInstaller](https://pyinstaller.org/):

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
pyinstaller book_editor.spec
```

The executable will be placed in `dist/BookEditor.exe`. Double-click it to run the app — no Python installation needed on the target machine.

> **Note:** The spec file targets a one-file build. For very large books the app may take a few seconds to start when launched from the `.exe`.

---

## Configuration

Edit `config.py` to change:

| Setting | Default | Description |
|---|---|---|
| `UPLOAD_FOLDER` | `uploads/` | Where uploaded files are stored |
| `OUTPUT_FOLDER` | `output/` | Where edited files are saved |
| `DATABASE_PATH` | `book_editor.db` | SQLite database file |
| `CHUNK_SIZE` | 5000 | Characters per processing chunk |
| `MAX_CONTENT_LENGTH` | 100 MB | Maximum upload size |

---

## Supported File Formats

| Format | Parser |
|---|---|
| `.pdf` | PyPDF2 |
| `.epub` | ebooklib |
| `.docx` | python-docx |
| `.txt` | built-in |

---

## Privacy

All processing is done **locally on your machine**. No files or text are sent to any external service or API.

---

## License

MIT