# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

# 1. Base External Dependencies
hidden_imports = [
    'biopro.plugins',
    'matplotlib.backends.backend_qtagg',
    'pandas',
    'numpy',
    'scipy',
    'cv2',
    'PyQt6.QtPrintSupport',
    'PyQt6.QtCore',
]

# 2. DYNAMIC Internal Collection
# Because __init__.py now exists, this automatically grabs image_utils.py 
# and any future tools you add to the shared folder!
hidden_imports += collect_submodules('biopro.shared')

# Grab any associated data files/binaries in the shared folder
shared_bins, shared_datas, shared_hidden = collect_all('biopro.shared')
hidden_imports.extend(shared_hidden)


a = Analysis(
    ['biopro/__main__.py'],
    pathex=[],
    binaries=shared_bins,
    # The tuple format ('source', 'dest') automatically handles Mac vs Windows pathing!
    datas=[('themes', 'themes')] + shared_datas, 
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