# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Book Editor
Build command:  pyinstaller book_editor.spec
"""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[str(Path('.').resolve())],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
    ],
    hiddenimports=[
        'flask',
        'werkzeug',
        'jinja2',
        'sqlite3',
        'PyPDF2',
        'ebooklib',
        'docx',
        'textstat',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BookEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
