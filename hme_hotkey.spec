# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the combined HME tray app and session editor
# Build: pyinstaller hme_hotkey.spec --clean
#
# Produces dist\hme.exe (single-file executable with tray and setup UI)
#

block_cipher = None

a = Analysis(
    ['hme_hotkey.py'],
    pathex=[],
    binaries=[],
    datas=[
        (r'assets\hme.png', 'assets'),
        (r'assets\hme.ico', 'assets'),
    ],
    hiddenimports=[
        # HTTP
        'requests',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
        # Hotkey
        'keyboard',
        # Clipboard
        'pyperclip',
        # Toast notifications
        'winotify',
        # Tray icon
        'pystray',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'unittest',
        'pydoc',
        'doctest',
        'test',
        'distutils',
        'setuptools',
        'pip',
        'wheel',
        'numpy',
        'pandas',
        'matplotlib',
        'scipy',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
        # Optional urllib3 integration; requests uses Windows' standard TLS stack.
        'cryptography',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='hme',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'assets\hme.ico',
    version_file=None,
)
