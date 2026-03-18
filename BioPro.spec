# -*- mode: python ; coding: utf-8 -*-
import sys

# 1. Base External Dependencies (No internal files needed here anymore!)
hidden_imports = [
    'biopro.plugins',
    'matplotlib.backends.backend_qtagg',
    'pandas',
    'numpy',
    'scipy',
    'cv2',
    'skimage', # <-- The missing piece!
    'PyQt6.QtPrintSupport',
    'PyQt6.QtCore',
]

a = Analysis(
    ['biopro/__main__.py'],
    pathex=[],
    binaries=[],
    # 2. THE SILVER BULLET: Treat the 'shared' folder as an external SDK
    # This physically copies the folder so external plugins can read the raw files.
    datas=[
        ('themes', 'themes'),
        ('biopro/shared', 'biopro/shared') 
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BioPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, 
    disable_windowed_traceback=False,
    argv_emulation=False,
    # Fixes the Apple Silicon Segfault natively
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.icns'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BioPro',
)

# Protects the Windows/Linux servers from trying to build Apple bundles
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='BioPro.app',
        icon='icon.icns',
        bundle_identifier=None,
    )