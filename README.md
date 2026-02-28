# book-editor

## Quick Start (Windows)

### Option 1 — Double-click `launch.bat`

Simply double-click **`launch.bat`** in the project root. It will automatically:

1. Detect Python on your PATH (and prompt you to install it if missing).
2. Create a Python virtual environment (`venv/`) the first time it runs.
3. Install all dependencies from `requirements.txt` if they are not already present.
4. Start the Book Editor server (`app.py`).
5. Open `http://localhost:5000` in your default browser.

If anything goes wrong the console window stays open so you can read the error message.

### Option 2 — Create a Desktop Shortcut

Run **`setup_shortcut.bat`** once:

1. Double-click `setup_shortcut.bat` in the project root.
2. A **"Book Editor"** shortcut is created on your Desktop.
3. From now on, just double-click that shortcut — it handles everything (venv creation, dependency installation, server launch, and browser opening) automatically.

> **Prerequisites:** [Python 3](https://www.python.org/downloads/) must be installed and added to your PATH.