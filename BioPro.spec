# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

# 1. Force-collect the entirety of scikit-image
sk_bins, sk_datas, sk_hidden = collect_all('skimage')

# 2. Base External Dependencies
hidden_imports = [
    'biopro.plugins',
    'matplotlib.backends.backend_qtagg',
    'pandas',
    'numpy',
    'scipy',
    'cv2',
    'PyQt6.QtPrintSupport',
    'PyQt6.QtCore',
] + sk_hidden  # Add the skimage submodules here!

a = Analysis(
    ['biopro/__main__.py'],
    pathex=[],
    binaries=[] + sk_bins, # Add skimage binaries here!
    # Physically copy your shared folder as raw data
    datas=[
        ('themes', 'themes'),
        ('biopro/shared', 'biopro/shared') 
    ] + sk_datas, # Add skimage data files here!
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