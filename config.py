import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')
DATABASE_PATH = os.path.join(BASE_DIR, 'book_editor.db')

ALLOWED_EXTENSIONS = {'pdf', 'epub', 'txt', 'docx'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB

CHUNK_SIZE = 5000  # characters per chunk

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
